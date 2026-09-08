"""--output-dir nunca pode ser aceito e silenciosamente ignorado por import order."""

import os
import subprocess
import sys
from pathlib import Path


def _run(code: str, *args: str):
    env = os.environ.copy()
    env.pop("OUTPUT_DIR", None)
    env.pop("GARIMPO_OUTPUT_DIR", None)
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=Path(__file__).parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_main_aplica_output_dir_antes_de_importar_paths(tmp_path):
    result = _run(
        "import sys; sys.argv=['app','--output-dir',sys.argv[1]]; "
        "\ntry: import GarimpoInvestimentos.main"
        "\nexcept ModuleNotFoundError: pass"
        "\nfrom GarimpoInvestimentos.core.paths import OUTPUT_DIR; print(OUTPUT_DIR.resolve())",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(tmp_path.resolve())


def test_import_tardio_falha_alto_em_vez_de_ignorar_output_dir(tmp_path):
    result = _run(
        "import GarimpoInvestimentos.core.paths; import sys; "
        "sys.argv=['app','--output-dir',sys.argv[1]]; import GarimpoInvestimentos.main",
        str(tmp_path),
    )
    assert result.returncode != 0
    assert "depois de core.paths ter sido carregado" in result.stderr
