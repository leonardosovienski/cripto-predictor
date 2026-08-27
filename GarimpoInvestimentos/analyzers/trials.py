"""COMPAT SHIM — o Experiment Registry foi RECONCILIADO no predictor_core (2026-07-09).

Esta era a versão evoluída (schema formal, governança N+1) que divergiu da cópia
original do core — o drift que a meta-auditoria pegou. A evolução foi re-promovida
ao canônico (predictor_core/measurement/trials.py, v1.1.0) e este módulo virou
fachada fina, preservando o default histórico do caminho (trials.json versionado
dentro do pacote). Mesmo padrão dos shims do circuit_breaker (Onda 3).

Novidade herdada do core: criar trial NOVA agora exige o atestado de controle
positivo (testing.harness.attest_pipeline_power) — o arquivo irmão
`trials.harness_attestation.json` é emitido por `scripts/attest_harness.py`,
que prova que o juiz GO/NO-GO detecta edge plantado e rejeita ruído.
"""

from pathlib import Path

from predictor_core.measurement.trials import (  # noqa: F401 — re-export
    PowerAttestationMissingError,
    attestation_path_for,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    validate_trials,
)
from predictor_core.measurement.trials import load_trials as _core_load
from predictor_core.measurement.trials import register_trial as _core_register

# Versionado junto do código (dentro do pacote) — viaja com o repositório.
TRIALS_PATH = Path(__file__).resolve().parent.parent / "trials.json"


def load_trials(path: Path | None = None) -> list[dict]:
    target = path or TRIALS_PATH
    trials = _core_load(target)
    errors = validate_trials(trials)
    if errors:
        raise ValueError(f"{target}: trials.json inválido: " + "; ".join(errors))
    return trials


def register_trial(
    name: str,
    *,
    params: dict,
    sharpe: float | None = None,
    notes: str = "",
    path: Path | None = None,
    **extra,
) -> list[dict]:
    target = path or TRIALS_PATH
    if Path(target).resolve() == TRIALS_PATH.resolve() and Path(target).exists():
        # The registry and scientific charter are one governance boundary.
        # Toda hipótese semanticamente fechada é imutável; o core protege
        # identidade/métrica, mas deliberadamente não conhece este charter.
        from GarimpoInvestimentos.governance import load_scientific_state

        state = load_scientific_state()
        closed_trials = {
            state.hypothesis_trials[h]
            for h, status in state.hypotheses.items()
            if status.is_closed
        }
        if name in closed_trials:
            raise ValueError(
                f"trial {name!r} pertence a hipótese fechada e não pode ser reescrita"
            )
    return _core_register(
        name, params=params, sharpe=sharpe, notes=notes, path=target, **extra
    )
