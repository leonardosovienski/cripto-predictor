"""H7 (macro/DXY): covariáveis extras para o RegimeEngine — docs/HYPOTHESES.md.

Duas funções puras, alinhadas por timestamp a uma lista de FeatureVector:

  1. `build_macro_event_dummy` — 1.0/0.0 por ponto: está a até `window_days` de
     QUALQUER evento (FOMC/CPI/PPI) do calendário? Reusa o parser puro de
     `dpl.macro_calendar` (sem tocar em `persist_macro_signals`/FeatureStore —
     este módulo não grava nada, só deriva a covariável em memória).
  2. `build_dxy_return` — retorno 1d do DXY, ponto-a-ponto, respeitando
     `publish_lag_days` (mesma semântica de `dpl.providers.dxy.DXYProvider`):
     usa o candle mais recente cujo `date + lag <= data do ponto`, nunca um
     valor "do futuro" relativo ao momento em que o dado estaria realmente
     publicado.

Ambas recebem dado JÁ COLETADO (calendário local; série de closes do DXY) — não
buscam nada na rede. A coleta ao vivo do DXY é responsabilidade do
`DXYProvider`, chamado fora deste módulo.
"""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from pathlib import Path

from GarimpoInvestimentos.dpl.business_days import published_at
from GarimpoInvestimentos.dpl.macro_calendar import MacroEvent, load_macro_calendar
from GarimpoInvestimentos.v3.feature_builder import FeatureVector


def _ts_to_date(timestamp_exchange_ms: int) -> date:
    return datetime.fromtimestamp(timestamp_exchange_ms / 1000, tz=UTC).date()


def _add_business_days(day: date, n: int) -> date:
    """Soma `n` dias ÚTEIS (pula sábado/domingo) a `day`. Duplica
    `dpl.providers.dxy._add_business_days` (mesma lógica, `date` em vez de
    `datetime`) para não acoplar este módulo puro/sem-rede à cadeia de
    imports do provider (que traz `predictor_core.net`). Usada aqui como
    predicado direto — "a observação `o`, publicada com `n` dias úteis de
    atraso, já estaria disponível na data `day`?" — em vez de tentar
    inverter a soma com uma subtração (armadilha: subtrair dias úteis de um
    dia de FIM DE SEMANA não é o inverso de somar dias úteis a partir de um
    dia útil, porque a soma pula o fim de semana adiante mas a subtração
    "recua" para o útil mais próximo sem saber que ir pra frente teria
    pulado esse mesmo fim de semana).

    CORREÇÃO 2026-09-05 (achado por auditoria externa): a implementação
    original usava `day - timedelta(days=n)` (dias CORRIDOS) como cutoff,
    e uma tentativa inicial de corrigir para dias úteis usando subtração
    ingênua (`day - n dias úteis`) ainda dava resultado ERRADO pra pontos de
    fim de semana — ex.: com lag=1 dia útil, o close de sexta só é publicado
    na segunda seguinte, mas `subtract_business_days(sábado, 1)` devolvia
    sexta como cutoff, permitindo usar o close de sexta num ponto de sábado
    (2 dias antes da publicação real). A checagem direta
    `_add_business_days(o, lag) <= day` não tem essa armadilha."""
    if n < 0:
        raise ValueError("n não pode ser negativo")
    d = day
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:  # 0=segunda ... 4=sexta
            added += 1
    return d


def build_macro_event_dummy(
    feature_vectors: list[FeatureVector],
    *,
    calendar_path: Path | None = None,
    window_days: int = 1,
    events: list[MacroEvent] | None = None,
) -> list[float]:
    """1.0 se o dia do ponto está a até `window_days` dias (antes OU depois,
    inclusive) de QUALQUER evento macro no calendário; 0.0 caso contrário.
    Combina FOMC/CPI/PPI com OR — o RegimeEngine recebe uma covariável escalar
    por ponto, não uma por tipo de evento.

    `events`: injeção direta para teste (evita reler o JSON); se omitido, carrega
    de `calendar_path` (ou do arquivo padrão do projeto).
    """
    if window_days < 0:
        raise ValueError("window_days não pode ser negativo")
    ev = events if events is not None else load_macro_calendar(calendar_path)
    event_dates = [e.event_date for e in ev]
    out = []
    for fv in feature_vectors:
        day = _ts_to_date(fv.timestamp_exchange_ms)
        in_window = any(abs((day - ed).days) <= window_days for ed in event_dates)
        out.append(1.0 if in_window else 0.0)
    return out


def build_dxy_return(
    feature_vectors: list[FeatureVector],
    dxy_daily_closes: dict[date, float],
    *,
    publish_lag_days: int = 1,
) -> list[float]:
    """Retorno percentual 1d do DXY, alinhado a `feature_vectors`, respeitando
    `publish_lag_days` EM DIAS ÚTEIS (o release H.10 do Fed sai com defasagem —
    mesma convenção conservadora de `DXYProvider._add_business_days`, não
    recalibrada aqui, agora consistente entre os dois módulos).

    Para o ponto no dia D, usa a observação `o` mais recente cuja data de
    publicação real (`o` + `publish_lag_days` dias úteis) já ocorreu em D ou
    antes, contra a observação anterior a essa — NUNCA uma cujo `date`
    publicado seja posterior a D. Cripto negocia fim de semana; usar dias corridos aqui subestimaria o lag
    real perto de sábado/domingo (bug real encontrado por auditoria em
    2026-09-05, corrigido nesta versão — ver `_add_business_days` para o
    porquê de usar checagem direta em vez de um cutoff único subtraído).
    Pontos sem dado DXY suficiente (início da série, ou lacuna na coleta)
    recebem 0.0 — é uma decisão CONSERVADORA (covariável neutra), não um erro
    silencioso: quem chama deve conferir a cobertura de `dxy_daily_closes`
    antes de treinar.
    """
    if publish_lag_days < 0:
        raise ValueError("publish_lag_days não pode ser negativo")
    available_dates = sorted(dxy_daily_closes)
    published = [(published_at(d, publish_lag_days), d) for d in available_dates]
    out = []
    for fv in feature_vectors:
        day = _ts_to_date(fv.timestamp_exchange_ms)
        usable = [d for d in available_dates if _add_business_days(d, publish_lag_days) <= day]
        if len(usable) < 2:
            out.append(0.0)
            continue
        latest, prev = usable[-1], usable[-2]
        c_latest, c_prev = dxy_daily_closes[latest], dxy_daily_closes[prev]
        out.append(0.0 if c_prev == 0 else (c_latest - c_prev) / c_prev * 100.0)
    return out


def dxy_coverage(
    feature_vectors: list[FeatureVector],
    dxy_daily_closes: dict[date, float],
    *,
    publish_lag_days: int = 1,
) -> tuple[int, int]:
    """`(n_pontos_imputados, n_pontos_total)` para a mesma entrada que
    `build_dxy_return` receberia.

    O 0.0 que `build_dxy_return` devolve em lacuna NÃO é neutro: entra no
    `StandardScaler` ajustado no IS e vira uma posição concreta da distribuição,
    então uma cobertura ruim ensina o HMM um "estado de dado faltante"
    disfarçado de regime. Esta função existe para que essa fração seja MEDIDA
    antes do treino em vez de permanecer invisível — deliberadamente separada,
    para não alterar o valor numérico que `build_dxy_return` já produz (o
    veredito fechado do H9 e o pré-registro do H7 dependem dele estável).
    """
    if publish_lag_days < 0:
        raise ValueError("publish_lag_days não pode ser negativo")
    published = [published_at(d, publish_lag_days) for d in sorted(dxy_daily_closes)]
    imputados = sum(
        1
        for fv in feature_vectors
        if sum(1 for pub in published if pub <= _ts_to_date(fv.timestamp_exchange_ms)) < 2
    )
    return imputados, len(feature_vectors)


def load_dxy_daily_closes(path: Path) -> dict[date, float]:
    """Lê um CSV local de 2 colunas (`date,close`) com o histórico do DXY, coletado
    offline via `DXYProvider` (ou o `fredgraph.csv` bruto do FRED). Não busca nada
    na rede — só materializa um cache local em `dict[date, float]` pra
    `build_dxy_return` consumir. Levanta ValueError em linha malformada (falha
    alto: um preço mal-parseado silenciosamente vira uma covariável errada)."""
    out: dict[date, float] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            if len(row) != 2:
                raise ValueError(f"{path}: linha malformada {row!r} (esperado date,close)")
            raw_date, raw_close = row
            try:
                d = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
                c = float(raw_close)
            except ValueError as exc:
                raise ValueError(f"{path}: linha inválida {row!r}") from exc
            out[d] = c
    if not out:
        raise ValueError(f"{path}: nenhum dado válido lido (header={header!r})")
    return out


__all__ = [
    "build_dxy_return",
    "dxy_coverage",
    "build_macro_event_dummy",
    "load_dxy_daily_closes",
]
