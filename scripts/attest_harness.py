"""Controle positivo OFICIAL do juiz GO/NO-GO — emite o atestado do registry.

Substitui a validação ad-hoc ("NO-GO correto em ruído", jun/2026) pelo
testing.harness canônico do predictor_core. O que é certificado aqui é o JUIZ
ESTATÍSTICO do V3 — os critérios PSR >= 0.80 e IC_lower > 0 usados pelo
backtest_v3 — sobre séries sintéticas com verdade conhecida:

  - EDGE:  sinal correlacionado ao retorno futuro (skill plantado) → o juiz TEM
           que dizer GO (sensibilidade; juiz cego = inútil).
  - RUÍDO: sinal independente do retorno → o juiz NÃO pode dizer GO
           (especificidade; juiz que fabrica significância = pior que inútil).

Passando nos dois braços, o harness grava o atestado irmão do trials.json —
sem ele, registrar trial NOVA no Experiment Registry é erro (trava de poder do
core v1.1.0). Determinístico (seeds fixos): re-rodar reproduz o veredito.

Uso:
    python scripts/attest_harness.py            # roda e grava o atestado
    python scripts/attest_harness.py --dry-run  # só roda o controle, não grava
"""
import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from predictor_core.measurement.stats import (          # noqa: E402
    probabilistic_sharpe_ratio, spearman_block_ci)
from predictor_core.measurement.trials import attestation_path_for  # noqa: E402
from predictor_core.testing.harness import (            # noqa: E402
    assert_pipeline_has_power, attest_pipeline_power)

TRIALS_PATH = ROOT / "GarimpoInvestimentos" / "trials.json"

# Mesmos limiares do backtest_v3 (o juiz REAL, não uma cópia amaciada).
_PSR_THRESHOLD = 0.80


def judge_go_nogo(pairs: list[tuple[float, float]]) -> dict:
    """O juiz do V3 destilado: GO exige PSR >= 0.80 E IC_lower > 0 sobre pares
    (sinal, retorno_forward) — os mesmos critérios de run_wfa."""
    returns = [s * r for s, r in pairs]                  # P&L de seguir o sinal
    psr = probabilistic_sharpe_ratio(returns)
    _rho, lo, _hi = spearman_block_ci(pairs)
    go = (psr == psr and psr >= _PSR_THRESHOLD           # psr==psr descarta nan
          and lo is not None and lo > 0)
    return {"verdict": "GO" if go else "NO-GO", "psr": psr, "ic_lower": lo}


def edge_series(n: int = 400, seed: int = 7) -> list[tuple[float, float]]:
    """Sinal com skill plantado: direção do retorno + ruído moderado."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        fwd = rng.gauss(0.0, 0.01)
        signal = (1.0 if fwd > 0 else -1.0) + rng.gauss(0.0, 0.8)
        out.append((signal, fwd))
    return out


def noise_series(n: int = 400, seed: int = 8) -> list[tuple[float, float]]:
    """Sinal independente do retorno — qualquer GO aqui é significância fabricada."""
    rng = random.Random(seed)
    return [(rng.gauss(0.0, 1.0), rng.gauss(0.0, 0.01)) for _ in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Controle positivo do juiz GO/NO-GO (V3)")
    ap.add_argument("--dry-run", action="store_true", help="roda sem gravar o atestado")
    args = ap.parse_args()

    if args.dry_run:
        assert_pipeline_has_power(judge_go_nogo, edge_series, noise_series,
                                  edge_verdict="GO")
        print("controle positivo PASSOU (dry-run; atestado nao gravado)")
        return 0
    rec = attest_pipeline_power(
        judge_go_nogo, edge_series, noise_series,
        attestation_path=attestation_path_for(TRIALS_PATH),
        note="juiz GO/NO-GO do backtest_v3 (PSR>=0.80 & IC_lower>0) sobre "
             "edge plantado e ruido; seeds 7/8, n=400",
        edge_verdict="GO")
    print(f"controle positivo PASSOU — atestado gravado em "
          f"{attestation_path_for(TRIALS_PATH)} ({rec['passed_at']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
