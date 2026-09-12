"""Installed real Crypto reports -> isolated CAIN -> verified offline restoration."""

import hashlib
import importlib.metadata as metadata
import json
import subprocess
import sys
from pathlib import Path

import cain
import research_bundle
from cain.archive import backup, restore
from cain.research import ResearchService
from cain.research.bundles import BundleService
from cain.workspace import WorkspaceStore


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rejected(operation):
    try:
        operation()
    except (ValueError, PermissionError):
        return
    raise AssertionError("Expected fail-closed refusal")


source, cain_source, producer, area = map(Path, sys.argv[1:])
source, cain_source, area = [p.resolve() for p in (source, cain_source, area)]
# POSIX venv executables are symlinks: resolving them selects the base interpreter.
producer = producer.absolute()
area.mkdir(parents=True, exist_ok=False)
assert area.is_relative_to(source.parent) and not area.is_relative_to(source)
for module in (cain, research_bundle):
    assert Path(module.__file__).is_relative_to(Path(sys.prefix))
assert not any(x.metadata["Name"] == "cripto-predictor" for x in metadata.distributions())
commands = []


def run(args, expected=0):
    args = list(map(str, args))
    r = subprocess.run(args, cwd=area, capture_output=True, timeout=120)
    record = dict(
        command=args,
        exit_code=r.returncode,
        stdout=r.stdout.decode(errors="replace"),
        stderr=r.stderr.decode(errors="replace"),
    )
    commands.append(record)
    (area / "commands.json").write_text(json.dumps(commands, indent=2), encoding="utf-8")
    assert r.returncode == expected, record
    return r.stdout


run(
    [
        producer,
        "-I",
        "-c",
        "import crypto_research_export,importlib.metadata as m,json; from pathlib import Path; import sys; assert Path(crypto_research_export.__file__).is_relative_to(Path(sys.prefix)); assert not any(x.metadata['Name']=='cripto-predictor' for x in m.distributions()); print(json.dumps({'exporter':crypto_research_export.__file__,'packages':{x.metadata['Name']:x.version for x in m.distributions()}}))",
    ]
)
names = [
    "charters/scientific_state.json",
    "GarimpoInvestimentos/trials.json",
    "GarimpoInvestimentos/trials.harness_attestation.json",
    "GarimpoInvestimentos/trials.phase1_harness_attestation.json",
]
pins = {name: sha(source / name) for name in names}
charter = json.loads((source / names[0]).read_bytes())
clock = "2026-09-12T00:00:00Z"
transport = area / "transport"
transport.mkdir()
for destination in ("bundle", "repeat"):
    cmd = [
        producer,
        "-I",
        "-m",
        "crypto_research_export.bundle",
        "--root",
        source,
        "--expected-sha",
        pins[names[0]],
        "--trials-sha",
        pins[names[1]],
        "--destination",
        transport / destination,
        "--exported-at",
        clock,
    ]
    for name in names[2:]:
        cmd += ["--attestation-sha", name + "=" + pins[name]]
    run(cmd)
bundle = json.loads((transport / "bundle/bundle.json").read_bytes())
assert (transport / "bundle/bundle.json").read_bytes() == (
    transport / "repeat/bundle.json"
).read_bytes()
template = json.loads((cain_source / ".ci/completion/existing-bundle-policy.json").read_bytes())
grant = next(g for g in template["bundle_grants"] if g["collection"] == "crypto")
grant.update(user="audit", generate=False)
policy = dict(
    version=3,
    grants=[],
    imports=[dict(user="audit", project="", collection="crypto", root=str(transport))],
    bundle_grants=[grant],
)
policy_path = area / "policy.json"
policy_path.write_text(json.dumps(policy), encoding="utf-8")
service = ResearchService(area / "research.db", policy_path)
scope = service.scope("audit", None, "crypto")
store = BundleService(service)
rejected(lambda: store.ingest("bundle/bundle.json", scope))
store.approve("bundle/bundle.json", scope)
assert store.ingest("bundle/bundle.json", scope)["status"] == "admitted"
assert store.ingest("bundle/bundle.json", scope)["status"] == "duplicate"
result = store.query(scope, limit=50)
assert result["total"] == len(bundle["entities"])
assert result["relation_total"] == len(bundle["relations"])
for hypothesis, expected in charter["hypotheses"].items():
    found = [e for e in result["entities"] if e["entity_id"] == hypothesis]
    assert len(found) == 1 and found[0]["status"] == expected
    details = store.entity(scope, bundle["bundle_id"], hypothesis, found[0]["revision"])
    assert details["evidence_total"] > 0
    for evidence in details["evidence"]:
        assert store.evidence(scope, bundle["bundle_id"], evidence["id"])["evidence"] == evidence
assert store.query(service.scope("other", None, "crypto"))["total"] == 0
store.verify(scope)
snapshot_template = json.loads((cain_source / ".ci/completion/existing-policy.json").read_bytes())
snapshot_grant = next(g for g in snapshot_template["grants"] if g["collection"] == "crypto")
snapshot_grant.update(user="audit", generate=False)
policy["grants"] = [snapshot_grant]
policy_path.write_text(json.dumps(policy), encoding="utf-8")
revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"]).decode().strip()
admission = dict(
    policy="crypto-frozen-reports-local/1",
    read=True,
    sources={names[0]: pins[names[0]]},
    code_revision=revision,
    exporter_revision="installed-exporter-recorded-in-commands",
)
(area / "admission.json").write_text(json.dumps(admission), encoding="utf-8")
run(
    [
        producer,
        "-I",
        "-c",
        "from crypto_research_export import main; raise SystemExit(main())",
        "--root",
        source,
        "--admission",
        area / "admission.json",
        "--output",
        transport / "snapshot.json",
        "--exported-at",
        clock,
    ]
)
service.ingest("snapshot.json", scope)
service.ingest("snapshot.json", scope)
snap = service.query(scope, limit=50)
assert snap["total_record_revisions"] == len(charter["hypotheses"])
assert {r["source_id"]: r["source_status"] for r in snap["records"]} == charter["hypotheses"]
for row in snap["records"]:
    for evidence in row["evidence"]:
        service.evidence(scope, evidence["reference_id"])
service.verify(scope)
workspace = WorkspaceStore(area / "workspace.db")
backup(workspace.path, service.path, policy_path, area / "backup")
restore(area / "backup", area / "restored")
transport.rename(area / "producer-unavailable")
restored_service = ResearchService(area / "restored/research.db", area / "restored/policy.json")
restored = BundleService(restored_service)
assert restored.query(scope, limit=50)["entities"] == result["entities"]
assert restored_service.query(scope, limit=50)["records"] == snap["records"]
restored.verify(scope, rebuild=True)
restored_service.verify(scope, rebuild=True)
received = 0
for artifact in result["artifacts"]:
    if artifact["availability"] == "received":
        destination = area / ("materialized-" + str(received))
        restored.materialize(scope, bundle["bundle_id"], artifact["artifact_id"], destination)
        assert sha(destination) == artifact["sha256"]
        received += 1
assert received > 0
revoked = json.loads((area / "restored/policy.json").read_bytes())
revoked["bundle_grants"] = []
revoked["grants"] = []
(area / "restored/policy.json").write_text(json.dumps(revoked), encoding="utf-8")
assert restored.query(scope)["total"] == 0
assert restored_service.query(scope)["total_record_revisions"] == 0
rejected(lambda: restored.verify(scope))
rejected(lambda: restored.verify(scope, rebuild=True))
first = next(a for a in result["artifacts"] if a["availability"] == "received")
rejected(
    lambda: restored.materialize(scope, bundle["bundle_id"], first["artifact_id"], area / "denied")
)
assert {name: sha(source / name) for name in names} == pins
assert not any(n.startswith("GarimpoInvestimentos") for n in sys.modules)
receipt = dict(
    status="PASS",
    source_commit=revision,
    source_sha256=pins,
    bundle_id=bundle["bundle_id"],
    hypothesis_oracle=charter["hypotheses"],
    entities=result["total"],
    relations=result["relation_total"],
    snapshot_records=snap["total_record_revisions"],
    materialized=received,
    offline_restore=True,
    revocation=True,
    absent_approval_refused=True,
    isolated_environments=True,
    scientific_runtime_imported=False,
    receiver_modules=dict(cain=cain.__file__, bundle=research_bundle.__file__),
)
(area / "evidence.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt))
