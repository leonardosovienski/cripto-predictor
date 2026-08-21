"""Controle positivo OFICIAL dos juízes da plataforma — emite o atestado do registry.

Substitui a validação ad-hoc ("NO-GO correto em ruído", jun/2026) pelo
testing.harness canônico do predictor_core. DOIS juízes são certificados
(2026-07-10: antes só o do V3 — mas o registry governa trials das duas famílias,
e a H5 é julgada pelo caminho da Fase 1):

  1. JUIZ DO V3 — critérios PSR >= 0.80 e IC_lower > 0 do backtest_v3.
  2. JUIZ DA FASE 1 — o critério de validação do analyzers/backtest: Spearman
     (score, retorno) com IC95 por block bootstrap que NÃO cruza zero.

Cada um sobre séries sintéticas com verdade conhecida:

  - EDGE:  sinal correlacionado ao retorno futuro (skill plantado) → o juiz TEM
           que dizer GO/VALIDADO (sensibilidade; juiz cego = inútil).
  - RUÍDO: sinal independente do retorno → o juiz NÃO pode validar
           (especificidade; juiz que fabrica significância = pior que inútil).

Passando nos QUATRO braços (2 juízes × edge/ruído), o harness grava DOIS
atestados irmãos do trials.json — um por juiz/família, cada um com sua própria
`metric` (contrato do registry, core 2.0.0+): `trials.harness_attestation.json`
(juiz V3, metric="psr") e `trials.phase1_harness_attestation.json` (juiz Fase 1,
metric="spearman_ic"). Sem o atestado correspondente, registrar trial NOVA no
Experiment Registry é erro (trava de poder do core v1.1.0). Determinístico
(seeds fixos): re-rodar reproduz o veredito.

Uso:
    python scripts/attest_harness.py            # roda e grava os atestados
    python scripts/attest_harness.py --dry-run  # só roda o controle, não grava
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from predictor_core.measurement.stats import (  # noqa: E402
    probabilistic_sharpe_ratio,
    spearman_block_ci,
)
from predictor_core.measurement.trials import attestation_path_for  # noqa: E402
from predictor_core.testing.harness import (  # noqa: E402
    assert_pipeline_has_power,
    attest_pipeline_power,
)

TRIALS_PATH = ROOT / "GarimpoInvestimentos" / "trials.json"
PHASE1_ATTESTATION_PATH = TRIALS_PATH.with_name(
    TRIALS_PATH.stem + ".phase1_harness_attestation.json"
)

# Nomes de métrica: contrato com o Experiment Registry (measurement.trials).
# Trocar qualquer um dos dois é decisão de nomenclatura, não refactor livre —
# toda trial NOVA registrada contra o atestado correspondente tem que declarar
# exatamente o mesmo nome, senão o registry levanta MetricMismatchError.
#   "psr"         — juiz V3 (backtest_v3): PSR>=0.80 & IC_lower>0 sobre P&L do
#                   sinal. PSR é o limiar nomeado em todo H1/H2/H3
#                   (docs/HYPOTHESES.md) e no HANDOFF — nome já de fato usado.
#   "spearman_ic" — juiz da Fase 1 (analyzers/backtest._report): Spearman(score,
#                   retorno) com IC95 por block bootstrap. Não usei "ic" puro
#                   para não colidir com as variáveis ic_lower/ic_upper (bounds
#                   de IC, não o nome da métrica) já estabelecidas no código.
_METRIC_V3 = "psr"
_METRIC_PHASE1 = "spearman_ic"

# Mesmos limiares do backtest_v3 (o juiz REAL, não uma cópia amaciada).
_PSR_THRESHOLD = 0.80


def judge_go_nogo(pairs: list[tuple[float, float]]) -> dict:
    """O juiz do V3 destilado: GO exige PSR >= 0.80 E IC_lower > 0 sobre pares
    (sinal, retorno_forward) — os mesmos critérios de run_wfa."""
    returns = [s * r for s, r in pairs]  # P&L de seguir o sinal
    psr = probabilistic_sharpe_ratio(returns)
    _rho, lo, _hi = spearman_block_ci(pairs)
    go = (
        psr == psr
        and psr >= _PSR_THRESHOLD  # psr==psr descarta nan
        and lo is not None
        and lo > 0
    )
    return {"verdict": "GO" if go else "NO-GO", "psr": psr, "ic_lower": lo}


def judge_phase1(pairs: list[tuple[float, float]]) -> dict:
    """O juiz da Fase 1 destilado (analyzers/backtest._report): 'validado' exige
    Spearman com IC95 (block bootstrap) que não cruza zero, na direção positiva —
    o mesmo critério pré-registrado da H4/H5."""
    rho, lo, _hi = spearman_block_ci(pairs)
    ok = rho is not None and lo is not None and lo > 0
    return {"verdict": "VALIDADO" if ok else "RUIDO", "spearman": rho, "ic_lower": lo}


def phase1_edge_series(n: int = 120, seed: int = 21) -> list[tuple[float, float]]:
    """Scores 0-100 com skill plantado: score alto tende a preceder retorno alto
    (mesma escala do pipeline real; n na ordem de meses de coleta, não anos)."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        fwd = rng.gauss(0.0, 4.0)  # var % em D+7
        score = 50 + 8 * (1 if fwd > 0 else -1) + rng.gauss(0.0, 12.0)
        out.append((max(0.0, min(100.0, score)), fwd))
    return out


def phase1_noise_series(n: int = 120, seed: int = 22) -> list[tuple[float, float]]:
    """Scores independentes do retorno — validar aqui é significância fabricada."""
    rng = random.Random(seed)
    return [(max(0.0, min(100.0, rng.gauss(50.0, 15.0))), rng.gauss(0.0, 4.0)) for _ in range(n)]


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


def _expira_em(dias: float) -> bool:
    """Algum dos dois atestados expira dentro de `dias`? Ausente ou ilegivel
    conta como EXPIRADO — na duvida, renovar (o controle positivo roda de novo e
    o custo e de segundos), nunca assumir validade."""
    from datetime import UTC, datetime, timedelta

    limite = datetime.now(UTC) + timedelta(days=dias)
    for caminho in (attestation_path_for(TRIALS_PATH), PHASE1_ATTESTATION_PATH):
        if not caminho.exists():
            return True
        try:
            expira = json.loads(caminho.read_text(encoding="utf-8"))["expires_at"]
            if datetime.fromisoformat(expira) <= limite:
                return True
        except (OSError, ValueError, KeyError):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Controle positivo dos juizes GO/NO-GO (V3) e VALIDADO/RUIDO (Fase 1)"
    )
    ap.add_argument("--dry-run", action="store_true", help="roda sem gravar os atestados")
    ap.add_argument(
        "--if-expiring-within",
        type=float,
        metavar="DIAS",
        help="so roda se ALGUM atestado expira dentro de DIAS (ou ja expirou/nao existe). "
        "Existe para agendamento: a validade e de 7 dias e a renovacao era 100%% manual, "
        "entao um job diario com --if-expiring-within 2 renova sozinho sem gravar todo dia. "
        "NAO afrouxa nada: o atestado so e gravado se o controle positivo PASSAR, como sempre.",
    )
    args = ap.parse_args()

    if args.if_expiring_within is not None and not _expira_em(args.if_expiring_within):
        print(
            f"atestados validos por mais de {args.if_expiring_within:g} dia(s) — "
            "nada a fazer (use sem --if-expiring-within para forcar)"
        )
        return 0

    if args.dry_run:
        # Juiz da Fase 1 primeiro: se ele não tem poder, nenhum atestado deveria
        # existir (o registry governa trials das DUAS famílias). Só o V3 passar
        # não basta.
        assert_pipeline_has_power(
            judge_phase1,
            phase1_edge_series,
            phase1_noise_series,
            edge_verdict="VALIDADO",
            null_verdict="RUIDO",
        )
        print("juiz Fase 1 (Spearman IC95): sensibilidade e especificidade OK")
        assert_pipeline_has_power(judge_go_nogo, edge_series, noise_series, edge_verdict="GO")
        print("juiz V3 (PSR & IC_lower): sensibilidade e especificidade OK")
        print("controle positivo PASSOU (dry-run; atestados nao gravados)")
        return 0

    # Cada juiz grava o SEU atestado, com a SUA metrica — arquivos irmaos
    # distintos, um por familia de trial (measurement/trials.py so casa uma
    # trial nova contra o atestado cujo metric+pipeline_fingerprint batem).
    rec_phase1 = attest_pipeline_power(
        judge_phase1,
        phase1_edge_series,
        phase1_noise_series,
        attestation_path=PHASE1_ATTESTATION_PATH,
        note="Juiz da Fase 1 (analyzers/backtest._report): VALIDADO/RUIDO via "
        "Spearman IC95 block bootstrap nao cruza zero, seeds 21/22, n=120 "
        "— edge plantado e ruido",
        edge_verdict="VALIDADO",
        null_verdict="RUIDO",
        metric=_METRIC_PHASE1,
    )
    print("juiz Fase 1 (Spearman IC95): sensibilidade e especificidade OK")
    print(f"atestado da Fase 1 gravado em {PHASE1_ATTESTATION_PATH} ({rec_phase1['passed_at']})")

    rec_v3 = attest_pipeline_power(
        judge_go_nogo,
        edge_series,
        noise_series,
        attestation_path=attestation_path_for(TRIALS_PATH),
        note="Juiz V3 (backtest_v3): GO/NO-GO via PSR>=0.80 & IC_lower>0, "
        "seeds 7/8, n=400 — edge plantado e ruido",
        edge_verdict="GO",
        metric=_METRIC_V3,
    )
    print("juiz V3 (PSR & IC_lower): sensibilidade e especificidade OK")
    print(
        f"controle positivo PASSOU — atestado gravado em "
        f"{attestation_path_for(TRIALS_PATH)} ({rec_v3['passed_at']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
