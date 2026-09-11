import subprocess
import sys

import pytest

from GarimpoInvestimentos.pipeline_results import summarize_outcomes


@pytest.mark.parametrize("mode", ["status", "ingest", "analyze", "history", "migrate-history"])
def test_read_only_dispatch_does_not_load_analysis(mode):
    code = f"""
import sys
sys.argv = ["cripto-predictor", {mode!r}, "--help"]
from GarimpoInvestimentos.cli import main
try:
    main()
except SystemExit as exc:
    assert exc.code in (None, 0), exc.code
assert "GarimpoInvestimentos.main" not in sys.modules
assert "GarimpoInvestimentos.config" not in sys.modules
assert "GarimpoInvestimentos.analyzers.ai_insights" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_ingestion_composition_import_is_lazy():
    code = """
import sys
import GarimpoInvestimentos.ingestion
assert "GarimpoInvestimentos.config" not in sys.modules
assert "GarimpoInvestimentos.analyzers.ai_insights" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_unknown_outcome_never_implies_success():
    with pytest.raises(ValueError, match="unknown"):
        summarize_outcomes({"synthetic": "TYPO"})


def test_ingestion_settings_do_not_require_unrelated_model_credentials(tmp_path):
    code = """
import os
for key in list(os.environ):
    if key.endswith(("_API_KEY", "_AUTH_TOKEN")):
        del os.environ[key]
from GarimpoInvestimentos.runtime_mode import select_mode
select_mode("ingest")
from GarimpoInvestimentos.config import settings, Settings
assert settings.runtime_mode == "ingest"
try:
    Settings(runtime_mode="analysis", _env_file=None)
except Exception:
    pass
else:
    raise AssertionError("analysis credentials were bypassed")
try:
    select_mode("analysis")
except RuntimeError:
    pass
else:
    raise AssertionError("mode changed after configuration")
"""
    import os

    env = os.environ.copy()
    empty = tmp_path / "empty.env"
    empty.write_text("")
    env["CRIPTO_ENV_FILE"] = str(empty)
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
