from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_payload_is_present_and_not_runtime_ignored():
    payload = list((ROOT / "GarimpoInvestimentos").rglob("*.py"))
    assert payload
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "GarimpoInvestimentos" not in ignore


def test_no_legacy_shared_source_directories():
    assert not (ROOT / "vendor").exists()
    assert not (ROOT / "packages").exists()


def test_pyright_tem_uma_unica_fonte_de_configuracao():
    """pyrightconfig.json vence sobre [tool.pyright] do pyproject; manter os dois
    cria uma configuracao morta que silenciosamente nao tem efeito.

    Aconteceu: em 2026-08-21 as duas existiam e divergiam — a json listava 15
    caminhos em `include`, a do pyproject listava 8. Quem editasse o pyproject
    esperando mudar a cobertura do type check nao mudaria nada, e sem erro.
    """
    raiz = Path(__file__).resolve().parents[1]
    json_existe = (raiz / "pyrightconfig.json").exists()
    pyproject = (raiz / "pyproject.toml").read_text(encoding="utf-8")
    tem_bloco = "[tool.pyright]" in pyproject
    assert json_existe != tem_bloco, (
        "pyright deve ter exatamente UMA fonte de configuracao: "
        f"pyrightconfig.json={json_existe}, [tool.pyright] no pyproject={tem_bloco}"
    )
