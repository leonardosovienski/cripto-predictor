import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(
    rb"(?:sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|SERP_API_KEY\s*=\s*[^\r\n]+)"
)


def test_built_wheels_contain_no_runtime_artifacts_or_secrets():
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    assert wheels
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
