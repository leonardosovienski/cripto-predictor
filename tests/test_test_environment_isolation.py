"""Direct pytest collection must not inherit the operator's environment."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_collection_isolates_credentials_config_and_durable_state(tmp_path):
    project = Path(__file__).resolve().parents[1]
    operator = tmp_path / "operator"
    operator.mkdir()
    private = operator / "private.env"
    private.write_text("COINGECKO_API_KEY=test-private-config-unused\n", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        CRIPTO_ROOT=str(tmp_path),
        CRIPTO_ENV_FILE=str(private),
        GEMINI_API_KEY="test-inherited-credential-unused",
        COINGECKO_API_KEY="test-inherited-optional-unused",
        PYTHONPATH=str(project),
    )
    for key in ("DATA_DIR", "OUTPUT_DIR", "CACHE_DIR", "LOGS_DIR", "PREDICTOR_OPS_STATE_DIR"):
        env[key] = str(operator)
    env["PREDICTOR_EVENTS_PATH"] = str(operator / "events.jsonl")
    code = """
import json, os, runpy
from pathlib import Path
runpy.run_path('tests/conftest.py')
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.core import api_guard
api_guard.allow('ingest', 'assets', 1)
print(json.dumps({
    'synthetic': settings.GEMINI_API_KEY == 'test-gemini-key-for-unit-tests-only',
    'optional_empty': not settings.COINGECKO_API_KEY,
    'dotenv': str(settings.model_config['env_file']),
    'paths': {k: os.environ[k] for k in (
        'DATA_DIR','OUTPUT_DIR','CACHE_DIR','LOGS_DIR',
        'PREDICTOR_OPS_STATE_DIR','PREDICTOR_EVENTS_PATH')},
}))
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout.splitlines()[-1])
    assert observed["synthetic"]
    assert observed["optional_empty"]
    assert Path(observed["dotenv"]) != private
    for path in observed["paths"].values():
        assert Path(path).is_relative_to(tmp_path)
        assert not Path(path).is_relative_to(operator)
    assert sorted(p.name for p in operator.iterdir()) == ["private.env"]
