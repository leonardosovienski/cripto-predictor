"""Calibração por juiz (B11a em docs/HYPOTHESES.md) — descritivo, não preditivo.

A H5 distribui ativos entre 4 juízes por partição FIXA (sha256 do nome do ativo,
`provider_for_asset`), sob a premissa implícita de que juízes distintos trazem
diversificação. Este módulo mede a parte dessa premissa que o dado existente
consegue responder.

O QUE ELE NÃO MEDE, e por quê: concordância entre juízes. A partição é
determinística — o mesmo ativo cai SEMPRE no mesmo provedor —, então não existe
nenhuma observação pareada (dois juízes, mesmo ativo, mesma data) em toda a
coorte. A ausência é por desenho, não por falta de coleta. Medir concordância
exigiria atribuição sobreposta, o que muda a coleta e portanto é trial nova com
pré-registro (B11b). Reportar aqui uma "correlação entre juízes" calculada por
pareamento de índice ou por data seria inventar pareamento que não existe.

O QUE ELE MEDE: se os juízes usam a MESMA RÉGUA. Nível médio do score, dispersão
e fração acima do limiar são comparáveis entre juízes mesmo sem pareamento,
porque descrevem a distribuição marginal de cada um. Se as réguas diferem, o
pooled da H5 combina estimadores não-calibrados entre si — o que NÃO invalida o
veredito já emitido (o critério pré-registrado julgava o pooled e foi executado
como estava), mas qualifica sua leitura.

NÃO é gate, não escreve em trials.json, não altera veredito nenhum.

Uso:
    python -m GarimpoInvestimentos.analyzers.judge_calibration
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from GarimpoInvestimentos.analyzers.backtest import _load_rows
from GarimpoInvestimentos.config import settings


@dataclass(frozen=True)
class JudgeStats:
    juiz: str
    n: int
    media: float
    desvio: float
    mediana: float
    minimo: float
    maximo: float
    frac_acima_limiar: float
    frac_abaixo_invertido: float
    n_ativos: int


def _desvio(valores: Sequence[float], media: float) -> float:
    if len(valores) < 2:
        return 0.0
    return math.sqrt(sum((x - media) ** 2 for x in valores) / (len(valores) - 1))


def _mediana(valores: Sequence[float]) -> float:
    ordenado = sorted(valores)
    n = len(ordenado)
    if not n:
        return 0.0
    meio = n // 2
    return ordenado[meio] if n % 2 else (ordenado[meio - 1] + ordenado[meio]) / 2


def calibration_by_judge(
    rows: list[dict], *, limiar: float | None = None
) -> tuple[JudgeStats, ...]:
    """Estatística marginal do score por juiz. `juiz` é o carimbo canônico
    (provider:modelo:hash-do-prompt); o provedor é o primeiro campo."""
    thr = settings.LIMIAR_SCORE_MINIMO if limiar is None else limiar
    por_juiz: dict[str, list[float]] = defaultdict(list)
    ativos: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        juiz = (r.get("juiz") or "").split(":", 1)[0] or "desconhecido"
        score = r.get("score")
        if score is None:
            continue
        por_juiz[juiz].append(float(score))
        ativos[juiz].add(r.get("ativo", ""))

    saida = []
    for juiz in sorted(por_juiz):
        vals = por_juiz[juiz]
        media = sum(vals) / len(vals)
        saida.append(
            JudgeStats(
                juiz=juiz,
                n=len(vals),
                media=round(media, 2),
                desvio=round(_desvio(vals, media), 2),
                mediana=round(_mediana(vals), 2),
                minimo=min(vals),
                maximo=max(vals),
                frac_acima_limiar=round(sum(1 for v in vals if v >= thr) / len(vals), 4),
                frac_abaixo_invertido=round(sum(1 for v in vals if v <= 100 - thr) / len(vals), 4),
                n_ativos=len(ativos[juiz]),
            )
        )
    return tuple(saida)


def spread(stats: Sequence[JudgeStats]) -> dict[str, float] | None:
    """Amplitude entre juízes. É o número que responde a pergunta prática:
    'as réguas diferem?'. None com menos de 2 juízes — comparar exige ao menos
    duas coisas a comparar."""
    if len(stats) < 2:
        return None
    medias = [s.media for s in stats]
    fracs = [s.frac_acima_limiar for s in stats]
    return {
        "amplitude_media": round(max(medias) - min(medias), 2),
        "amplitude_frac_acima_limiar": round(max(fracs) - min(fracs), 4),
    }


def render(stats: Sequence[JudgeStats], limiar: float) -> str:
    if not stats:
        return "CALIBRACAO POR JUIZ\n  (sem previsoes gravadas)"
    linhas = [
        "CALIBRACAO POR JUIZ (descritivo — nao e gate, nao altera veredito)",
        f"  limiar de referencia: {limiar:g}  |  leitura invertida: <= {100 - limiar:g}",
        "",
        f"  {'juiz':<12}{'n':>6}{'ativos':>8}{'media':>8}{'desvio':>8}"
        f"{'mediana':>9}{'>=lim':>8}{'<=inv':>8}",
        f"  {'-' * 67}",
    ]
    for s in stats:
        linhas.append(
            f"  {s.juiz:<12}{s.n:>6}{s.n_ativos:>8}{s.media:>8.1f}{s.desvio:>8.1f}"
            f"{s.mediana:>9.1f}{s.frac_acima_limiar:>8.1%}{s.frac_abaixo_invertido:>8.1%}"
        )
    sp = spread(stats)
    if sp:
        linhas += [
            "",
            f"  amplitude entre juizes: media {sp['amplitude_media']:+.1f} pontos, "
            f"fracao >= limiar {sp['amplitude_frac_acima_limiar']:.1%}",
        ]
    linhas += [
        "",
        "  CONCORDANCIA entre juizes NAO e computavel deste dado: a particao e fixa",
        "  (cada ativo tem sempre o mesmo juiz), entao nao ha observacao pareada.",
        "  Medi-la exigiria atribuicao sobreposta = coleta nova = trial nova (B11b).",
    ]
    return "\n".join(linhas)


def main() -> int:
    rows = _load_rows()
    stats = calibration_by_judge(rows)
    print(render(stats, settings.LIMIAR_SCORE_MINIMO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
