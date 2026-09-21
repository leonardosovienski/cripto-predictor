"""Rights-aware ResearchBundleV1 producer for sanitized external evidence."""

from pathlib import Path

from research_bundle import canonical, digest, loads
from research_bundle.export import Builder, admitted_sources, exporter_provenance

SOURCE = "external-intelligence/export.json"


def export_external(root, expected_sha, destination, exported_at):
    revision, sources = admitted_sources(root, {SOURCE: expected_sha}, {SOURCE})
    payload = loads(sources[SOURCE])
    if payload.get("schema_version") != "ExternalIntelligenceExportV1":
        raise ValueError("Unsupported External Intelligence export")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("External evidence must be a list")
    provenance = exporter_provenance({"external.py": Path(__file__)})
    builder = Builder(
        dict(
            domain="crypto",
            repository="https://github.com/leonardosovienski/cripto-predictor",
            publisher="crypto-local",
            stream="external-intelligence-shadow",
            code_revision=revision,
            exporter_revision="sha256:" + digest(canonical(provenance)),
            inputs={SOURCE: expected_sha},
        ),
        dict(policy="external-intelligence-export/1", read=True, disclose=False, generate=False),
        exported_at,
        provenance=provenance,
    )
    excluded = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Malformed external evidence")
        rights = item.get("rights")
        forbidden = {"raw_payload", "headers", "api_key", "wallets"} & set(item)
        if forbidden:
            raise ValueError("Raw or sensitive external data is forbidden")
        if not isinstance(rights, dict) or rights.get("derived_export") is not True:
            excluded.append(item.get("evidence_id", "unknown"))
            continue
        if rights.get("cain_read") is not True:
            excluded.append(item.get("evidence_id", "unknown"))
            continue
        entity = builder.entity(
            item["evidence_id"],
            "external_evidence",
            "RESEARCH_ONLY",
            {
                "canonical_asset_id": item["canonical_asset_id"],
                "provider": item["provider"],
                "metric": item["metric"],
                "feature_version": item.get("feature_version"),
                "pit_grade": item["pit_grade"],
                "effective_available_at": item["effective_available_at"],
                "dataset_snapshot_revision": payload["dataset_snapshot_revision"],
                "derived_evidence": item["derived_evidence"],
                "coverage": item.get("coverage", {}),
                "rights": {
                    "read": True,
                    "generate": bool(rights.get("cain_generate", False)),
                    "persistent_memory": bool(rights.get("persistent_memory", False)),
                },
            },
            SOURCE,
            axis="scientific",
            event_at=item.get("observed_at"),
            recorded_at=item.get("effective_available_at"),
        )
        resource = builder.resource(
            "external-evidence:" + item["evidence_id"],
            "producer:" + SOURCE + "#" + item["evidence_id"],
            raw=canonical(item),
            role="feature_slice",
            metadata={"sanitized": True, "raw_provider_payload": False},
        )
        builder.relation(entity, "REPRESENTED_BY", resource)
    coverage = builder.body["coverage"]
    if not isinstance(coverage, dict):
        raise ValueError("Bundle builder returned invalid coverage")
    coverage["missing"] = ["Scientific edge not evaluated"]
    coverage["excluded"] = sorted(excluded) + [
        "API keys and headers",
        "Raw restricted provider payloads",
        "Wallet lists",
        "Evidence without explicit CAIN read and derived-export rights",
    ]
    return builder.publish(root, destination, sources)


__all__ = ["SOURCE", "export_external"]
