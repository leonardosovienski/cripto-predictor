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


def test_incident_remains_open_pending_human_rotation():
    incident = (ROOT / "docs" / "SECURITY_INCIDENT_SERPAPI.md").read_text(encoding="utf-8")
    assert "BLOCKED_PENDING_SECRET_ROTATION" in incident
    assert "ação humana" in incident.lower()
    assert "encerrado" not in incident.lower()
