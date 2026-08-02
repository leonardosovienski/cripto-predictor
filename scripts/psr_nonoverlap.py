"""C2 (auditoria 2026-07-09): re-verificacao do PSR sem sobreposicao de janelas.

O WFA gera um sinal a cada 8h avaliado contra o retorno forward de 24h - cada
retorno compartilha ~2/3 da janela com o vizinho. O PSR (e o Sharpe) tratam a
serie como observacoes independentes, o que INFLA a significancia. O IC do
Spearman ja usa block bootstrap (imune); o PSR nao tinha correcao.

Metodo: a serie OOS persistida em wfa_returns.json preserva a ordem de geracao
(cadencia 8h). Subamostrando i::3 obtem-se 3 sub-series (offsets 00h/08h/16h)
cujos retornos de 24h NAO se sobrepoem dentro de cada sub-serie. O PSR e
recomputado em cada uma; o veredicto so se sustenta se as tres aprovarem.

Nota de honestidade: kelly_fraction nao afeta o PSR (escala linear de retorno,
PSR/Sharpe sao invariantes de escala) - a serie salva (kelly=1.0) vale para
qualquer fracao homologada.

Uso:
    python scripts/psr_nonoverlap.py [--symbol BTCUSDT] [--threshold 0.80]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from predictor_core.stats import probabilistic_sharpe_ratio  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="PSR em sub-series nao sobrepostas (C2)")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--threshold", type=float, default=0.80)
    args = ap.parse_args()

    path = ROOT / "data" / "v3" / args.symbol / "wfa_returns.json"
    if not path.exists():
        print(f"{path} nao existe - rode o backtest_v3 primeiro")
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    net = data["net"]

    print(
        f"C2 - PSR sem sobreposicao [{args.symbol}]  "
        f"(serie salva: kelly={data['kelly_fraction']}, "
        f"fee={data['taker_fee_bps']}bps, n={len(net)})"
    )
    print(f"{'serie':<22}{'n':>6}{'n ativos':>10}{'PSR':>8}  veredicto (>= {args.threshold})")

    def linha(nome, serie):
        ativos = sum(1 for r in serie if r != 0.0)
        psr = probabilistic_sharpe_ratio(serie) if len(serie) >= 3 else float("nan")
        ok = "PASSA" if psr >= args.threshold else "REPROVA"
        print(f"{nome:<22}{len(serie):>6}{ativos:>10}{psr:>8.3f}  {ok}")
        return psr

    original = linha("original (8h, sobrep.)", net)
    subs = [linha(f"offset {off} (24h puros)", net[off::3]) for off in range(3)]

    aprovadas = sum(1 for p in subs if p >= args.threshold)
    print(
        f"\noriginal: {original:.3f} | sub-series: "
        + ", ".join(f"{p:.3f}" for p in subs)
        + f" | {aprovadas}/3 aprovadas"
    )
    if aprovadas == 3:
        print("VEREDICTO C2: GO SOBREVIVE sem sobreposicao.")
    elif aprovadas == 0:
        print(
            "VEREDICTO C2: GO NAO sobrevive - PSR original estava inflado "
            "pela sobreposicao. Rediscutir a decisao de capital."
        )
    else:
        print(
            "VEREDICTO C2: AMBIGUO - parte das sub-series reprova. Tratar "
            "como evidencia enfraquecida; nao promover a capital real sem "
            "investigacao (ver tambem IC do Spearman, que e imune)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
