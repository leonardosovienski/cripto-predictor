"""Real subprocess checks of the local profile, including rejected path escapes."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
PATH_VARIABLES = (
    "DATA_DIR",
    "OUTPUT_DIR",
    "CACHE_DIR",
    "LOGS_DIR",
    "GARIMPO_DATA_DIR",
    "GARIMPO_OUTPUT_DIR",
    "GARIMPO_CACHE_DIR",
    "GARIMPO_LOGS_DIR",
    "PREDICTOR_OPS_STATE_DIR",
    "PREDICTOR_EVENTS_PATH",
    "CRIPTO_ENV_FILE",
)


def run(root, code, **overrides):
    env = {k: v for k, v in os.environ.items() if k not in PATH_VARIABLES}
    env.update(CRIPTO_ROOT=str(root), PYTHONDONTWRITEBYTECODE="1", **overrides)
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=PROJECT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=40,
    )


def test_paths_settings_events_job_state_and_tempfile_share_the_root(tmp_path):
    root = tmp_path / "Cripto with spaces"
    result = run(
        root,
        """
import json, os, tempfile
from pathlib import Path
from GarimpoInvestimentos.core import paths
from GarimpoInvestimentos.config import settings
from GarimpoInvestimentos.jobs import _state_root
with tempfile.NamedTemporaryFile() as f:
    temp = f.name
    f.write(b'local scratch')
    f.flush()
    assert Path(temp).is_file()
items = {name: str(getattr(paths, name)) for name in ('DATA_DIR','OUTPUT_DIR','CACHE_DIR','LOGS_DIR','FEATURE_STORE_DB')}
items.update(settings_output=str(settings.OUTPUT_DIR), state=str(_state_root()), temp=temp, events=os.environ['PREDICTOR_EVENTS_PATH'])
print(json.dumps(items))
""",
    )
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert all(Path(value).is_relative_to(root) for value in values.values())
    assert values["OUTPUT_DIR"] == values["settings_output"]
    assert values["state"] == str(root / "operacao/estado")


@pytest.mark.parametrize("name", PATH_VARIABLES)
def test_external_path_fails_before_creating_any_operational_directory(tmp_path, name):
    root, outside = tmp_path / "Cripto", tmp_path / "outside"
    result = run(root, "from GarimpoInvestimentos.core import paths", **{name: str(outside)})
    assert result.returncode != 0
    assert "fora de CRIPTO_ROOT" in result.stderr
    assert not outside.exists()
    assert not (root / "operacao").exists()


def test_relative_output_is_resolved_under_root_not_process_cwd(tmp_path):
    result = run(
        tmp_path,
        "from GarimpoInvestimentos.core.paths import OUTPUT_DIR; print(OUTPUT_DIR)",
        OUTPUT_DIR="custom/reports",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(tmp_path / "custom/reports")
    escape = run(tmp_path, "from GarimpoInvestimentos.core import paths", OUTPUT_DIR="../escape")
    assert escape.returncode != 0


def test_pipeline_output_flag_cannot_escape_root(tmp_path):
    outside = tmp_path / "outside"
    code = f"import sys; sys.argv=['cripto-predictor','--output-dir',{str(outside)!r}]; from GarimpoInvestimentos.cli import main; main()"
    result = run(tmp_path / "Cripto", code)
    assert result.returncode != 0
    assert "fora de CRIPTO_ROOT" in result.stderr
    assert not outside.exists()


def test_root_env_file_is_loaded_without_exporting_credentials(tmp_path):
    config = tmp_path / "configuracao/pipeline.env"
    config.parent.mkdir()
    config.write_text(
        "GEMINI_API_KEY=test-gemini-key-for-local-runtime-only\nSERP_API_KEY=test-serp-key-for-local-runtime-only\n",
        encoding="utf-8",
    )
    result = run(
        tmp_path,
        """
import os
os.environ.pop('GEMINI_API_KEY', None)
os.environ.pop('SERP_API_KEY', None)
from GarimpoInvestimentos.config import settings
assert settings.GEMINI_API_KEY and settings.SERP_API_KEY
assert 'GEMINI_API_KEY' not in os.environ
print('CONFIG_LOADED_WITHOUT_SECRET_OUTPUT')
""",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "CONFIG_LOADED_WITHOUT_SECRET_OUTPUT"


def test_marker_activates_profile_without_environment_variable(tmp_path):
    marker = tmp_path / ".cripto-root"
    marker.write_text(str(tmp_path / "Cripto"), encoding="utf-8")
    result = run(
        tmp_path,
        f"""
import os
from pathlib import Path
from GarimpoInvestimentos import local_runtime
os.environ.pop('CRIPTO_ROOT', None)
local_runtime.MARKER = Path({str(marker)!r})
print(local_runtime.configure_local_runtime()['DATA_DIR'])
""",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(tmp_path / "Cripto/operacao/dados")


def test_symlink_escape_is_rejected(tmp_path):
    root, outside = tmp_path / "Cripto", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires Windows privilege")
    result = run(root, "from GarimpoInvestimentos.core import paths", OUTPUT_DIR="linked/reports")
    assert result.returncode != 0
    assert "fora de CRIPTO_ROOT" in result.stderr
    assert not (outside / "reports").exists()
