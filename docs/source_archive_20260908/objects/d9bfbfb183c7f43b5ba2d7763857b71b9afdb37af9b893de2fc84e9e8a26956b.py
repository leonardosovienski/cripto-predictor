import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|SERP_API_KEY\s*=\s*[^\r\n]+)"
)


def test_sdist_contains_build_sources_without_research_archives():
    sdists = sorted((ROOT / "dist").glob("*.tar.gz"))
    assert sdists, "rode uv build antes da suíte para validar o pacote fonte"
    for sdist in sdists:
        with tarfile.open(sdist, "r:gz") as archive:
            names = [
                member.name.split("/", 1)[1] for member in archive.getmembers() if member.isfile()
            ]
            assert "pyproject.toml" in names
            assert "GarimpoInvestimentos/cli.py" in names
            assert any(name.startswith("charters/") for name in names)
            assert any(name.startswith("observation_plans/") for name in names)
            assert not any(
                name.split("/", 1)[0] in {"docs", "dist", "work", ".git", ".venv"}
                or name.endswith((".zip", ".bundle", ".whl", ".tar.gz", ".db", ".jsonl", ".env"))
                for name in names
            )


def test_built_wheels_contain_no_runtime_artifacts_or_secrets():
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    assert wheels, (
        f"nenhum .whl em {ROOT / 'dist'} — rode `uv build` antes da suíte "
        "(este teste inspeciona o wheel construído, não o checkout)"
    )
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert not any(
                name.endswith(".env") or "/logs/" in name or name.endswith((".db", ".jsonl"))
                for name in names
            )
            for name in names:
                if name.endswith((".py", ".json", ".toml", ".txt")):
                    assert not SECRET.search(archive.read(name)), (
                        f"secret-like payload in {wheel.name}:{name}"
                    )


def test_incident_registra_rotacao_confirmada_pelo_dono_sem_apagar_historico():
    """A rotação em 2026-08-19 foi confirmada diretamente pelo dono do repositório
    (não uma evidência criptográfica verificável a partir do código). O registro
    original 'BLOCKED_PENDING_SECRET_ROTATION' precisa continuar no arquivo — a
    confirmação é um adendo, não uma reescrita do histórico."""
    incident = (ROOT / "docs" / "SECURITY_INCIDENT_SERPAPI.md").read_text(encoding="utf-8")
    assert "BLOCKED_PENDING_SECRET_ROTATION" in incident
    assert "ROTATED_CONFIRMED_BY_OWNER_2026-08-19" in incident
    assert "ação humana" in incident.lower()
    assert "verificação de uso indevido" in incident.lower()
