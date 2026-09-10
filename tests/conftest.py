"""Credenciais sintéticas e paths temporários para testes offline."""

import os
import pathlib
import tempfile

from GarimpoInvestimentos.local_runtime import local_root, within_root

ROOT = pathlib.Path(__file__).parent.parent

# Isolate before importing config/core paths, including direct pytest runs.
# Caller-provided paths and credentials may belong to the actual operator.
_local_root = local_root()
_scratch = within_root(_local_root, "operacao/temporarios") if _local_root else None
if _scratch is not None:
    _scratch.mkdir(parents=True, exist_ok=True)
_test_run = pathlib.Path(tempfile.mkdtemp(prefix="cripto-pytest-", dir=_scratch))
os.environ["CRIPTO_ROOT"] = str(_local_root or _test_run)
_dotenv = _test_run / "synthetic.env"
_dotenv.write_text("# Isolated offline tests; no private dotenv.\n", encoding="utf-8")
os.environ["CRIPTO_ENV_FILE"] = str(_dotenv)
for _name in ("DATA", "OUTPUT", "CACHE", "LOGS"):
    os.environ[_name + "_DIR"] = os.environ["GARIMPO_" + _name + "_DIR"] = str(
        _test_run / _name.lower()
    )
os.environ["PREDICTOR_OPS_STATE_DIR"] = str(_test_run / "state")
os.environ["PREDICTOR_EVENTS_PATH"] = str(_test_run / "events.jsonl")
for _name in list(os.environ):
    if any(part in _name.upper() for part in ("API_KEY", "AUTH_TOKEN", "API_SECRET", "SECRET_KEY")):
        os.environ.pop(_name)

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
    os.environ[_k] = _v


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
