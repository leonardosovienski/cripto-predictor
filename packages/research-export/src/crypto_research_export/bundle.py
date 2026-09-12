"""Opt-in producer-owned structured charter export. No scientific runtime."""

import argparse
from pathlib import Path

from research_bundle import canonical, digest, loads
from research_bundle.export import Builder, admitted_sources, exporter_provenance

TRIALS = "GarimpoInvestimentos/trials.json"
ATTESTATIONS = {
    "GarimpoInvestimentos/trials.harness_attestation.json",
    "GarimpoInvestimentos/trials.phase1_harness_attestation.json",
}
SOURCES = {"charters/scientific_state.json", TRIALS, *ATTESTATIONS}


def export(root, expected, destination, exported_at):
    revision, sources = admitted_sources(root, expected, SOURCES)
    name = "charters/scientific_state.json"
    charter = loads(sources[name])
    if charter.get("schema_version") != "crypto-scientific-state/1":
        raise ValueError("Unsupported scientific charter")
    trials = {}
    if TRIALS in sources:
        registry = loads(sources[TRIALS])
        if type(registry) is not list:
            raise ValueError("Unsupported trial registry")
        for record in registry:
            if (
                type(record) is not dict
                or type(record.get("name")) is not str
                or record["name"] in trials
            ):
                raise ValueError("Ambiguous trial identity")
            trials[record["name"]] = record
    provenance = exporter_provenance({"bundle.py": Path(__file__)})
    builder = Builder(
        dict(
            domain="crypto",
            repository="https://github.com/leonardosovienski/cripto-predictor",
            publisher="crypto-local",
            stream="research-bundle",
            code_revision=revision,
            exporter_revision="sha256:" + digest(canonical(provenance)),
            inputs=expected,
        ),
        dict(policy="crypto-research-bundle/1", read=True, disclose=False, generate=False),
        exported_at,
        provenance=provenance,
    )
    document = builder.resource(
        name,
        "producer:" + name,
        raw=sources[name],
        role="document",
        metadata={"scope": "Admitted scientific charter, not a trial result"},
    )
    for attestation_source in sorted(ATTESTATIONS & sources.keys()):
        record = loads(sources[attestation_source])
        if record.get("schema_version") != "pipeline-power/2":
            raise ValueError("Unsupported harness attestation")
        attestation = builder.entity(
            attestation_source,
            "attestation",
            "RECORDED",
            record,
            attestation_source,
            axis="operational",
            identity_basis="source_locator",
            recorded_at=record.get("passed_at"),
        )
        resource = builder.resource(
            attestation_source,
            "producer:" + attestation_source,
            raw=sources[attestation_source],
            role="attestation",
            metadata={
                "scope": "Existing planted-control harness; not a trial verdict or current validity certification"
            },
        )
        builder.relation(attestation, "REPRESENTED_BY", resource)
        # No trial linkage is inferred: neither registry explicitly assigns this receipt to a trial.
    for hypothesis, status in sorted(charter["hypotheses"].items()):
        node = builder.entity(
            hypothesis,
            "hypothesis",
            status,
            {
                "charter_schema": charter["schema_version"],
                "as_of_commit": charter.get("as_of_commit"),
                "frozen_families": charter.get("frozen_families"),
                "notes": charter.get("notes"),
            },
            name,
            axis="domain_lifecycle",
        )
        builder.relation(node, "SUPPORTED_BY", document)
        trial_id = charter.get("hypothesis_trials", {}).get(hypothesis)
        if trial_id is not None:
            record = trials.get(trial_id)
            payload = (
                record
                if record is not None
                else {
                    "identity_source": "charter hypothesis_trials mapping",
                    "trial_record_received": False,
                }
            )
            trial = builder.entity(
                trial_id,
                "trial",
                record.get("status", "UNKNOWN") if record is not None else "UNKNOWN",
                payload,
                TRIALS if record is not None else name,
                recorded_at=record.get("registered_at") if record is not None else None,
            )
            reference = builder.resource(
                "trial-record:" + trial_id,
                "producer:" + TRIALS + "#" + trial_id,
                raw=canonical(record) if record is not None else None,
                metadata={
                    "selection": {"name": trial_id},
                    "source_sha256": expected.get(TRIALS),
                    "serialization": "canonical JSON selected record; not original file bytes"
                    if record is not None
                    else None,
                    "availability_reason": "Pinned existing trial entry"
                    if record is not None
                    else "Only identity mapping admitted; trial bytes unavailable",
                },
            )
            builder.relation(node, "HAS_TRIAL", trial)
            builder.relation(trial, "REPRESENTED_BY", reference)
    builder.body["coverage"]["missing"] = [
        "Exact input datasets not admitted in this slice",
        *([] if ATTESTATIONS & sources.keys() else ["Harness attestations not admitted"]),
        *([] if TRIALS in sources else ["Trial registry not admitted"]),
    ]
    return builder.publish(root, destination, sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument(
        "--trials-sha", help="Optional explicit SHA256 admission of existing trial registry"
    )
    parser.add_argument("--attestation-sha", action="append", default=[], metavar="PATH=SHA256")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--exported-at", required=True)
    args = parser.parse_args()
    expected = {"charters/scientific_state.json": args.expected_sha}
    if args.trials_sha:
        expected[TRIALS] = args.trials_sha
    for admission in args.attestation_sha:
        name, separator, sha = admission.partition("=")
        if not separator or name not in ATTESTATIONS or name in expected:
            parser.error("Invalid or duplicate attestation admission")
        expected[name] = sha
    bundle = export(
        args.root,
        expected,
        args.destination,
        args.exported_at,
    )
    print(bundle["bundle_id"])


if __name__ == "__main__":
    main()
