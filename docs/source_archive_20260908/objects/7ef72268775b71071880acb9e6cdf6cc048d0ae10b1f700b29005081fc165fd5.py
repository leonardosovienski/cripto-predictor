"""Harness de VERDADE PLANTADA — mede erros e acertos do pipeline INTEIRO.

=== POR QUE DADO REAL DO PASSADO NAO SERVE PARA ISTO ===

A tentacao natural e "rodar o pipeline sobre o historico e ver se ele acerta".
Nao funciona como medida de QUALIDADE DO PIPELINE, por um motivo estrutural: se
o resultado der NO-GO, ha duas explicacoes indistinguiveis — (a) nao ha edge no
mercado, (b) o pipeline esta quebrado e nao acharia edge nenhum. Um sistema que
so emitiu NO-GO ate hoje e infalsificavel enquanto essa ambiguidade existir.

Verdade PLANTADA desfaz a ambiguidade: construimos um mundo onde a resposta e
conhecida por construcao, e exigimos que o pipeline a recupere. Foi exatamente
o raciocinio do controle positivo ja existente (tests/test_positive_control.py,
scripts/attest_harness.py).

=== O QUE ESTE MODULO ACRESCENTA AO QUE JA EXISTIA ===

O controle positivo atual injeta pares (score, retorno) DIRETO no `_report`.
Ele valida o JUIZ ESTATISTICO — e nada mais. Fica de fora todo o encanamento
entre a previsao gravada e o par que chega ao juiz:

    predictions (store)  ->  _load_rows()  ->  enrich_with_realized_prices()  ->  par

`enrich_with_realized_prices` e onde a MEDICAO acontece: e ela que transforma
"previsao de 01/08 com preco X" em "retorno de +2,3% em D+7". Verificado em
2026-08-21: NENHUM teste da suite a importava. Ela rodava (via quality_snapshot)
mas nunca fora confrontada com uma resposta conhecida.

Isso importa porque um erro ali e SILENCIOSO e TOTAL: se a funcao pegasse o
preco do dia errado, ou perdesse um estrato, todo veredito ja emitido estaria
medindo outra coisa que nao o que afirma medir — e o controle positivo do juiz
continuaria verde, porque ele nunca toca esse caminho.

=== O QUE ELE MEDE ===

1. ERRO DE MEDICAO: o `var_dN_pct` recuperado bate com o retorno que plantamos?
   Esta e a pergunta que ninguem estava fazendo.
2. PERDA DE AMOSTRA: alguma previsao gravada some no caminho?
3. PODER: com edge plantado o veredito e "validado"; com ruido puro, "RUIDO".

NAO e gate, nao altera veredito e nao autoriza nada. E instrumento de aferição
do proprio instrumento.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from GarimpoInvestimentos.analyzers.backtest import HORIZONS
from GarimpoInvestimentos.dpl.contracts import MarketDataPoint
from GarimpoInvestimentos.dpl.feature_store import FeatureStore

#: Fonte usada no mundo sintetico. Precisa ser uma fonte real do vocabulario
#: para o caminho de estratificacao ser o mesmo da producao.
FONTE = "dpl:fallback"

#: Granularidade da medicao, medida (nao suposta) por este harness em 2026-08-21.
#: `enrich_with_realized_prices` faz `round(..., 2)` no var_dN_pct, entao o retorno
#: e quantizado em 0,01 ponto percentual e o erro maximo de arredondamento e
#: metade disso. Nao e defeito — e escolha de formatacao — mas nunca estivera
#: caracterizada em lugar nenhum, e a tolerancia de qualquer afericao precisa
#: parti-la, senao acusa bug onde ha arredondamento.
MEASUREMENT_QUANTUM_PP = 0.01
MAX_ROUNDING_ERROR_PP = MEASUREMENT_QUANTUM_PP / 2


@dataclass(frozen=True)
class PlantedWorld:
    """Mundo sintetico com resposta conhecida por construcao."""

    db_path: Path
    #: (ativo, pred_date) -> retorno percentual REAL em D+horizon, por construcao.
    truth: dict[tuple[str, datetime], float]
    n_predictions: int
    horizon_days: int


@dataclass(frozen=True)
class HarnessResult:
    n_planted: int
    n_recovered: int
    max_measurement_error_pp: float | None
    mean_measurement_error_pp: float | None
    lost_predictions: int

    @property
    def measurement_ok(self) -> bool:
        """Tolerancia = o quantum de arredondamento da propria medicao, e nada
        alem dele.

        O retorno e aritmetica sobre precos que nos mesmos gravamos, entao a
        unica discrepancia legitima e o `round(..., 2)` que
        `enrich_with_realized_prices` aplica. Qualquer desvio ACIMA disso e bug
        de medicao — dia errado, preco errado, fonte errada — e nao ruido.

        A primeira versao deste harness usava 1e-6 e falhou com 0,004992pp: foi
        assim que a granularidade real da medicao ficou caracterizada.
        """
        return (
            self.lost_predictions == 0
            and self.max_measurement_error_pp is not None
            and self.max_measurement_error_pp <= MAX_ROUNDING_ERROR_PP + 1e-9
        )


def plant_world(
    db_path: Path,
    *,
    n_assets: int = 6,
    n_days: int = 90,
    horizon_days: int = 7,
    edge: float = 0.08,
    seed: int = 17,
    base_price: float = 100.0,
) -> PlantedWorld:
    """Constroi store com OHLCV e previsoes cuja relacao score->retorno e conhecida.

    `edge` = pontos percentuais de retorno por ponto de score acima/abaixo de 50
    (mesma parametrizacao do controle positivo existente, para as duas medidas
    serem comparaveis). `edge=0` produz o mundo NULO.

    Os precos sao gravados na store para que `_realized_price` os resolva
    OFFLINE — o caminho de rede nao e exercitado aqui de proposito: o objeto sob
    teste e a aritmetica da medicao, nao a coleta.
    """
    rng = random.Random(seed)
    inicio = datetime(2026, 1, 1, tzinfo=UTC)
    ativos = [f"ativo{i}" for i in range(n_assets)]
    truth: dict[tuple[str, datetime], float] = {}
    previsoes = []
    pontos: list[MarketDataPoint] = []

    for ativo in ativos:
        # Caminho de precos: passeio aleatorio. Guardamos TODOS os dias, entao o
        # retorno em D+h e determinado — nao estimado.
        precos = [base_price]
        for _ in range(n_days):
            precos.append(precos[-1] * (1.0 + rng.gauss(0.0, 0.02)))
        for dia, preco in enumerate(precos):
            ts = inicio + timedelta(days=dia)
            pontos.append(
                MarketDataPoint(
                    symbol=ativo,
                    timestamp=ts,
                    open=preco,
                    high=preco,
                    low=preco,
                    close=preco,
                    volume=1000.0,
                    source=FONTE,
                    interval="1d",
                    published_at=ts,
                )
            )

        # Previsoes so em dias cujo MAIOR horizonte ainda existe no mundo.
        #
        # Nao e detalhe de conveniencia: `_realized_price` e offline-first, mas
        # quando a store NAO tem o dia ele cai no CoinGecko e dorme 1,5s por
        # consulta (rate limit). Gerar previsao cujo D+30 caia fora do mundo faria
        # o harness sair para a rede centenas de vezes — a primeira versao deste
        # arquivo fazia exatamente isso e levava minutos em vez de segundos.
        # Cobrir TODOS os horizontes mantem a afericao 100% offline e rapida.
        maior_horizonte = max(HORIZONS)
        for dia in range(n_days - maior_horizonte):
            p0, ph = precos[dia], precos[dia + horizon_days]
            retorno_pp = (ph / p0 - 1.0) * 100.0
            # Score CONSTRUIDO a partir do retorno realizado: e assim que se
            # planta edge conhecido. Com edge=0 o score e independente do retorno.
            score = 50.0 + (retorno_pp / edge if edge else rng.gauss(0.0, 15.0))
            score = max(0.0, min(100.0, score))
            pred_date = inicio + timedelta(days=dia)
            truth[(ativo, pred_date)] = retorno_pp
            previsoes.append(
                {
                    "ativo": ativo,
                    "ts": pred_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "score": round(score, 2),
                    "sentimento": "neutro",
                    "resumo": "mundo sintetico",
                    "price_usd": p0,
                    "juiz": "harness:sintetico:v1",
                    "divergencia": 0,
                    "fonte": FONTE,
                    "llm_fallback": 0,
                }
            )

    with FeatureStore(db_path) as store:
        store.write_raw(pontos)
        store.write_predictions(previsoes)

    return PlantedWorld(
        db_path=db_path,
        truth=truth,
        n_predictions=len(previsoes),
        horizon_days=horizon_days,
    )


def compare_to_truth(enriched: list[dict], world: PlantedWorld) -> HarnessResult:
    """Confronta o que o pipeline MEDIU com o que plantamos.

    Previsao cujo D+h cai fora do mundo tem `var` None legitimamente e nao conta
    como perda; perda e previsao que EXISTIA na verdade e sumiu do caminho.
    """
    chave = f"var_d{world.horizon_days}_pct"
    erros: list[float] = []
    recuperadas = 0
    vistas: set[tuple[str, datetime]] = set()

    for r in enriched:
        medido = r.get(chave)
        if medido is None:
            continue
        k = (r["ativo"], r["pred_date"].replace(tzinfo=None))
        esperado = world.truth.get((k[0], k[1].replace(tzinfo=UTC)))
        if esperado is None:
            continue
        vistas.add(k)
        recuperadas += 1
        erros.append(abs(float(medido) - esperado))

    maturas = sum(
        1
        for (ativo, data) in world.truth
        if data + timedelta(days=world.horizon_days) <= _ultimo_dia(world)
    )
    return HarnessResult(
        n_planted=len(world.truth),
        n_recovered=recuperadas,
        max_measurement_error_pp=max(erros) if erros else None,
        mean_measurement_error_pp=(sum(erros) / len(erros)) if erros else None,
        lost_predictions=max(0, maturas - recuperadas),
    )


def _ultimo_dia(world: PlantedWorld) -> datetime:
    return max(data for _ativo, data in world.truth) + timedelta(days=world.horizon_days)


def spearman_of(enriched: list[dict], horizon: int) -> float | None:
    """Correlacao de posto simples, so para comparar o recuperado com o plantado.
    O veredito oficial continua sendo o do `_report`; isto e aferição."""
    pares = [
        (r["score"], r[f"var_d{horizon}_pct"])
        for r in enriched
        if r.get(f"var_d{horizon}_pct") is not None
    ]
    n = len(pares)
    if n < 3:
        return None

    def _postos(vals):
        ordem = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        for pos, i in enumerate(ordem):
            r[i] = float(pos)
        return r

    rx, ry = _postos([p[0] for p in pares]), _postos([p[1] for p in pares])
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return None if den == 0 else num / den


__all__ = [
    "FONTE",
    "HarnessResult",
    "PlantedWorld",
    "compare_to_truth",
    "plant_world",
    "spearman_of",
]
