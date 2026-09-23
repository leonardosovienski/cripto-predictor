"""The transitive import closure of every entrypoint stays inside the domain.

Checked on the INSTALLED package (checkout in CI, published wheel in cleanroom): no path
from [project.scripts] or the plugin entry point reaches the envelope protocol, CAIN,
the ecosystem envelope, or the reserved adapter_paths; and nothing outside the
adapter_paths imports from them (C24.1 adapter_paths rules 1 and 2).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from collections import deque
from importlib.metadata import distribution
from pathlib import Path

import GarimpoInvestimentos

FORBIDDEN_TOP = {
    "research_protocol",
    "cain",
    "ecosystem",
    "research_snapshot",
    "research_bundle",
    "crypto_research_export",
}
ADAPTERS = "GarimpoInvestimentos.adapters"
PACKAGE = Path(GarimpoInvestimentos.__file__).resolve().parent


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _graph() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for path in PACKAGE.rglob("*.py"):
        name = _module_name(path)
        is_package = path.name == "__init__.py"
        base = name.split(".") if is_package else name.split(".")[:-1]
        targets: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            if isinstance(node, ast.Import):
                targets.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    root = base[: len(base) - (node.level - 1)] if node.level > 1 else base
                    module = ".".join(root + ([node.module] if node.module else []))
                else:
                    module = node.module or ""
                targets.add(module)
                targets.update(f"{module}.{alias.name}" for alias in node.names)
            elif (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith("GarimpoInvestimentos.")
                and " " not in node.value
            ):
                targets.add(node.value)  # modules launched with `python -m <module>`
        edges[name] = targets
    return edges


def _resolve(target: str, modules: set[str]) -> str | None:
    while target:
        if target in modules:
            return target
        target = target.rpartition(".")[0]
    return None


def _roots() -> dict[str, str]:
    dist = distribution("cripto-predictor")
    return {
        f"{ep.group}:{ep.name}": ep.value.split(":")[0]
        for ep in dist.entry_points
        if ep.group in {"console_scripts", "predictor.plugins"}
    }


def _closure(root: str, edges: dict[str, set[str]]) -> tuple[dict[str, str | None], set[str]]:
    modules = set(edges)
    seen: dict[str, str | None] = {root: None}
    external: set[str] = set()
    queue = deque([root])
    while queue:
        current = queue.popleft()
        parts = current.split(".")
        for target in [".".join(parts[:i]) for i in range(1, len(parts))] + sorted(
            edges.get(current, ())
        ):
            if target.startswith("GarimpoInvestimentos"):
                local = _resolve(target, modules)
                if local and local not in seen:
                    seen[local] = current
                    queue.append(local)
            elif target:
                external.add(target.split(".")[0])
    return seen, external


def test_entrypoints_include_the_research_circuit():
    roots = _roots()
    assert roots["console_scripts:cripto-research"] == "GarimpoInvestimentos.research_runner"


def test_no_entrypoint_reaches_envelope_cain_or_adapter_paths():
    edges = _graph()
    report = {}
    for label, root in _roots().items():
        seen, external = _closure(root, edges)
        report[label] = {
            "forbidden": sorted(external & FORBIDDEN_TOP),
            "adapters": sorted(m for m in seen if m == ADAPTERS or m.startswith(ADAPTERS + ".")),
        }
    assert all(not v["forbidden"] and not v["adapters"] for v in report.values()), json.dumps(
        report, indent=1
    )


def test_research_circuit_components_are_reachable_from_the_entrypoint():
    seen, _ = _closure("GarimpoInvestimentos.research_runner", _graph())
    for component in (
        "research_admission",
        "research_execution",
        "research_results",
        "research_worker",
        "research_recovery",
        "research_contract",
    ):
        assert f"GarimpoInvestimentos.{component}" in seen, component


def test_nothing_outside_adapter_paths_imports_them():
    offenders = []
    for module, targets in _graph().items():
        if module == ADAPTERS or module.startswith(ADAPTERS + "."):
            continue
        if any(t == ADAPTERS or t.startswith(ADAPTERS + ".") for t in targets):
            offenders.append(module)
    assert offenders == []


def test_runtime_import_of_the_circuit_loads_no_forbidden_module():
    code = (
        "import sys, json\n"
        "import GarimpoInvestimentos.research_runner, GarimpoInvestimentos.research_worker\n"
        "import GarimpoInvestimentos.research_recovery\n"
        f"bad = sorted(m for m in sys.modules if m.split('.')[0] in {sorted(FORBIDDEN_TOP)!r}"
        f" or m.startswith({ADAPTERS!r}))\n"
        "print(json.dumps(bad))\n"
    )
    output = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout
    assert json.loads(output.strip().splitlines()[-1]) == []
