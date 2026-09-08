"""Credenciais sintéticas e paths temporários para testes offline."""

import os
import pathlib

ROOT = pathlib.Path(__file__).parent.parent

# Injetar credenciais mínimas ANTES que qualquer módulo que importe config.py
# seja coletado. A trava P0 exige ≥ 16 chars e não-placeholder. Estes valores
# são válidos para testes offline — nunca chegam à rede.
_TEST_CREDS = {
    "GEMINI_API_KEY": "test-gemini-key-for-unit-tests-only",
    "OPENAI_API_KEY": "test-openai-key-for-unit-tests-only",
    "SERP_API_KEY": "test-serp-key-for-unit-tests-only-xx",
    "LLM_PROVIDER": "gemini",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "OPENAI_MODEL": "gpt-4o-mini",
    "LIMIAR_SCORE_MINIMO": "60",
    "DEFAULT_ASSETS": "bitcoin,ethereum",
    "CACHE_TTL_HOURS": "6",
    "ENABLE_CACHE": "true",
    "SCORE_HORIZON_DAYS": "7",
}
for _k, _v in _TEST_CREDS.items():
    os.environ.setdefault(_k, _v)

# emit_event agora é chamado por cache.py/logger.py durante os testes — redireciona
# o JSONL para a pasta de build dos testes para não poluir o cwd do projeto.
os.environ.setdefault("PREDICTOR_EVENTS_PATH", str(ROOT / "tests" / "_events_test.jsonl"))


import pytest


@pytest.fixture
def registry_attestation(tmp_path):
    """Executa o juiz real sobre controles sintéticos; só escreve no tmp do teste."""
    from predictor_core.testing.harness import attest_pipeline_power

    from scripts.attest_harness import judge_phase1, phase1_edge_series, phase1_noise_series

    def emit(path):
        att = path.with_name(path.stem + ".phase1_harness_attestation.json")
        record = attest_pipeline_power(
            judge_phase1,
            phase1_edge_series,
            phase1_noise_series,
            attestation_path=att,
            edge_verdict="VALIDADO",
            null_verdict="RUIDO",
            metric="spearman_ic",
            repo=tmp_path,
            note="Controle real do juiz em fixture sintética; não autoriza registro canônico.",
        )
        return {
            "metric": "spearman_ic",
            "power_attestation": att,
            "pipeline_fingerprint": record["pipeline_fingerprint"],
        }

    return emit
