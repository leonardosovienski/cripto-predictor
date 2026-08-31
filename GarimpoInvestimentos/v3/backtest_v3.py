"""
Backtest V3 — Walk Forward Analysis com Go/No-Go automático.

Valida a hipótese de edge da Fase 1 usando predictor_core.stats:
    - Spearman IC com Block Bootstrap CI
    - PSR (Probabilistic Sharpe Ratio)
    - Max Drawdown

CRITÉRIOS GO/NO-GO:
    GO     : PSR > 0.80 AND CI_lower > 0 AND MaxDD < 20%
    NO-GO  : PSR < 0.80 OR curva destruída por 5bps de slippage

ARQUITETURA WFA:
    Janela in-sample : 180 dias (≈ 540 períodos 8h)
    Janela OOS       : 30 dias  (≈ 90 períodos 8h)
    Purge gap        : 7 dias   (entre IS e OOS — evita leakage)
    Passo            : 30 dias  (rolando)

    Ex.: 360 dias de dados →
        Fold 0: IS=[0,180), purge=[180,187), OOS=[187,217)
        Fold 1: IS=[30,210), purge=[210,217), OOS=[217,247)
        ...

SLIPPAGE:
    5bps = 0.0005 por trade (ida + volta = 0.001 round-trip).
    Aplicado como custo por sinal ativo: P&L_net = P&L_bruto - slippage × |position|.

KELLY FRACIONAL:
    Position sizing pelo critério de Kelly com fração f ∈ (0, 1].
    position = direction × strength × kelly_fraction
    f=1.0 = Kelly completo (MaxDD máximo); f=0.5 / f=0.25 reduzem risco.
    Use --kelly-fractions para simular múltiplas frações de uma vez.

    O Kelly fracional NÃO muda o sinal nem o modelo — apenas escala o tamanho
    da posição. É o lever correto para controlar MaxDD sem destruir o edge.

FORWARD RETURN:
    O sinal no timestamp t é avaliado contra o retorno D+horizon_hours.
    forward_return_8h: ln(spot_close_{t+8h} / spot_close_t)
    forward_return_24h: ln(spot_close_{t+24h} / spot_close_t)

USO (CLI):
    python -m GarimpoInvestimentos.v3.backtest_v3 \
        --symbol BTCUSDT \
        --start-date 2023-01-01 \
        --end-date 2024-12-31 \
        --slippage-bps 5

    # Varredura de Kelly fracional (simula 1.0, 0.5, 0.25, 0.10 de uma vez):
    python -m GarimpoInvestimentos.v3.backtest_v3 \
        --symbol BTCUSDT --start-date 2021-01-01 \
        --kelly-fractions 1.0 0.5 0.25 0.10
"""

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass

from predictor_core.measurement.bootstrap import bootstrap_ci
from predictor_core.obs import emit_event
from predictor_core.stats import (
    max_drawdown,
    probabilistic_sharpe_ratio,
    spearman_block_ci,
)

from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.analyzers.trials import TRIALS_PATH, register_trial
from GarimpoInvestimentos.v3.collectors.funding_collector import load_funding_csv
from GarimpoInvestimentos.v3.collectors.oi_collector import load_oi_csv
from GarimpoInvestimentos.v3.collectors.spot_collector import load_spot_csv
from GarimpoInvestimentos.v3.costs import CostModel
from GarimpoInvestimentos.v3.feature_builder import (
    build_feature_vectors,
    build_oi_index,
    build_spot_index,
)
from GarimpoInvestimentos.v3.regime_engine import RegimeEngine
from GarimpoInvestimentos.v3.signal_engine import (
    _FR_ZSCORE_THRESHOLD as _SIGNAL_FR_ZSCORE_THRESHOLD,
)
from GarimpoInvestimentos.v3.signal_engine import (
    _MIN_REGIME_CONFIDENCE as _SIGNAL_MIN_REGIME_CONFIDENCE,
)
from GarimpoInvestimentos.v3.signal_engine import generate_signal
from GarimpoInvestimentos.v3.timeindex import SortedTimeIndex

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Parâmetros WFA                                                       #
# ------------------------------------------------------------------ #

_IS_DAYS = 180
_OOS_DAYS = 30
_PURGE_DAYS = 7
_STEP_DAYS = 30

_MS_PER_DAY = 86_400_000
_MS_PER_8H = 28_800_000
_SPOT_CANDLE_MS = 3_600_000
_DEFAULT_SLIPPAGE_BPS = 5
_DEFAULT_TAKER_FEE_BPS = 10  # taker por perna (Risco 4 — custos; ver v3/costs.py)
_DEFAULT_HORIZON_HOURS = 24

_GO_PSR_THRESHOLD = 0.80
_GO_MAX_DD_THRESHOLD = 0.20  # 20%

# Gestão de risco intratrade (ausente até esta revisão — o sinal só saía no
# horizonte fixo). 0.0 = desabilitado, preserva o comportamento anterior.
_DEFAULT_STOP_LOSS_BPS = 0.0
_DEFAULT_TAKE_PROFIT_BPS = 0.0

# Fração de Kelly homologada para produção (Kelly sweep BTCUSDT, 2026-06-27).
# Maior fração com veredicto GO: PSR 0.909, IC_lower +0.0205, MaxDD 10.45% (< 20%).
# Maximiza retorno absoluto dentro do orçamento de risco; PSR/IC são invariantes
# sob fracionamento (o Kelly escala exposição, não o sinal). Ver HANDOFF.md.
DEFAULT_KELLY_FRACTION = 0.50

_DATA_ROOT = DATA_DIR / "v3"


# ------------------------------------------------------------------ #
# Resultado por fold                                                   #
# ------------------------------------------------------------------ #


@dataclass
class FoldResult:
    fold: int
    is_start_ms: int
    is_end_ms: int
    oos_start_ms: int
    oos_end_ms: int
    n_signals: int
    n_active: int
    ic: float
    ic_ci_lower: float
    ic_ci_upper: float
    psr: float
    max_dd: float
    sharpe: float
    slippage_bps: float
    verdict: str  # "GO" / "NO-GO" / "INSUFFICIENT_DATA"
    sortino: float = 0.0
    calmar: float = 0.0


@dataclass
class WFAResult:
    symbol: str
    n_folds: int
    folds: list[FoldResult]
    aggregate_psr: float
    aggregate_ic: float
    aggregate_ic_ci_lower: float
    aggregate_max_dd: float
    aggregate_sharpe: float
    final_verdict: str  # "GO" / "NO-GO"
    verdict_reason: str
    fr_window: int = 90  # janela do z-score usada (baseline=90, pivot=21)
    kelly_fraction: float = 1.0  # fração de Kelly aplicada
    # Risco 4 — custos (passo 5.2): bruto vs liquido + IC95 do liquido medio
    aggregate_gross_return: float = 0.0
    aggregate_net_return: float = 0.0
    net_ci_lower: float = 0.0
    net_ci_upper: float = 0.0
    taker_fee_bps: float = _DEFAULT_TAKER_FEE_BPS
    stop_loss_bps: float = _DEFAULT_STOP_LOSS_BPS
    take_profit_bps: float = _DEFAULT_TAKE_PROFIT_BPS
    # Sortino/Calmar sobre a curva de portfólio (V-01 revisão 2): só fazem
    # sentido agora que a equity curve faz netting real de posições
    # concorrentes — sobre a série ingênua anterior, ambos herdariam o
    # mesmo viés de MaxDD subestimado.
    aggregate_sortino: float = 0.0
    aggregate_calmar: float = 0.0


@dataclass
class KellySweepResult:
    """Varredura de frações de Kelly: PSR, MaxDD e Sharpe por fração."""

    symbol: str
    fr_window: int
    results: list[WFAResult]  # um por fração, na mesma ordem que kelly_fractions


# ------------------------------------------------------------------ #
# Utilidades                                                           #
# ------------------------------------------------------------------ #


def _find_spot_return(
    ts_ms: int,
    horizon_hours: int,
    spot_index: "dict[int, float] | SortedTimeIndex",
    tolerance_ms: int = 300_000,
) -> float | None:
    """
    Calcula o retorno forward do spot a partir de ts_ms sem usar o fechamento
    da vela que abre em ``ts_ms``. O indice usa o open-time da vela de 1h para
    armazenar seu close; logo, no instante t, o ultimo close publico e t-1h.
    Aceita SortedTimeIndex (O(log n)) ou dict cru (embrulhado na hora).
    """
    if not isinstance(spot_index, SortedTimeIndex):
        spot_index = SortedTimeIndex(spot_index)
    close_start = spot_index.as_of(ts_ms - _SPOT_CANDLE_MS, tolerance_ms)
    close_end = spot_index.as_of(
        ts_ms + horizon_hours * _SPOT_CANDLE_MS - _SPOT_CANDLE_MS,
        tolerance_ms,
    )

    if close_start is None or close_end is None or close_start <= 0:
        return None
    return math.log(close_end / close_start)


def _find_barrier_return(
    ts_ms: int,
    horizon_hours: int,
    direction: int,
    spot_index: "dict[int, float] | SortedTimeIndex",
    stop_loss_bps: float = 0.0,
    take_profit_bps: float = 0.0,
    tolerance_ms: int = 300_000,
) -> tuple[float, str] | None:
    """
    Retorno de P&L intrabar com saída antecipada por stop-loss/take-profit.

    Caminha hora a hora a partir de ``ts_ms`` (mesma base de close_start de
    ``_find_spot_return``, sem lookahead — cada candle só é observável no seu
    próprio close) e sai assim que o retorno log acumulado, projetado na
    direção do sinal, cruza a barreira de perda ou de ganho. Sem barreira
    atingida, cai no comportamento antigo: retorno do horizonte cheio.

    stop_loss_bps / take_profit_bps == 0.0 desabilita a respectiva barreira
    (mantém compatibilidade com o backtest original quando ambos são 0).

    Retorna (retorno_log, motivo) onde motivo ∈ {"stop_loss", "take_profit",
    "horizon"}, ou None se não houver preço de entrada válido.
    """
    if not isinstance(spot_index, SortedTimeIndex):
        spot_index = SortedTimeIndex(spot_index)

    entry_ts = ts_ms - _SPOT_CANDLE_MS
    entry_price = spot_index.as_of(entry_ts, tolerance_ms)
    if entry_price is None or entry_price <= 0:
        return None

    sl = stop_loss_bps / 10_000.0 if stop_loss_bps > 0 else None
    tp = take_profit_bps / 10_000.0 if take_profit_bps > 0 else None

    last_return = None
    n_candles = horizon_hours
    for h in range(1, n_candles + 1):
        check_ts = ts_ms + h * _SPOT_CANDLE_MS - _SPOT_CANDLE_MS
        price = spot_index.as_of(check_ts, tolerance_ms)
        if price is None or price <= 0:
            continue
        r = math.log(price / entry_price)
        last_return = r
        directional_r = r * direction

        if sl is not None and directional_r <= -sl:
            return -sl * direction, "stop_loss"
        if tp is not None and directional_r >= tp:
            return tp * direction, "take_profit"

    if last_return is None:
        return None
    return last_return, "horizon"


def _ms_to_day_offset(ts_ms: int, origin_ms: int) -> int:
    """Converte timestamp em offset de dias inteiros desde origin_ms."""
    return (ts_ms - origin_ms) // _MS_PER_DAY


def _equity_curve(returns: list[float]) -> list[float]:
    """
    Converte retornos por-período em curva de equity acumulada (base 1.0).
    predictor_core.max_drawdown ESPERA equity acumulada, não retornos brutos.
    Composição multiplicativa: equity_t = Π (1 + r_i).

    Uso restrito a séries de retornos que já representam o P&L do
    portfólio inteiro por período (ex.: paper trading, onde cada retorno é
    sequencial e não-sobreposto). Para o WFA — onde sinais de horizonte
    24h saem a cada 8h e chegam a coexistir 3 posições — use
    ``_portfolio_equity_curve``, que faz o netting correto por
    contabilidade de eventos de abertura/fechamento (V-01).
    """
    equity: list[float] = []
    acc = 1.0
    for r in returns:
        acc *= 1.0 + r
        equity.append(acc)
    return equity


@dataclass
class _Trade:
    entry_ms: int
    net_return: float
    horizon_hours: int


def _portfolio_equity_curve(trades: list["_Trade"], num_slots: int) -> list[float]:
    """
    Curva de equity com netting de posições concorrentes (V-01, revisão 2).

    Contabilidade real por evento de abertura/fechamento — não mais um peso
    fixo 1/num_slots aplicado multiplicativamente em ordem de fechamento.
    Cada posição reserva 1/num_slots do EQUITY TOTAL no instante em que
    abre (não do capital inicial, nem do equity já reduzido por perdas de
    trades que ainda nem tinham fechado quando esta posição foi aberta) e
    devolve capital + P&L realizado no fechamento (entry_ms + horizon_hours).

    Por que a revisão 1 (peso fixo, ver git blame) subestimava perdas
    correlacionadas: aplicar `acc *= 1 + peso*retorno` em ORDEM DE
    FECHAMENTO faz cada trade herdar implicitamente a base já reduzida
    pelos fechamentos anteriores — mesmo que sua alocação tenha sido
    decidida antes desses fechamentos serem conhecidos (lookahead na
    contabilidade, não no sinal). Ex.: 3 trades concorrentes, cada um
    -50%, dividindo 1/3 do capital: contabilidade correta por evento dá
    equity final 0.500 (perda aditiva de 1/6 por trade, como em
    sub-contas reais); a composição multiplicativa antiga dava 0.579
    (perda ~14% menor que a real). Ver tests/test_v3_backtest_barriers.py.

    ``num_slots`` deve refletir o teto físico de concorrência do desenho
    (horizon_hours / cadência de sinal, 8h nesta arquitetura — ver
    ``run_wfa``); a cadência fixa garante que nunca mais que num_slots
    trades estejam abertos ao mesmo tempo, então não há necessidade de
    rejeitar trade por falta de slot (apenas por falta de caixa, coberto
    pelo `min(..., cash)` abaixo — nunca deveria disparar na prática).
    """
    if not trades:
        return []
    num_slots = max(1, num_slots)

    # Eventos: (timestamp, prioridade, trade). Fechamentos (0) processados
    # antes de aberturas (1) no mesmo instante — libera capital antes de
    # realocar, evitando negar uma abertura por caixa momentaneamente presa.
    events: list[tuple[int, int, _Trade]] = []
    for t in trades:
        exit_ms = t.entry_ms + t.horizon_hours * _SPOT_CANDLE_MS
        events.append((t.entry_ms, 1, t))
        events.append((exit_ms, 0, t))
    events.sort(key=lambda e: (e[0], e[1]))

    cash = 1.0
    open_alloc: dict[int, float] = {}  # id(trade) -> capital alocado na abertura
    equity: list[float] = []

    for _, kind, t in events:
        if kind == 0:
            alloc = open_alloc.pop(id(t), None)
            if alloc is not None:
                cash += alloc * (1.0 + t.net_return)
        else:
            invested = sum(open_alloc.values())
            total_equity = cash + invested
            alloc = min(total_equity / num_slots, cash)
            cash -= alloc
            open_alloc[id(t)] = alloc
        equity.append(cash + sum(open_alloc.values()))

    return equity


def _sortino_ratio(returns: list[float]) -> float:
    """
    Sortino não-anualizado, na mesma escala do "Sharpe simples" já usado
    neste módulo (mean/desvio × sqrt(N) sobre a própria amostra de trades,
    não sobre um período calendário fixo — ``predictor_core.stats.sortino``
    assume 252 períodos/ano, o que não bate com a cadência de 8h do WFA;
    reimplementado aqui para consistência com ``fold_sharpe``/``agg_sharpe``).

    Só penaliza desvio de retornos negativos (downside deviation) — dois
    trades com o mesmo retorno médio e mesma volatilidade total, mas um
    deles com toda a variância concentrada em ganhos, não devem ser
    penalizados igualmente pelo Sharpe simples.
    """
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    downside_sq = sum(r**2 for r in returns if r < 0.0)
    downside_std = math.sqrt(downside_sq / len(returns))
    if downside_std <= 1e-12:
        return 0.0
    return (mean_r / downside_std) * math.sqrt(len(returns))


def _calmar_ratio(equity_curve: list[float], max_dd: float) -> float:
    """
    Calmar = retorno cumulativo do portfólio / |MaxDD|, sobre a MESMA curva
    de equity com netting real (``_portfolio_equity_curve``) usada no
    cálculo de ``max_dd`` — nunca sobre a média de retorno por trade, que
    mediria uma grandeza diferente (retorno médio por posição, não do
    portfólio como um todo).
    """
    if not equity_curve or max_dd <= 1e-9:
        return 0.0
    cumulative_return = equity_curve[-1] - 1.0
    return cumulative_return / max_dd


_FINITE_COERCIONS = 0


def _finite(x: float) -> float:
    """Coage nan/inf para 0.0 — evita NaN inválido no JSONL e em comparações.

    ATENÇÃO: coerção silenciosa pode inflar métricas (NaN vira 0 = "neutro").
    Por isso toda coerção é contabilizada em `_FINITE_COERCIONS` e logada —
    se o contador sair de zero, investigue a origem do NaN em vez de
    confiar no agregado.
    """
    global _FINITE_COERCIONS
    if x == x and x not in (float("inf"), float("-inf")):
        return x
    _FINITE_COERCIONS += 1
    logging.getLogger(__name__).warning(
        "_finite coagiu valor não-finito para 0.0 (total=%d) — métricas podem estar infladas",
        _FINITE_COERCIONS,
    )
    return 0.0


# ------------------------------------------------------------------ #
# WFA core                                                            #
# ------------------------------------------------------------------ #


def run_wfa(
    symbol: str,
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
    taker_fee_bps: float = _DEFAULT_TAKER_FEE_BPS,
    horizon_hours: int = _DEFAULT_HORIZON_HOURS,
    fr_window: int = 90,
    kelly_fraction: float = 1.0,
    stop_loss_bps: float = _DEFAULT_STOP_LOSS_BPS,
    take_profit_bps: float = _DEFAULT_TAKE_PROFIT_BPS,
    fr_zscore_threshold: float = _SIGNAL_FR_ZSCORE_THRESHOLD,
    min_regime_confidence: float = _SIGNAL_MIN_REGIME_CONFIDENCE,
) -> WFAResult:
    """
    Executa Walk Forward Analysis sobre os dados locais coletados pelo pipeline.
    Os CSVs devem existir em data/v3/{symbol}/ — rode pipeline.py primeiro.

    kelly_fraction: escala a posição (direction × strength × kelly_fraction).
        1.0 = Kelly completo (baseline); 0.5/0.25/0.10 = fracionamentos.
        NÃO muda sinal nem modelo — apenas o tamanho da posição.

    stop_loss_bps / take_profit_bps: barreiras intratrade em bps (0 = desliga,
    comportamento idêntico ao anterior — saída só no horizonte fixo). Não
    afetam o IC (que mede o sinal cru contra o retorno do horizonte cheio),
    só o P&L simulado — é gestão de risco, não recalibração de sinal.
    """
    sym_dir = _DATA_ROOT / symbol

    funding_records = load_funding_csv(sym_dir / "funding.csv")
    oi_records = load_oi_csv(sym_dir / "oi.csv")
    kline_records = load_spot_csv(sym_dir / "spot_1h.csv")

    if not funding_records:
        raise FileNotFoundError(
            f"Nenhum dado de funding para {symbol}. "
            f"Execute: python -m GarimpoInvestimentos.v3.pipeline --symbol {symbol} --start-date YYYY-MM-DD"
        )

    oi_index = build_oi_index(oi_records)
    spot_index = build_spot_index(kline_records)
    # índice ordenado UMA vez — o loop OOS consulta milhares de vezes (C5)
    spot_ti = SortedTimeIndex(spot_index)

    funding_times_ms = [r.funding_time_ms for r in funding_records]
    funding_rates = [r.funding_rate for r in funding_records]

    origin_ms = funding_times_ms[0]
    total_days = (funding_times_ms[-1] - origin_ms) // _MS_PER_DAY

    logger.info(
        "backtest_v3 [%s]: %d registros de funding, %d dias totais",
        symbol,
        len(funding_records),
        total_days,
    )

    if total_days < (_IS_DAYS + _OOS_DAYS + _PURGE_DAYS):
        raise ValueError(
            f"Série insuficiente: {total_days} dias. "
            f"Necessário ≥ {_IS_DAYS + _OOS_DAYS + _PURGE_DAYS} dias."
        )

    # Constrói features UMA vez sobre a série contínua completa.
    # CRÍTICO: o z-score do funding precisa de fr_window=90 períodos de warmup.
    # Reconstruir features por fatia OOS (30d ≈ 90 períodos) zeraria o output.
    all_features = build_feature_vectors(
        funding_times_ms,
        funding_rates,
        oi_index,
        spot_index,
        symbol,
        fr_window=fr_window,
    )
    logger.info(
        "backtest_v3 [%s]: fr_window=%d, kelly=%.2f",
        symbol,
        fr_window,
        kelly_fraction,
    )
    if len(all_features) < 100:
        raise ValueError(
            f"Apenas {len(all_features)} feature vectors construídos para {symbol}. "
            "Verifique a cobertura de OI e spot 1h."
        )
    logger.info("backtest_v3 [%s]: %d feature vectors (série contínua)", symbol, len(all_features))

    folds: list[FoldResult] = []
    all_oos_returns: list[float] = []
    all_gross_returns: list[float] = []
    all_oos_trades: list[_Trade] = []
    all_ic_pairs: list[tuple[float, float]] = []  # (signal_strength, fwd_return)

    fold_idx = 0
    is_start_day = 0

    while True:
        oos_start_day = is_start_day + _IS_DAYS + _PURGE_DAYS
        oos_end_day = oos_start_day + _OOS_DAYS

        if oos_end_day > total_days:
            break

        is_start_ms = origin_ms + is_start_day * _MS_PER_DAY
        is_end_ms = origin_ms + (is_start_day + _IS_DAYS) * _MS_PER_DAY
        oos_start_ms = origin_ms + oos_start_day * _MS_PER_DAY
        oos_end_ms = origin_ms + oos_end_day * _MS_PER_DAY

        logger.info(
            "backtest_v3 [%s] fold %d: IS=[%d d, %d d), OOS=[%d d, %d d)",
            symbol,
            fold_idx,
            is_start_day,
            is_start_day + _IS_DAYS,
            oos_start_day,
            oos_end_day,
        )

        # Particiona as features pré-construídas por timestamp (sem rebuild).
        is_features = [
            fv for fv in all_features if is_start_ms <= fv.timestamp_exchange_ms < is_end_ms
        ]
        if len(is_features) < 50:
            logger.warning(
                "backtest_v3 fold %d: features IS insuficientes (%d)", fold_idx, len(is_features)
            )
            fold_idx += 1
            is_start_day += _STEP_DAYS
            continue

        # Treina regime engine SOMENTE sobre IS (sem lookahead)
        engine = RegimeEngine()
        engine.fit(
            [fv.log_return_8h for fv in is_features],
            [fv.realized_vol_24h for fv in is_features],
        )

        # Inferência causal: alimenta a série contígua de is_start até o fim do OOS.
        # O Forward Algorithm é causal → cada ponto usa só x_{0:t}; o trecho IS+purge
        # serve apenas de warmup para a recursão alpha. Nenhuma observação futura vaza.
        infer_features = [
            fv for fv in all_features if is_start_ms <= fv.timestamp_exchange_ms < oos_end_ms
        ]
        regime_all = engine.predict_series(
            [fv.log_return_8h for fv in infer_features],
            [fv.realized_vol_24h for fv in infer_features],
        )
        oos_pairs = [
            (fv, rg)
            for fv, rg in zip(infer_features, regime_all)
            if oos_start_ms <= fv.timestamp_exchange_ms < oos_end_ms
        ]

        if len(oos_pairs) < 10:
            logger.warning(
                "backtest_v3 fold %d: dados OOS insuficientes (%d)", fold_idx, len(oos_pairs)
            )
            fold_idx += 1
            is_start_day += _STEP_DAYS
            continue

        # Geração de sinais e cálculo de P&L OOS
        fold_ic_pairs: list[tuple[float, float]] = []
        fold_pnl: list[float] = []
        fold_gross: list[float] = []
        fold_trades: list[_Trade] = []
        n_active = 0
        costs = CostModel(taker_fee_bps=taker_fee_bps, slippage_bps=slippage_bps)

        for fv, regime in oos_pairs:
            signal = generate_signal(
                fv,
                regime,
                horizon_hours=horizon_hours,
                fr_zscore_threshold=fr_zscore_threshold,
                min_regime_confidence=min_regime_confidence,
            )

            fwd = _find_spot_return(fv.timestamp_exchange_ms, horizon_hours, spot_ti)
            if fwd is None:
                continue

            if signal.active and signal.direction != 0:
                n_active += 1
                position = signal.direction * signal.strength * kelly_fraction

                # P&L usa o retorno com barreiras (SL/TP corta a cauda quando
                # configurado); o IC abaixo continua usando `fwd` (retorno
                # cheio do horizonte) para medir o sinal cru, não a saída.
                barrier = _find_barrier_return(
                    fv.timestamp_exchange_ms,
                    horizon_hours,
                    signal.direction,
                    spot_ti,
                    stop_loss_bps=stop_loss_bps,
                    take_profit_bps=take_profit_bps,
                )
                pnl_return = barrier[0] if barrier is not None else fwd

                gross = position * pnl_return
                # Risco 4: liquido de fricção round-trip (taker+slippage × 2 pernas)
                # e do funding REAL vigente na abertura (long paga f>0; short recebe).
                net = costs.net_return(gross, position, fv.funding_rate_raw, horizon_hours)
                fold_gross.append(gross)
                fold_pnl.append(net)
                fold_trades.append(
                    _Trade(
                        entry_ms=fv.timestamp_exchange_ms,
                        net_return=net,
                        horizon_hours=horizon_hours,
                    )
                )
                fold_ic_pairs.append((signal.strength * signal.direction, fwd))
            else:
                # Posição flat: não contribui para P&L mas é contada
                fold_gross.append(0.0)
                fold_pnl.append(0.0)

        if not fold_ic_pairs:
            logger.warning("backtest_v3 fold %d: sem sinais ativos no OOS", fold_idx)
            fold_idx += 1
            is_start_day += _STEP_DAYS
            continue

        # Métricas do fold — spearman_block_ci retorna TUPLA (rho, lo, hi)
        rho, lo, hi = spearman_block_ci(fold_ic_pairs)
        rho, lo, hi = _finite(rho or 0.0), _finite(lo or 0.0), _finite(hi or 0.0)
        fold_psr = _finite(probabilistic_sharpe_ratio(fold_pnl)) if len(fold_pnl) >= 3 else 0.0
        num_slots = max(1, math.ceil(horizon_hours / (_MS_PER_8H / 3_600_000)))
        fold_equity = _portfolio_equity_curve(fold_trades, num_slots)
        fold_dd = max_drawdown(fold_equity)

        # Sharpe simples
        if len(fold_pnl) >= 2:
            mean_r = sum(fold_pnl) / len(fold_pnl)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in fold_pnl) / len(fold_pnl))
            fold_sharpe = (mean_r / std_r) * math.sqrt(len(fold_pnl)) if std_r > 1e-12 else 0.0
        else:
            fold_sharpe = 0.0
        fold_sortino = _sortino_ratio(fold_pnl)
        fold_calmar = _calmar_ratio(fold_equity, fold_dd)

        # Verdict por fold
        if len(fold_ic_pairs) < 10:
            verdict = "INSUFFICIENT_DATA"
        elif fold_psr >= _GO_PSR_THRESHOLD and lo > 0 and fold_dd < _GO_MAX_DD_THRESHOLD:
            verdict = "GO"
        else:
            verdict = "NO-GO"

        fold_result = FoldResult(
            fold=fold_idx,
            is_start_ms=is_start_ms,
            is_end_ms=is_end_ms,
            oos_start_ms=oos_start_ms,
            oos_end_ms=oos_end_ms,
            n_signals=len(oos_pairs),
            n_active=n_active,
            ic=rho,
            ic_ci_lower=lo,
            ic_ci_upper=hi,
            psr=fold_psr,
            max_dd=fold_dd,
            sharpe=fold_sharpe,
            slippage_bps=slippage_bps,
            verdict=verdict,
            sortino=fold_sortino,
            calmar=fold_calmar,
        )
        folds.append(fold_result)
        all_oos_returns.extend(fold_pnl)
        all_gross_returns.extend(fold_gross)
        all_oos_trades.extend(fold_trades)
        all_ic_pairs.extend(fold_ic_pairs)

        logger.info(
            "backtest_v3 [%s] fold %d: IC=%.4f [%.4f, %.4f] PSR=%.3f MaxDD=%.2f%% → %s",
            symbol,
            fold_idx,
            fold_result.ic,
            fold_result.ic_ci_lower,
            fold_result.ic_ci_upper,
            fold_result.psr,
            fold_result.max_dd * 100,
            fold_result.verdict,
        )

        fold_idx += 1
        is_start_day += _STEP_DAYS

    if not folds:
        raise RuntimeError(
            f"Nenhum fold completado para {symbol}. "
            "Verifique o volume de dados e a cobertura temporal."
        )

    # Métricas agregadas (concatenação de todos os OOS) — tupla (rho, lo, hi)
    if all_ic_pairs:
        agg_rho, agg_lo, agg_hi = spearman_block_ci(all_ic_pairs)
        agg_rho, agg_lo = _finite(agg_rho or 0.0), _finite(agg_lo or 0.0)
    else:
        agg_rho, agg_lo = 0.0, 0.0
    agg_psr = (
        _finite(probabilistic_sharpe_ratio(all_oos_returns)) if len(all_oos_returns) >= 3 else 0.0
    )
    agg_num_slots = max(1, math.ceil(horizon_hours / (_MS_PER_8H / 3_600_000)))
    agg_equity = _portfolio_equity_curve(all_oos_trades, agg_num_slots)
    agg_dd = max_drawdown(agg_equity)

    # Risco 4: bruto vs liquido, com IC95 do retorno LIQUIDO medio (block bootstrap
    # — mesma lente 2 do pedagio; bloco adaptado a amostras curtas).
    n_ret = len(all_oos_returns)
    agg_gross_mean = sum(all_gross_returns) / n_ret if n_ret else 0.0
    agg_net_mean = sum(all_oos_returns) / n_ret if n_ret else 0.0
    if n_ret >= 12:
        _bl = max(1, min(21, n_ret // 3))
        net_lo, net_hi, _ = bootstrap_ci(
            list(all_oos_returns), lambda u: sum(u) / len(u), scheme="moving", block_length=_bl
        )
        net_lo, net_hi = _finite(net_lo or 0.0), _finite(net_hi or 0.0)
    else:
        net_lo, net_hi = 0.0, 0.0

    # Sharpe agregado (série OOS completa)
    if len(all_oos_returns) >= 2:
        mean_r = sum(all_oos_returns) / len(all_oos_returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in all_oos_returns) / len(all_oos_returns))
        agg_sharpe = _finite(
            (mean_r / std_r) * math.sqrt(len(all_oos_returns)) if std_r > 1e-12 else 0.0
        )
    else:
        agg_sharpe = 0.0
    agg_sortino = _sortino_ratio(all_oos_returns)
    agg_calmar = _calmar_ratio(agg_equity, agg_dd)

    if agg_psr >= _GO_PSR_THRESHOLD and agg_lo > 0 and agg_dd < _GO_MAX_DD_THRESHOLD:
        final_verdict = "GO"
        verdict_reason = (
            f"PSR={agg_psr:.3f} > 0.80, IC_CI_lower={agg_lo:.4f} > 0, MaxDD={agg_dd:.2%} < 20%"
        )
    else:
        final_verdict = "NO-GO"
        reasons = []
        if agg_psr < _GO_PSR_THRESHOLD:
            reasons.append(f"PSR={agg_psr:.3f} < 0.80")
        if agg_lo <= 0:
            reasons.append(f"IC_CI_lower={agg_lo:.4f} ≤ 0")
        if agg_dd >= _GO_MAX_DD_THRESHOLD:
            reasons.append(f"MaxDD={agg_dd:.2%} ≥ 20%")
        verdict_reason = "; ".join(reasons)

    result = WFAResult(
        symbol=symbol,
        n_folds=len(folds),
        folds=folds,
        aggregate_psr=agg_psr,
        aggregate_ic=agg_rho,
        aggregate_ic_ci_lower=agg_lo,
        aggregate_max_dd=agg_dd,
        aggregate_sharpe=agg_sharpe,
        aggregate_sortino=agg_sortino,
        aggregate_calmar=agg_calmar,
        final_verdict=final_verdict,
        verdict_reason=verdict_reason,
        fr_window=fr_window,
        kelly_fraction=kelly_fraction,
        aggregate_gross_return=agg_gross_mean,
        aggregate_net_return=agg_net_mean,
        net_ci_lower=net_lo,
        net_ci_upper=net_hi,
        taker_fee_bps=taker_fee_bps,
        stop_loss_bps=stop_loss_bps,
        take_profit_bps=take_profit_bps,
    )

    _log_summary(result)
    _emit_result(result)
    # Persiste a serie de retornos OOS (bruto/liquido) — insumo do DSR (Risco 2):
    # o Deflated Sharpe precisa da SERIE, nao dos agregados. Deterministico
    # (random_state=42 + dados estaticos) => re-execucao reproduz a serie.
    import json as _json

    (sym_dir / "wfa_returns.json").write_text(
        _json.dumps(
            {
                "symbol": symbol,
                "kelly_fraction": kelly_fraction,
                "taker_fee_bps": taker_fee_bps,
                "slippage_bps": slippage_bps,
                "net": all_oos_returns,
                "gross": all_gross_returns,
            }
        ),
        encoding="utf-8",
    )
    return result


# ------------------------------------------------------------------ #
# Relatório                                                           #
# ------------------------------------------------------------------ #


def _log_summary(r: WFAResult) -> None:
    logger.info("=" * 60)
    logger.info(
        "WFA RESULTADO FINAL — %s (fr_window=%d, kelly=%.2f)",
        r.symbol,
        r.fr_window,
        r.kelly_fraction,
    )
    logger.info("=" * 60)
    logger.info(
        "Folds: %d | GO: %d | NO-GO: %d",
        r.n_folds,
        sum(1 for f in r.folds if f.verdict == "GO"),
        sum(1 for f in r.folds if f.verdict == "NO-GO"),
    )
    logger.info("PSR agregado   : %.4f (threshold: %.2f)", r.aggregate_psr, _GO_PSR_THRESHOLD)
    logger.info("IC Spearman    : %.4f  CI_lower: %.4f", r.aggregate_ic, r.aggregate_ic_ci_lower)
    logger.info(
        "Max Drawdown   : %.2f%%  (threshold: %.0f%%)",
        r.aggregate_max_dd * 100,
        _GO_MAX_DD_THRESHOLD * 100,
    )
    logger.info("Sharpe agregado: %.4f", r.aggregate_sharpe)
    logger.info(
        "Sortino/Calmar : %.4f / %.4f (sobre a curva de equity com netting)",
        r.aggregate_sortino,
        r.aggregate_calmar,
    )
    logger.info(
        "Retorno medio  : bruto %.6f -> LIQUIDO %.6f por sinal (fee %sbps + slip + funding real)",
        r.aggregate_gross_return,
        r.aggregate_net_return,
        r.taker_fee_bps,
    )
    logger.info(
        "IC95 liq. medio: [%.6f, %.6f]%s",
        r.net_ci_lower,
        r.net_ci_upper,
        "  — cruza zero" if r.net_ci_lower <= 0 <= r.net_ci_upper else "",
    )
    logger.info("─" * 60)
    logger.info("VEREDICTO: %s", r.final_verdict)
    logger.info("RAZÃO    : %s", r.verdict_reason)
    logger.info("=" * 60)
    if r.final_verdict == "GO":
        logger.info("→ Critérios da Fase 1 atendidos. Fase 2 AUTORIZADA.")
    else:
        logger.info("→ Critérios não atendidos. Fase 2 BLOQUEADA. Pivot de pesquisa necessário.")


def run_kelly_sweep(
    symbol: str,
    kelly_fractions: list[float],
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
    taker_fee_bps: float = _DEFAULT_TAKER_FEE_BPS,
    horizon_hours: int = _DEFAULT_HORIZON_HOURS,
    fr_window: int = 90,
) -> KellySweepResult:
    """
    Executa run_wfa para cada fração de Kelly e imprime tabela comparativa.

    O objetivo é encontrar a menor fração que mantém PSR ≥ 0.80 e MaxDD ≤ 18%
    (margem de 2pp sobre o limiar de 20%). O edge (IC Spearman) não muda — só
    o tamanho da posição muda.

    Exemplo:
        frações  [1.0, 0.5, 0.25, 0.10]
        expected : MaxDD cai monotonicamente; Sharpe cai mais lentamente.
    """
    results: list[WFAResult] = []
    for kf in kelly_fractions:
        logger.info("kelly_sweep [%s]: testando kelly_fraction=%.2f", symbol, kf)
        r = run_wfa(
            symbol=symbol,
            slippage_bps=slippage_bps,
            taker_fee_bps=taker_fee_bps,
            horizon_hours=horizon_hours,
            fr_window=fr_window,
            kelly_fraction=kf,
        )
        results.append(r)

    # Tabela comparativa
    header = (
        f"\n{'Kelly':>8}  {'PSR':>6}  {'IC_low':>7}  {'MaxDD':>7}  {'Sharpe':>7}  {'Veredicto'}"
    )
    logger.info(header)
    logger.info("─" * len(header))
    for r in results:
        row = (
            f"{r.kelly_fraction:>8.2f}  "
            f"{r.aggregate_psr:>6.3f}  "
            f"{r.aggregate_ic_ci_lower:>+7.4f}  "
            f"{r.aggregate_max_dd:>6.2%}  "
            f"{r.aggregate_sharpe:>+7.3f}  "
            f"{r.final_verdict}"
        )
        logger.info(row)

    # Recomendação: menor kelly_fraction com Go
    go_results = [r for r in results if r.final_verdict == "GO"]
    if go_results:
        best = min(go_results, key=lambda r: r.kelly_fraction)
        logger.info(
            "\n→ RECOMENDAÇÃO: kelly_fraction=%.2f (menor fração com GO, MaxDD=%.2f%%)",
            best.kelly_fraction,
            best.aggregate_max_dd * 100,
        )
    else:
        logger.info(
            "\n→ Nenhuma fração atingiu GO. Avaliar mudança de parâmetros ou aceitar risco."
        )

    sweep = KellySweepResult(symbol=symbol, fr_window=fr_window, results=results)
    emit_event(
        "v3_cripto",
        "kelly_sweep",
        metrics={
            "n_fractions": float(len(results)),
            "n_go": float(len(go_results)),
        },
        metadata={
            "symbol": symbol,
            "fr_window": fr_window,
            "fractions": kelly_fractions,
            "verdicts": [r.final_verdict for r in results],
            "max_dds": [round(r.aggregate_max_dd * 100, 2) for r in results],
            "psrs": [round(r.aggregate_psr, 4) for r in results],
        },
    )
    return sweep


@dataclass
class ThresholdGridResult:
    """Varredura de thresholds do sinal (fr_zscore, confiança de regime) × WFA.

    Cada combinação roda o WFA completo (retrain do HMM por fold, IS/OOS
    disjuntos, purge) — não é otimização in-sample: os thresholds nunca veem
    o OOS antes do veredito daquele fold. Ainda assim, escolher a MELHOR
    combinação olhando o agregado de TODOS os folds depois de rodar tudo é
    uma forma de overfitting de seleção (igual ao que backtest.py combate
    com PBO/CSCV do lado LLM) — trate o "melhor" daqui como candidato a
    validar numa hipótese pré-registrada nova, nunca como veredicto GO.
    """

    symbol: str
    results: list[WFAResult]
    fr_thresholds: list[float]
    confidence_thresholds: list[float]


def run_threshold_grid(
    symbol: str,
    fr_thresholds: list[float],
    confidence_thresholds: list[float],
    slippage_bps: float = _DEFAULT_SLIPPAGE_BPS,
    taker_fee_bps: float = _DEFAULT_TAKER_FEE_BPS,
    horizon_hours: int = _DEFAULT_HORIZON_HOURS,
    fr_window: int = 90,
    kelly_fraction: float = 1.0,
    stop_loss_bps: float = _DEFAULT_STOP_LOSS_BPS,
    take_profit_bps: float = _DEFAULT_TAKE_PROFIT_BPS,
) -> ThresholdGridResult:
    """Roda WFA para cada combinação (fr_zscore_threshold × min_regime_confidence).

    AVISO METODOLÓGICO (leia antes de usar o resultado para decidir capital):
    isto substitui thresholds "escolhidos por bom senso" por thresholds
    "escolhidos pelo melhor agregado OOS observado" — o que resolve a crítica
    de arbitrariedade, mas troca por um risco de data-snooping se o candidato
    vencedor for tratado como veredicto em vez de nova hipótese a pré-registrar
    e testar em dado fresco (mesma disciplina de docs/HYPOTHESES.md).
    """
    attestation_path = TRIALS_PATH.with_name(f"{TRIALS_PATH.stem}.harness_attestation.json")
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    fingerprint = attestation["pipeline_fingerprint"]
    attempts: list[tuple[str, dict]] = []
    for fr_t in fr_thresholds:
        for conf_t in confidence_thresholds:
            name = f"v3-grid-{symbol.lower()}-fr{fr_t:g}-conf{conf_t:g}"
            params = {
                "symbol": symbol,
                "fr_zscore_threshold": fr_t,
                "min_regime_confidence": conf_t,
                "slippage_bps": slippage_bps,
                "taker_fee_bps": taker_fee_bps,
                "horizon_hours": horizon_hours,
                "fr_window": fr_window,
                "kelly_fraction": kelly_fraction,
                "stop_loss_bps": stop_loss_bps,
                "take_profit_bps": take_profit_bps,
                "selection_family": "threshold_grid",
            }
            # Registra TODAS as combinações antes de olhar qualquer resultado.
            # Atestado expirado ou incompatível bloqueia a grade inteira.
            register_trial(
                name,
                params=params,
                notes="threshold-grid attempt; candidate-only, never direct GO",
                metric="psr",
                pipeline_fingerprint=fingerprint,
            )
            attempts.append((name, params))

    results: list[WFAResult] = []
    for fr_t in fr_thresholds:
        for conf_t in confidence_thresholds:
            logger.info(
                "threshold_grid [%s]: fr_zscore_threshold=%.2f min_regime_confidence=%.2f",
                symbol,
                fr_t,
                conf_t,
            )
            r = run_wfa(
                symbol=symbol,
                slippage_bps=slippage_bps,
                taker_fee_bps=taker_fee_bps,
                horizon_hours=horizon_hours,
                fr_window=fr_window,
                kelly_fraction=kelly_fraction,
                stop_loss_bps=stop_loss_bps,
                take_profit_bps=take_profit_bps,
                fr_zscore_threshold=fr_t,
                min_regime_confidence=conf_t,
            )
            results.append(r)
            register_trial(
                attempts[len(results) - 1][0],
                params=attempts[len(results) - 1][1],
                sharpe=r.aggregate_sharpe,
                notes="threshold-grid attempt completed; candidate-only, never direct GO",
            )

    header = (
        f"\n{'FR_thr':>7}  {'Conf_thr':>9}  {'PSR':>6}  {'IC_low':>7}  "
        f"{'MaxDD':>7}  {'Sharpe':>7}  {'n_active':>9}  {'Veredicto'}"
    )
    logger.info(header)
    logger.info("─" * len(header))
    idx = 0
    for fr_t in fr_thresholds:
        for conf_t in confidence_thresholds:
            r = results[idx]
            idx += 1
            n_active = sum(f.n_active for f in r.folds)
            row = (
                f"{fr_t:>7.2f}  "
                f"{conf_t:>9.2f}  "
                f"{r.aggregate_psr:>6.3f}  "
                f"{r.aggregate_ic_ci_lower:>+7.4f}  "
                f"{r.aggregate_max_dd:>6.2%}  "
                f"{r.aggregate_sharpe:>+7.3f}  "
                f"{n_active:>9d}  "
                f"{r.final_verdict}"
            )
            logger.info(row)

    go_results = [r for r in results if r.final_verdict == "GO"]
    if go_results:
        best = max(go_results, key=lambda r: r.aggregate_psr)
        logger.info(
            "\n→ MELHOR CANDIDATO (maior PSR entre os GO): PSR=%.3f — "
            "trate como hipótese nova a pré-registrar, não como veredicto.",
            best.aggregate_psr,
        )
    else:
        best = max(results, key=lambda r: r.aggregate_psr) if results else None
        logger.info(
            "\n→ Nenhuma combinação atingiu GO. Melhor PSR observado: %.3f (ainda NO-GO).",
            best.aggregate_psr if best else 0.0,
        )

    grid = ThresholdGridResult(
        symbol=symbol,
        results=results,
        fr_thresholds=fr_thresholds,
        confidence_thresholds=confidence_thresholds,
    )
    emit_event(
        "v3_cripto",
        "threshold_grid",
        metrics={
            "n_combinations": float(len(results)),
            "n_go": float(len(go_results)),
            "best_psr": float(max((r.aggregate_psr for r in results), default=0.0)),
        },
        metadata={
            "symbol": symbol,
            "fr_thresholds": fr_thresholds,
            "confidence_thresholds": confidence_thresholds,
            "verdicts": [r.final_verdict for r in results],
        },
    )
    return grid


def _emit_result(r: WFAResult) -> None:
    emit_event(
        "v3_cripto",
        "wfa_result",
        metrics={
            "aggregate_psr": r.aggregate_psr,
            "aggregate_ic": r.aggregate_ic,
            "aggregate_ic_ci_lower": r.aggregate_ic_ci_lower,
            "aggregate_max_dd": r.aggregate_max_dd,
            "aggregate_sharpe": r.aggregate_sharpe,
            "aggregate_sortino": r.aggregate_sortino,
            "aggregate_calmar": r.aggregate_calmar,
            "n_folds": float(r.n_folds),
            "go_folds": float(sum(1 for f in r.folds if f.verdict == "GO")),
        },
        metadata={
            "symbol": r.symbol,
            "final_verdict": r.final_verdict,
            "verdict_reason": r.verdict_reason,
            "psr_threshold": _GO_PSR_THRESHOLD,
            "max_dd_threshold": _GO_MAX_DD_THRESHOLD,
            "fr_window": r.fr_window,
        },
    )


# ------------------------------------------------------------------ #
# CLI                                                                  #
# ------------------------------------------------------------------ #


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Crypto-Predictor V3 — Walk Forward Analysis (Go/No-Go)",
    )
    parser.add_argument("--symbol", nargs="+", default=["BTCUSDT"])
    parser.add_argument(
        "--taker-fee-bps",
        type=float,
        default=_DEFAULT_TAKER_FEE_BPS,
        help="Taxa taker por perna em bps (Risco 4; default 10 = 0,10%%).",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=_DEFAULT_SLIPPAGE_BPS,
        help="Slippage em basis points por trade (default: 5)",
    )
    parser.add_argument(
        "--horizon-hours",
        type=int,
        default=_DEFAULT_HORIZON_HOURS,
        help="Horizonte de avaliação do sinal em horas (default: 24)",
    )
    parser.add_argument(
        "--fr-window",
        type=int,
        default=90,
        help="Janela do z-score de funding em períodos 8h (baseline=90/30d, pivot=21/7d)",
    )
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=1.0,
        help="Fração de Kelly para dimensionamento de posição (default: 1.0 = Kelly completo)",
    )
    parser.add_argument(
        "--kelly-fractions",
        type=float,
        nargs="+",
        default=None,
        help="Varredura de Kelly: simula múltiplas frações de uma vez. Ex: 1.0 0.5 0.25 0.10",
    )
    parser.add_argument(
        "--stop-loss-bps",
        type=float,
        default=_DEFAULT_STOP_LOSS_BPS,
        help="Stop-loss intratrade em bps, na direção do sinal (default: 0 = desligado).",
    )
    parser.add_argument(
        "--take-profit-bps",
        type=float,
        default=_DEFAULT_TAKE_PROFIT_BPS,
        help="Take-profit intratrade em bps, na direção do sinal (default: 0 = desligado).",
    )
    parser.add_argument(
        "--fr-thresholds",
        type=float,
        nargs="+",
        default=None,
        help="Varredura de threshold do z-score de funding (grid junto com --confidence-thresholds).",
    )
    parser.add_argument(
        "--confidence-thresholds",
        type=float,
        nargs="+",
        default=None,
        help="Varredura de confiança mínima de regime (grid junto com --fr-thresholds).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    for symbol in args.symbol:
        try:
            if args.fr_thresholds or args.confidence_thresholds:
                run_threshold_grid(
                    symbol=symbol.upper(),
                    fr_thresholds=args.fr_thresholds or [_SIGNAL_FR_ZSCORE_THRESHOLD],
                    confidence_thresholds=args.confidence_thresholds
                    or [_SIGNAL_MIN_REGIME_CONFIDENCE],
                    slippage_bps=args.slippage_bps,
                    taker_fee_bps=args.taker_fee_bps,
                    horizon_hours=args.horizon_hours,
                    fr_window=args.fr_window,
                    kelly_fraction=args.kelly_fraction,
                    stop_loss_bps=args.stop_loss_bps,
                    take_profit_bps=args.take_profit_bps,
                )
            elif args.kelly_fractions:
                run_kelly_sweep(
                    symbol=symbol.upper(),
                    kelly_fractions=args.kelly_fractions,
                    slippage_bps=args.slippage_bps,
                    taker_fee_bps=args.taker_fee_bps,
                    horizon_hours=args.horizon_hours,
                    fr_window=args.fr_window,
                )
            else:
                run_wfa(
                    symbol=symbol.upper(),
                    slippage_bps=args.slippage_bps,
                    taker_fee_bps=args.taker_fee_bps,
                    horizon_hours=args.horizon_hours,
                    fr_window=args.fr_window,
                    kelly_fraction=args.kelly_fraction,
                    stop_loss_bps=args.stop_loss_bps,
                    take_profit_bps=args.take_profit_bps,
                )
        except Exception as exc:
            logger.error("backtest_v3 [%s]: ERRO — %s", symbol, exc)
            sys.exit(1)


if __name__ == "__main__":
    _main()
