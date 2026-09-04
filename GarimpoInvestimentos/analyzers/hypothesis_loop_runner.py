"""H8 (docs/HYPOTHESES.md): entrypoint que faltava em `hypothesis_loop.py` —
o motor (propõe→valida→registra) já existia e era testado isoladamente, mas
nada chamava `evaluate_proposal` sobre as propostas aceitas, e nada agendava
isso pra rodar. Sem isso, o checklist de ativação do H8 nunca sai do item 4
("coletar dado GENUINAMENTE NOVO") — é exatamente essa lacuna que este módulo
fecha.

O QUE ESTE MÓDULO FAZ (e só isso):
    1. Carrega os FeatureVector já coletados pela V3 (mesmo dado de H1-H3/H9 —
       zero coleta nova de mercado) para um símbolo.
    2. Monta `dados` (nome de feature -> série) e `retornos` (forward log
       return no horizonte pedido) a partir deles.
    3. `run_round()`: propõe (LLM real por padrão), valida, registra TODAS no
       traço append-only (`hypothesis_proposals.json`).
    4. Avalia SÓ as propostas ACEITAS desta rodada com `evaluate_proposal`
       (as mesmas funções canônicas do backtest oficial) e anexa o resultado
       a `hypothesis_evaluations.json` — outro traço append-only, mesmo
       princípio do `predictions_archive`.

O QUE ESTE MÓDULO CONTINUA NUNCA FAZENDO (herdado de hypothesis_loop.py):
    NÃO escreve em trials.json, NÃO emite veredito, NÃO descarta proposta em
    silêncio, NÃO promove nada. Nenhuma linha aqui decide se H8 é GO/NO-GO —
    isso exige leitura humana do traço acumulado contra o critério
    pré-registrado (Spearman IC95% não cruzando zero, n>=30), depois de n
    suficiente ter se acumulado.

Uso:
    python -m GarimpoInvestimentos.analyzers.hypothesis_loop_runner \
        --symbol BTCUSDT --horizon-days 7
    python -m GarimpoInvestimentos.analyzers.hypothesis_loop_runner --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from GarimpoInvestimentos.analyzers.hypothesis_loop import (
    ACCEPTED,
    PROPOSALS_PATH,
    Evaluation,
    evaluate_proposal,
    run_round,
)
from GarimpoInvestimentos.core.paths import DATA_DIR
from GarimpoInvestimentos.v3.collectors.funding_collector import load_funding_csv
from GarimpoInvestimentos.v3.collectors.oi_collector import load_oi_csv
from GarimpoInvestimentos.v3.collectors.spot_collector import load_spot_csv
from GarimpoInvestimentos.v3.feature_builder import (
    FeatureVector,
    build_feature_vectors,
    build_oi_index,
    build_spot_index,
)

_DATA_ROOT = DATA_DIR / "v3"

# Append-only, mesmo princípio de PROPOSALS_PATH (hypothesis_loop.py).
EVALUATIONS_PATH = Path(__file__).resolve().parent.parent / "hypothesis_evaluations.json"

# Campos de FeatureVector expostos ao DSL como "feature(nome)" — os mesmos que
# H1-H3/H9 já usam, nada novo é calculado aqui. `feature_zscore` renomeado só
# no vocabulário do prompt para bater com o nome do campo real
# (`funding_zscore`), evitando o LLM inventar um nome que não existe.
_EXPOSED_FEATURES = (
    "funding_zscore",
    "oi_log_delta",
    "leverage_pressure",
    "log_return_8h",
    "realized_vol_24h",
)

# Períodos de funding por dia (8h cada) — mesma convenção de overlap_block_length
# em analyzers/backtest.py, usada pra converter horizon_days em passos da série.
_PERIODS_PER_DAY = 3


def _build_dados_e_retornos(
    feature_vectors: list[FeatureVector], horizon_days: int
) -> tuple[dict[str, list[float | None]], list[float | None]]:
    """`dados`: uma série por campo exposto de FeatureVector, na ordem da série
    contínua. `retornos`: forward log return de `spot_close` no horizonte
    pedido — None nos últimos `passos` pontos (sem retorno futuro observável
    ainda), nunca um valor inventado."""
    passos = horizon_days * _PERIODS_PER_DAY
    dados: dict[str, list[float | None]] = {
        nome: [getattr(fv, nome) for fv in feature_vectors] for nome in _EXPOSED_FEATURES
    }
    closes = [fv.spot_close for fv in feature_vectors]
    retornos: list[float | None] = []
    for i in range(len(closes)):
        j = i + passos
        if j >= len(closes) or closes[i] <= 0.0 or closes[j] <= 0.0:
            retornos.append(None)
            continue
        retornos.append(math.log(closes[j] / closes[i]))
    return dados, retornos


def _load_feature_vectors(symbol: str) -> list[FeatureVector]:
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
    funding_times_ms = [r.funding_time_ms for r in funding_records]
    funding_rates = [r.funding_rate for r in funding_records]
    return build_feature_vectors(funding_times_ms, funding_rates, oi_index, spot_index, symbol)


def load_evaluations(path: Path = EVALUATIONS_PATH) -> list[dict]:
    if not path.exists():
        return []
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return dados if isinstance(dados, list) else []


def append_evaluations(evaluations: list[Evaluation], path: Path = EVALUATIONS_PATH) -> int:
    atuais = load_evaluations(path)
    atuais.extend(asdict(e) for e in evaluations)
    path.write_text(json.dumps(atuais, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(evaluations)


async def run_h8_round(
    *,
    symbol: str = "BTCUSDT",
    horizon_days: int = 7,
    historico: str = "H1-H6: todas refutadas ou encerradas sem veredito (docs/HYPOTHESES.md). "
    "H9 (razão OI/volume): registrada, aguardando primeira leitura.",
    proposer=None,
    proposer_name: str = "gemini",
    now: datetime | None = None,
    proposals_path: Path = PROPOSALS_PATH,
    evaluations_path: Path = EVALUATIONS_PATH,
) -> tuple[list, list[Evaluation]]:
    """Uma rodada completa do H8: propõe+registra (run_round), depois avalia só
    as propostas ACEITAS desta rodada e anexa ao traço de avaliações. Retorna
    (propostas, avaliacoes) — quem chama decide o que fazer com isso; este
    módulo não emite veredito nem promove nada.

    `proposals_path`/`evaluations_path` default para os caminhos reais do
    projeto — passados explicitamente (não via monkeypatch de módulo) porque
    `run_round` já vincula seu próprio default na assinatura no momento da
    importação; testes DEVEM passar um `tmp_path` aqui para não escrever no
    traço real."""
    feature_vectors = _load_feature_vectors(symbol)
    dados, retornos = _build_dados_e_retornos(feature_vectors, horizon_days)

    propostas = await run_round(
        features=_EXPOSED_FEATURES,
        horizon_days=horizon_days,
        historico=historico,
        proposer=proposer,
        proposer_name=proposer_name,
        path=proposals_path,
        now=now,
    )

    avaliacoes = [evaluate_proposal(p, dados, retornos) for p in propostas if p.status == ACCEPTED]
    if avaliacoes:
        append_evaluations(avaliacoes, path=evaluations_path)
    return propostas, avaliacoes


async def _dry_run_proposer(_prompt: str) -> str:
    """Proposer offline para --dry-run: não chama nenhum LLM real, só exercita
    o wiring ponta-a-ponta com uma proposta sintética válida."""
    return json.dumps(
        [
            {
                "hypothesis": "[DRY-RUN, nao e proposta real] leverage_pressure alto precede reversao.",
                "recipe": {"op": "feature", "args": ["leverage_pressure"]},
            }
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--horizon-days", type=int, default=7)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Usa um proposer sintético offline em vez do LLM real — smoke test do wiring, "
        "não gera dado que conte para o gate do H8.",
    )
    args = parser.parse_args(argv)

    proposer = _dry_run_proposer if args.dry_run else None
    proposer_name = "dry-run" if args.dry_run else "gemini"
    # --dry-run NUNCA escreve no traço real: mistura entrada sintética com
    # propostas de verdade corromperia o denominador honesto que o PBO/DSR
    # dependem de contar. Arquivos-irmãos separados, não os mesmos com um
    # filtro — simples o bastante pra não ter como vazar por engano.
    proposals_path = (
        PROPOSALS_PATH.with_name("hypothesis_proposals.dryrun.json")
        if args.dry_run
        else PROPOSALS_PATH
    )
    evaluations_path = (
        EVALUATIONS_PATH.with_name("hypothesis_evaluations.dryrun.json")
        if args.dry_run
        else EVALUATIONS_PATH
    )

    propostas, avaliacoes = asyncio.run(
        run_h8_round(
            symbol=args.symbol,
            horizon_days=args.horizon_days,
            proposer=proposer,
            proposer_name=proposer_name,
            proposals_path=proposals_path,
            evaluations_path=evaluations_path,
        )
    )
    print(
        f"H8 [{args.symbol}]: {len(propostas)} proposta(s) nesta rodada "
        f"({sum(p.status == 'ACCEPTED_FOR_EVALUATION' for p in propostas)} aceita(s)), "
        f"{len(avaliacoes)} avaliada(s)."
    )
    for a in avaliacoes:
        print(f"  {a.proposal_id}: n={a.n} rho={a.rho} ic=[{a.ic_lower}, {a.ic_upper}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
