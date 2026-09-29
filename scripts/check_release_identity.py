"""Fail when the version in pyproject already has a GitHub release whose wheel differs from the local build.

Motivo: em 2026-09-29 o `main` empacotava `cripto-predictor 1.2.0rc3` com 17 arquivos diferentes do asset
publicado `v1.2.0rc3` — o mesmo número designava dois conteúdos. Regra: versão com release publicada é
imutável; qualquer mudança de conteúdo exige bump de versão.

Compara o conteúdo (sha256 por membro, ignorando `*.dist-info/RECORD`, que carrega hashes/tamanhos da
própria wheel) da wheel em `dist/` com a wheel do asset da tag `v<versão>`. Sem release para a versão:
passa. Sem rede/API (fora do CI): sai com 0 e avisa, a menos que `--strict`.

Uso: python scripts/check_release_identity.py [--dist dist] [--strict]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "leonardosovienski/cripto-predictor"


def _members(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as wheel:
        return {
            info.filename: hashlib.sha256(wheel.read(info)).hexdigest()
            for info in wheel.infolist()
            if not info.filename.endswith(".dist-info/RECORD")
        }


def _request(url: str, accept: str) -> bytes:
    headers = {"Accept": accept, "User-Agent": "cripto-predictor-release-identity"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=60
    ) as response:
        return response.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--strict", action="store_true", help="network failure is an error")
    args = parser.parse_args(argv)
    with (ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    wheels = sorted(args.dist.glob(f"cripto_predictor-{version}-*.whl"))
    if len(wheels) != 1:
        print(
            f"RELEASE_IDENTITY_ERROR: expected one wheel for {version} in {args.dist}, found {len(wheels)}"
        )
        return 2
    try:
        release = json.loads(
            _request(
                f"https://api.github.com/repos/{REPO}/releases/tags/v{version}",
                "application/vnd.github+json",
            )
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"RELEASE_IDENTITY_OK: no release v{version} yet; the version is free")
            return 0
        print(f"RELEASE_IDENTITY_UNVERIFIABLE: GitHub API {exc.code}")
        return 1 if args.strict else 0
    except (urllib.error.URLError, OSError) as exc:
        print(f"RELEASE_IDENTITY_UNVERIFIABLE: {type(exc).__name__}: {exc}")
        return 1 if args.strict else 0
    assets = [a for a in release.get("assets", []) if a["name"] == wheels[0].name]
    if not assets:
        print(f"RELEASE_IDENTITY_ERROR: release v{version} exists without asset {wheels[0].name}")
        return 2
    published = args.dist / f".published-{wheels[0].name}"
    published.write_bytes(_request(assets[0]["browser_download_url"], "application/octet-stream"))
    local, remote = _members(wheels[0]), _members(published)
    changed = sorted(
        name for name in local.keys() | remote.keys() if local.get(name) != remote.get(name)
    )
    published.unlink()
    if changed:
        print(
            f"RELEASE_IDENTITY_MISMATCH: version {version} is already published (v{version}) with different "
            f"content in {len(changed)} member(s); bump the version. First differences: {changed[:10]}"
        )
        return 2
    print(f"RELEASE_IDENTITY_OK: wheel content identical to the published v{version} asset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
