"""Stack wheels: fetch, verify and audit the published wheels this project consumes.

Canonical artifact registry = ``STACK_WHEELS.json`` next to ``pyproject.toml``. Each entry names the
producer repository, the GitHub Release tag, the asset and its sha256. The wheels are downloaded
through the GitHub REST API (the only path that works for private repositories), verified against
the registry sha256 and placed in a local flat index (``.stack-wheels/``, never versioned). ``uv.lock``
pins the packages to that index by name + version, so the lock no longer embeds a repository name or
a URL: a repository rename or a visibility change cannot break ``uv sync --locked`` silently; it fails
here, with the reason, before ``uv`` runs.

Why this exists (R01, 2026-10-07): the locks pinned ``.../ecosystem-predictor/releases/download/...``;
the repository was renamed ``ecosystem-predictor-cain`` and a new repository took the old name, and
all product repositories became private. Every pinned URL answered 404 and no consumer could install.

Commands (stdlib only, Python >= 3.11, Linux/Windows):

    python <this file> fetch   [--project DIR]            download + verify into the flat index
    python <this file> check   [--project DIR]            index, uv.lock and pyproject agree with the registry
    python <this file> probe   [--project DIR]            availability sentinel: fetch into a temp dir
    python <this file> requirements --input FILE --output FILE [--project DIR]
                                                          add --hash/--find-links for the stack lines of a
                                                          ``uv export`` file, for ``pip --require-hashes``

Authentication (never printed): the first of ``STACK_READ_TOKEN``, ``GH_TOKEN``, ``GITHUB_TOKEN`` in the
environment; else ``gh auth token`` when the GitHub CLI is installed and logged in; else anonymous
(works only while the producer repository is public). A fine-grained token needs *Contents: read*
on every producer repository listed in the registry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.github.com"
REGISTRY_NAME = "STACK_WHEELS.json"
SCHEMA = "stack-wheels/1"
TOKEN_VARIABLES = ("STACK_READ_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
RELEASE_URL = re.compile(r"github\.com/[^/\s\"']+/[^/\s\"']+/releases/download/")


class StackError(RuntimeError):
    pass


# --------------------------------------------------------------------------- registry


def load_registry(project: Path) -> dict:
    path = project / REGISTRY_NAME
    if not path.is_file():
        raise StackError(f"registry not found: {path}")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != SCHEMA:
        raise StackError(f"{path}: unsupported schema {registry.get('schema')!r} (expected {SCHEMA!r})")
    required = {"package", "version", "repository", "release_tag", "asset", "sha256"}
    seen: set[str] = set()
    for entry in registry.get("wheels", []):
        missing = required - entry.keys()
        if missing:
            raise StackError(f"{path}: entry {entry.get('package')!r} lacks {sorted(missing)}")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise StackError(f"{path}: {entry['package']}: sha256 must be 64 lowercase hex characters")
        if not entry["asset"].endswith(".whl"):
            raise StackError(f"{path}: {entry['package']}: asset must be a wheel")
        if entry["package"] in seen:
            raise StackError(f"{path}: duplicate package {entry['package']}")
        seen.add(entry["package"])
        retired = registry.get("retired_repositories", {})
        if entry["repository"] in retired:
            raise StackError(
                f"{path}: {entry['package']} points to retired repository {entry['repository']}: "
                f"{retired[entry['repository']]}"
            )
    if not registry.get("wheels"):
        raise StackError(f"{path}: no wheels listed")
    registry.setdefault("index_dir", ".stack-wheels")
    return registry


def index_dir(project: Path, registry: dict) -> Path:
    return project / registry["index_dir"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------- GitHub


def resolve_token() -> tuple[str | None, str]:
    for name in TOKEN_VARIABLES:
        value = os.environ.get(name, "").strip()
        if value:
            return value, name
    gh = shutil.which("gh")
    if gh:
        try:
            completed = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            completed = None
        if completed and completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip(), "gh auth token"
    return None, "anonymous"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Stop at the first redirect: the Authorization header must not follow it to the CDN."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401 - urllib hook
        return None


def _github_request(url: str, token: str | None, accept: str, timeout: int = 60) -> urllib.request.Request:
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "stack-wheels"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _describe_http_error(exc: urllib.error.HTTPError, token_source: str, what: str) -> str:
    if exc.code == 404:
        hint = (
            "the repository is private and no token with Contents: read was supplied"
            if token_source == "anonymous"
            else "the repository was renamed, the release/asset is missing, or the token lacks access to it"
        )
        return f"{what}: HTTP 404 ({hint}; auth={token_source})"
    if exc.code in (401, 403):
        return f"{what}: HTTP {exc.code} (token rejected or rate limited; auth={token_source})"
    return f"{what}: HTTP {exc.code} (auth={token_source})"


def release_asset(entry: dict, token: str | None, token_source: str) -> dict:
    url = f"{API}/repos/{entry['repository']}/releases/tags/{urllib.parse.quote(entry['release_tag'])}"
    try:
        with urllib.request.urlopen(_github_request(url, token, "application/vnd.github+json")) as response:
            release = json.load(response)
    except urllib.error.HTTPError as exc:
        raise StackError(
            _describe_http_error(exc, token_source, f"{entry['repository']}@{entry['release_tag']}")
        ) from exc
    except urllib.error.URLError as exc:
        raise StackError(
            f"{entry['repository']}@{entry['release_tag']}: network error: {exc.reason}"
        ) from exc
    for asset in release.get("assets", []):
        if asset.get("name") == entry["asset"]:
            return asset
    names = ", ".join(sorted(a.get("name", "?") for a in release.get("assets", []))) or "none"
    raise StackError(
        f"{entry['repository']}@{entry['release_tag']}: asset {entry['asset']} not in release "
        f"(assets: {names})"
    )


def download_asset(asset: dict, destination: Path, token: str | None, token_source: str) -> None:
    opener = urllib.request.build_opener(_NoRedirect)
    request = _github_request(asset["url"], token, "application/octet-stream")
    try:
        try:
            with opener.open(request, timeout=120) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308) and exc.headers.get("Location"):
                # Pre-signed CDN URL: no Authorization header may travel with it.
                plain = urllib.request.Request(
                    exc.headers["Location"], headers={"User-Agent": "stack-wheels"}
                )
                with urllib.request.urlopen(plain, timeout=300) as response:
                    body = response.read()
            else:
                raise
    except urllib.error.HTTPError as exc:
        raise StackError(_describe_http_error(exc, token_source, f"asset {asset.get('name')}")) from exc
    except urllib.error.URLError as exc:
        raise StackError(f"asset {asset.get('name')}: network error: {exc.reason}") from exc
    destination.write_bytes(body)


# --------------------------------------------------------------------------- commands


def fetch(project: Path, destination: Path | None = None, force: bool = False) -> list[dict]:
    registry = load_registry(project)
    target = destination or index_dir(project, registry)
    target.mkdir(parents=True, exist_ok=True)
    token, token_source = resolve_token()
    report: list[dict] = []
    failures: list[str] = []
    for entry in registry["wheels"]:
        wheel = target / entry["asset"]
        if wheel.is_file() and not force and sha256_of(wheel) == entry["sha256"]:
            report.append({"package": entry["package"], "version": entry["version"], "status": "present"})
            continue
        try:
            asset = release_asset(entry, token, token_source)
            download_asset(asset, wheel, token, token_source)
            actual = sha256_of(wheel)
            if actual != entry["sha256"]:
                wheel.unlink(missing_ok=True)
                raise StackError(
                    f"{entry['package']} {entry['version']}: sha256 mismatch "
                    f"(registry {entry['sha256'][:12]}…, "
                    f"asset {actual[:12]}…); the published asset is not the registered one"
                )
        except StackError as exc:
            failures.append(str(exc))
            report.append(
                {
                    "package": entry["package"],
                    "version": entry["version"],
                    "status": "FAILED",
                    "error": str(exc),
                }
            )
            continue
        report.append(
            {
                "package": entry["package"],
                "version": entry["version"],
                "status": "fetched",
                "release_tag": entry["release_tag"],
                "asset_id": asset.get("id"),
            }
        )
    for line in report:
        print(json.dumps(line))
    if failures:
        raise StackError(
            f"{len(failures)} of {len(registry['wheels'])} stack wheels unavailable (auth={token_source}). "
            "If the producer repositories are private, set STACK_READ_TOKEN "
            "(fine-grained token, Contents: read "
            "on each producer repository). The lock cannot be installed until every wheel resolves."
        )
    print(f"stack wheels: {len(report)} verified in {target} (auth={token_source})")
    return report


def probe(project: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="stack-wheels-probe-") as temporary:
        fetch(project, Path(temporary), force=True)


def _lock_packages(project: Path) -> dict[str, dict]:
    lock_path = project / "uv.lock"
    if not lock_path.is_file():
        raise StackError(f"uv.lock not found: {lock_path}")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    return {package["name"]: package for package in lock.get("package", [])}


def check(project: Path) -> None:
    registry = load_registry(project)
    target = index_dir(project, registry)
    problems: list[str] = []

    pyproject_path = project / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    indexes = pyproject.get("tool", {}).get("uv", {}).get("index", [])
    flat = [i for i in indexes if i.get("format") == "flat" and i.get("url") == registry["index_dir"]]
    if not flat:
        problems.append(
            f'pyproject.toml: no [[tool.uv.index]] with format = "flat" and url = {registry["index_dir"]!r}'
        )
    sources = pyproject.get("tool", {}).get("uv", {}).get("sources", {})
    names = {entry["package"] for entry in registry["wheels"]}
    for name, source in sources.items():
        if name in names and ("url" in source or "git" in source or "path" in source):
            problems.append(
                f"pyproject.toml: [tool.uv.sources] {name} must not use url/git/path; "
                "the registry is the source"
            )
    for raw in (pyproject_path, project / "uv.lock"):
        if raw.is_file():
            for number, line in enumerate(raw.read_text(encoding="utf-8").splitlines(), 1):
                if RELEASE_URL.search(line):
                    problems.append(
                        f"{raw.name}:{number}: release URL pin found; wheels come from the registry only"
                    )

    packages = _lock_packages(project)
    for entry in registry["wheels"]:
        package = packages.get(entry["package"])
        if package is None:
            problems.append(f"uv.lock: {entry['package']} not locked")
            continue
        if package.get("version") != entry["version"]:
            problems.append(
                f"uv.lock: {entry['package']} is {package.get('version')}, registry says {entry['version']}"
            )
        source = package.get("source", {})
        if source.get("registry") != registry["index_dir"]:
            problems.append(
                f"uv.lock: {entry['package']} source is {source}, expected registry {registry['index_dir']!r}"
            )
        paths = {wheel.get("path") for wheel in package.get("wheels", [])}
        if entry["asset"] not in paths:
            problems.append(
                f"uv.lock: {entry['package']} wheels {sorted(p for p in paths if p)} "
                f"do not include {entry['asset']}"
            )
        wheel = target / entry["asset"]
        if not wheel.is_file():
            problems.append(f"{registry['index_dir']}/{entry['asset']}: missing (run `fetch`)")
        elif sha256_of(wheel) != entry["sha256"]:
            problems.append(f"{registry['index_dir']}/{entry['asset']}: sha256 differs from the registry")
    if target.is_dir():
        extra = sorted(
            p.name
            for p in target.iterdir()
            if p.suffix == ".whl" and p.name not in {e["asset"] for e in registry["wheels"]}
        )
        if extra:
            problems.append(f"{registry['index_dir']}: unregistered wheels present: {extra}")
    if problems:
        raise StackError("stack wheels check failed:\n  " + "\n  ".join(problems))
    print(
        f"stack wheels check: {len(registry['wheels'])} packages consistent "
        f"(registry, {registry['index_dir']}, uv.lock, pyproject.toml)"
    )


def requirements(project: Path, source: Path, output: Path) -> None:
    """Rewrite a ``uv export`` requirements file so the stack lines carry hashes and a find-links."""
    registry = load_registry(project)
    target = index_dir(project, registry).resolve()
    by_name = {entry["package"].lower().replace("_", "-"): entry for entry in registry["wheels"]}
    lines = source.read_text(encoding="utf-8").splitlines()
    out: list[str] = [f"--find-links {target.as_posix()}"]
    matched: set[str] = set()
    for line in lines:
        stripped = line.strip()
        candidate = re.match(r"^([A-Za-z0-9_.-]+)==([^\s\\;]+)", stripped)
        if candidate:
            name = candidate.group(1).lower().replace("_", "-")
            entry = by_name.get(name)
            if entry is not None:
                if candidate.group(2) != entry["version"]:
                    raise StackError(
                        f"{source}: {name}=={candidate.group(2)} but registry says {entry['version']}"
                    )
                if "--hash=" in stripped:
                    raise StackError(f"{source}: {name} already carries a hash; expected a flat-index line")
                out.append(f"{entry['package']}=={entry['version']} --hash=sha256:{entry['sha256']}")
                matched.add(name)
                continue
        out.append(line)
    missing = sorted(set(by_name) - matched)
    if missing:
        print(f"note: not in the exported requirements (not needed by this export): {missing}")
    output.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"requirements with stack hashes written to {output} ({len(matched)} stack lines)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    project_help = "directory holding pyproject.toml, uv.lock and STACK_WHEELS.json (default: cwd)"
    parser.add_argument("--project", type=Path, default=None, help=project_help)
    commands = parser.add_subparsers(dest="command", required=True)
    subparsers = {name: commands.add_parser(name) for name in ("fetch", "check", "probe", "requirements")}
    for subparser in subparsers.values():
        # Accepted before or after the command: `--project DIR fetch` and `fetch --project DIR`.
        subparser.add_argument("--project", type=Path, default=None, dest="project_after", help=project_help)
    subparsers["fetch"].add_argument(
        "--force", action="store_true", help="re-download even when the verified wheel is present"
    )
    subparsers["requirements"].add_argument("--input", type=Path, required=True)
    subparsers["requirements"].add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    project = (args.project_after or args.project or Path.cwd()).resolve()
    try:
        if args.command == "fetch":
            fetch(project, force=args.force)
        elif args.command == "check":
            check(project)
        elif args.command == "probe":
            probe(project)
        elif args.command == "requirements":
            requirements(project, args.input, args.output)
    except StackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
