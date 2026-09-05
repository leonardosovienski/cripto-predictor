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


class FrozenFamilyError(ValueError):
    """Tentativa de registrar uma trial numa família congelada do charter.

    Reabrir uma família congelada não é proibido em absoluto — é proibido em
    SILÊNCIO. O caminho legítimo passa por `scripts/check_reopen_dossier.py`,
    que exige um dossiê de reabertura revisado.
    """


def _reject_frozen_family(
    name: str,
    params: dict,
    frozen_families: tuple[str, ...],
    existing_names: set[str],
) -> None:
    """Barra o registro de uma trial NOVA cuja `params["family"]` esteja congelada.

    Fecha o buraco achado na auditoria de 2026-09-05: até então o congelamento
    era aplicado por NOME (só as trials das hipóteses fechadas), nunca por
    FAMÍLIA. Bastava um nome novo — `v3-hmm-funding-oi-fr45-reopen` com
    `family="funding_oi_hmm_v3"` — para reparametrizar a família congelada
    H1-H3 e o registro aceitava. O único guardião de família era
    `scripts/check_reopen_dossier.py`: manual, opt-in, e nunca invocado pelo CI.
    O caminho de escrita do core (verificado no wheel 3.0.0 pinado) não conhece
    `frozen_families` de propósito — ele é neutro quanto a este charter, então a
    checagem pertence a esta fachada, junto da de hipótese fechada.

    Só vale para trial NOVA (nome ainda não registrado). Atualizar uma trial que
    já existe é como um veredito é REGISTRADO — foi assim que o H9 foi fechado,
    re-registrando o mesmo nome com `sharpe` e `notes` preenchidos. Bloquear
    isso impediria fechar uma hipótese aberta de família congelada, que é o
    oposto do objetivo. A imutabilidade de `params`/`metric` no core já impede
    que um update vire reparametrização disfarçada.

    Ressalva honesta: isto fecha o caso HONESTO — quem declara a família
    corretamente é barrado. Não substitui o dossiê manual contra quem omita ou
    renomeie a `family` de propósito para escapar do guard.
    """
    if name in existing_names:
        return
    family = params.get("family")
    if family and family in frozen_families:
        raise FrozenFamilyError(
            f"trial nova {name!r} declara family={family!r}, que está CONGELADA "
            f"(frozen_families no charter). Reparametrizar uma família congelada "
            f"exige dossiê de reabertura revisado — veja "
            f"scripts/check_reopen_dossier.py --family {family}."
        )


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
            state.hypothesis_trials[h] for h, status in state.hypotheses.items() if status.is_closed
        }
        if name in closed_trials:
            raise ValueError(f"trial {name!r} pertence a hipótese fechada e não pode ser reescrita")

        # ACHADO DE AUDITORIA EXTERNA (2026-09-05): o core valida colisão de
        # NOME e imutabilidade de params/metric — mas nunca inspeciona
        # `params["family"]` nem `frozen_families`. Registrar uma trial NOVA
        # (nome diferente) com `family` igual a uma família congelada (ex.:
        # `funding_oi_hmm_v3`, H1-H3) passava batido: o único guardião era
        # `scripts/check_reopen_dossier.py`, manual e nunca chamado pelo CI.
        # Este guard fecha o caso HONESTO (quem declara a família congelada
        # corretamente é barrado aqui) — não substitui o dossiê manual para
        # reaberturas disfarçadas com family omitido ou renomeado.
        existing_names = {t["name"] for t in load_trials(target)}
        frozen_family = params.get("family")
        if (
            name not in existing_names
            and frozen_family is not None
            and frozen_family in state.frozen_families
        ):
            raise ValueError(
                f"trial nova {name!r} declara family={frozen_family!r}, que está em "
                f"frozen_families ({state.frozen_families}) — família congelada não pode "
                "receber trial nova silenciosamente. Reabertura exige dossiê explícito "
                "(scripts/check_reopen_dossier.py) e decisão do dono, não um registro comum."
            )
    return _core_register(name, params=params, sharpe=sharpe, notes=notes, path=target, **extra)
