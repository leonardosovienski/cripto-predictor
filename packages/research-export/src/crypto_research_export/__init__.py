"""Read-only export of explicitly admitted, pinned Crypto reports. No pipeline imports."""

import argparse
import json
import re
import sys
from pathlib import Path

from research_snapshot import canonical, confined, digest, loads, seal, validate

REPOSITORY = "https://github.com/leonardosovienski/cripto-predictor"
SOURCES = {"charters/scientific_state.json", "docs/EVIDENCE_REGISTRY.md"}


def export(root, admission, destination, exported_at):
    root = Path(root).resolve(strict=True)
    destination = Path(destination).resolve()
    if destination.is_relative_to(root):
        raise ValueError("Export destination must be outside scientific source checkout")
    if (
        admission.get("policy") != "crypto-frozen-reports-local/1"
        or admission.get("read") is not True
    ):
        raise ValueError("Explicit report admission required")
    sources = admission.get("sources", {})
    if not sources or not set(sources) <= SOURCES:
        raise ValueError("Only the charter and evidence registry are supported; no arbitrary files")
    # All path, permission and expected digest declarations checked before any source read.
    paths = {name: confined(root, name) for name in sources}
    if not all(
        isinstance(sha, str) and re.fullmatch("[a-f0-9]{64}", sha) for sha in sources.values()
    ):
        raise ValueError("Pin every admitted input SHA-256 before export")
    for revision in (admission.get("code_revision"), admission.get("exporter_revision")):
        if not isinstance(revision, str) or not revision.strip():
            raise ValueError("Source and exporter revision required")
    raw = {}
    for name, path in paths.items():
        with path.open("rb") as handle:
            content = handle.read(100_001)
        if len(content) > 100_000 or digest(content) != sources[name]:
            raise ValueError("Source exceeds limit or differs from admitted immutable input")
        raw[name] = content
    evidence, records = [], []

    def add_record(source, source_id, status, axis, kind, text, start, locator):
        eid = digest(canonical([source, start, text]))
        evidence.append(
            {
                "id": eid,
                "source": source,
                "availability": "received",
                "text": text,
                "sha256": digest(text.encode("utf-8")),
                "hash_basis": "received_utf8",
                "locator": locator,
                "start": start,
                "end": start + len(text),
                "offset_unit": "unicode_codepoints",
            }
        )
        payload = {
            "source_id": source_id,
            "kind": kind,
            "identity_basis": "source_assigned",
            "source_status": status,
            "status_axis": axis,
            "mapping": None,
            "reason": None,
            "event_at": None,
            "recorded_at": None,
            "available_at": None,
            "supersedes": [],
            "evidence_ids": [eid],
        }
        records.append({**payload, "revision": digest(canonical(payload))})

    for name, content in sorted(raw.items()):
        text = content.decode("utf-8")
        if name == "charters/scientific_state.json":
            charter = loads(content)
            if charter.get("schema_version") != "crypto-scientific-state/1":
                raise ValueError("Unsupported source charter")
            # Preserve full exact source for JSON pointers; no JSON reserialization as original bytes.
            eid = digest(canonical([name, 0, text]))
            for hypothesis, status in sorted(charter["hypotheses"].items()):
                add_record(
                    name,
                    hypothesis,
                    status,
                    "domain_lifecycle",
                    "hypothesis_status_report",
                    text,
                    0,
                    "/hypotheses/" + hypothesis,
                )
            evidence = list({e["id"]: e for e in evidence}.values())
            # Shared source bytes, per-record pointer stays resolvable via source_id.
            for e in evidence:
                if e["id"] == eid:
                    e["locator"] = "/hypotheses (record source_id is the key)"
        else:
            matches = list(re.finditer(r"^## (CLAIM-CR-[A-Z0-9-]+)\s*$", text, re.M))
            if not matches or len({m[1] for m in matches}) != len(matches):
                raise ValueError("Missing or ambiguous claim headings")
            for i, match in enumerate(matches):
                section = text[
                    match.start() : matches[i + 1].start() if i + 1 < len(matches) else len(text)
                ]
                status = re.search(r"^- \*\*state:\*\* (.+)$", section, re.M)
                if not status:
                    raise ValueError("Missing literal claim state")
                add_record(
                    name,
                    match[1],
                    status[1],
                    "scientific",
                    "documented_claim",
                    section,
                    match.start(),
                    "heading:" + match[1],
                )
    # Re-read pinned inputs: concurrent modifications invalidate this export; no mixed accepted snapshot.
    for name, path in paths.items():
        with path.open("rb") as handle:
            if digest(handle.read(100_001)) != sources[name]:
                raise ValueError("Source changed during export")
    package = seal(
        {
            "contract": "ResearchSnapshotV1",
            "profile": "local-evidence/1",
            "extensions": {},
            "origin": {
                "domain": "crypto",
                "repository": REPOSITORY,
                "publisher": "crypto-local",
                "stream": "frozen-reports",
                "code_revision": admission["code_revision"],
                "exporter_revision": admission["exporter_revision"],
                "inputs": sources,
            },
            "exported_at": exported_at,
            "coverage": {
                "scope": "Selected frozen hypothesis status and documented claims",
                "completeness": "partial",
                "included": sorted(sources),
                "missing": [],
                "excluded": [
                    "Operational databases",
                    "Protected holdouts",
                    "Other reports and later research",
                ],
                "limitations": [
                    "Documented claims, not reproduced experiments",
                    "No current-state or historical-availability attestation",
                    "Records are hypothesis/claim reports, not independent trials",
                    "Reason is unstructured in evidence; null is not absence of cause",
                    "Revisions without explicit supersedes are unordered",
                ],
            },
            "restrictions": {
                "policy": admission["policy"],
                "read": True,
                "disclose": False,
                "generate": True,
            },
            "records": records,
            "evidence": evidence,
        }
    )
    validate(package)
    from research_snapshot.publication import publish

    receipt = publish(package, destination)
    return {
        "publication_id": package["publication_id"],
        "sha256": receipt,
        "records": len(records),
        "evidence": len(evidence),
        "output": str(destination),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--exported-at", required=True, help="Explicit timestamp, preserved in publication identity"
    )
    args = parser.parse_args(argv)
    try:
        print(
            json.dumps(
                export(
                    args.root, loads(args.admission.read_bytes()), args.output, args.exported_at
                ),
                ensure_ascii=False,
            )
        )
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("Export refused: " + type(exc).__name__, file=sys.stderr)
        return 1
