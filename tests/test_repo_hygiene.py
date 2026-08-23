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


def _blocos_bat_com_parenteses_soltos(texto: str) -> list[tuple[int, str]]:
    """Linhas dentro de um bloco `... (` que contem ( ou ) sem escape ^.

    O cmd.exe conta parenteses ao PARSEAR o bloco inteiro, antes de executar
    qualquer coisa: um `)` solto no meio fecha o bloco cedo e o resto da linha
    vira comando. Por isso o defeito nao depende do ramo ser tomado -- ele
    quebra o script SEMPRE.
    """
    achados: list[tuple[int, str]] = []
    profundidade = 0
    for numero, linha in enumerate(texto.splitlines(), start=1):
        sem_escape = linha.replace("^(", "").replace("^)", "")
        corpo = sem_escape.strip()
        if profundidade > 0 and corpo not in (")", ") else (") and ("(" in corpo or ")" in corpo):
            achados.append((numero, linha.strip()))
        profundidade += sem_escape.count("(") - sem_escape.count(")")
        profundidade = max(profundidade, 0)
    return achados


def test_bat_nao_tem_parentese_solto_dentro_de_bloco():
    """Barreira do incidente de 2026-08-22.

    `run_sinal_diario.bat` trazia, dentro de um `if errorlevel 1 (`, um echo com
    "(GEMINI_API_KEY / SERP_API_KEY)". O `)` fechava o bloco cedo e o cmd
    abortava com "e foi inesperado neste momento" -- DEPOIS de a ingestao dos 10
    ativos fixos ter dado certo, entao parecia falha da rede. Efeito real: os
    passos `--discover` e `--summary` nunca rodaram por esse script desde que ele
    nasceu (#11), e o universo da Feature Store nunca cresceu por essa via.

    A suite pytest nao executa .bat; esta barreira cobre o que ela nao alcanca,
    no mesmo espirito da checagem de ASCII dos .ps1 em scripts/ci_check.py.
    """
    raiz = Path(__file__).resolve().parents[1]
    problemas: list[str] = []
    for bat in sorted(raiz.glob("*.bat")):
        texto = bat.read_text(encoding="utf-8", errors="replace")
        for numero, linha in _blocos_bat_com_parenteses_soltos(texto):
            problemas.append(f"{bat.name}:{numero}: {linha}")
    assert not problemas, (
        "parentese sem escape dentro de bloco de .bat (use ^( e ^) ou reescreva):\n"
        + "\n".join(problemas)
    )


def test_backup_aponta_para_o_banco_real():
    """O default do backup tem que ser o mesmo caminho que o resto do projeto usa.

    Ate 2026-08-23 ele era `<repo>/output/feature_store.db`, que nunca existe em
    producao (core.paths poe o banco sob DATA_DIR, fora do checkout). Num
    utilitario cuja unica razao de existir e nao perder dado, um default que
    aponta para lugar nenhum e o pior tipo de default -- e este projeto ja
    perdeu as 440 previsoes brutas da H5 em definitivo.
    """
    from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
    from scripts.feature_store_backup import DEFAULT_DATABASE

    assert DEFAULT_DATABASE == FEATURE_STORE_DB
