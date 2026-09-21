"""Local research-only External Intelligence commands."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from platformdirs import user_data_path

from GarimpoInvestimentos.external_intelligence.context import context_at
from GarimpoInvestimentos.external_intelligence.contracts import (
    AssetMapping,
    CollectionRun,
)
from GarimpoInvestimentos.external_intelligence.providers.coinmetrics import CoinMetricsAdapter
from GarimpoInvestimentos.external_intelligence.store import (
    ExternalIntelligenceStore,
    rights_from_row,
)


def default_db_path() -> Path:
    configured = os.getenv("CRIPTO_EXTERNAL_INTELLIGENCE_DB")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else user_data_path("cripto-predictor") / "external_intelligence.db"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    context = sub.add_parser("context-at")
    context.add_argument("--asset", required=True)
    context.add_argument("--decision-time", required=True)
    context.add_argument("--db", type=Path, default=default_db_path())
    collect = sub.add_parser("collect-coinmetrics")
    collect.add_argument("--asset", default=os.getenv("COINMETRICS_ASSET", "btc"))
    collect.add_argument(
        "--canonical-asset", default=os.getenv("COINMETRICS_CANONICAL_ASSET", "crypto:btc")
    )
    collect.add_argument("--metric", action="append", default=None)
    collect.add_argument("--start", default=os.getenv("COINMETRICS_START_TIME"))
    collect.add_argument("--end", default=os.getenv("COINMETRICS_END_TIME"))
    collect.add_argument(
        "--rights-policy",
        type=Path,
        default=Path(value).resolve()
        if (value := os.getenv("EXTERNAL_INTELLIGENCE_RIGHTS_POLICY"))
        else None,
    )
    collect.add_argument("--db", type=Path, default=default_db_path())
    args = parser.parse_args(argv)
    if args.command == "context-at":
        with ExternalIntelligenceStore(args.db) as store:
            result = context_at(
                store,
                asset=args.asset,
                decision_time=datetime.fromisoformat(args.decision_time.replace("Z", "+00:00")),
            )
        print(result.canonical_bytes().decode())
        return 0
    if args.command == "collect-coinmetrics":
        if not args.start or not args.end or args.rights_policy is None:
            parser.error("start, end and an explicit rights policy are required")
        rights = rights_from_row(json.loads(args.rights_policy.read_text("utf-8")))
        if not rights.local_research:
            parser.error("rights policy does not authorize local research")
        metrics = tuple(args.metric or ["TxCnt"])
        adapter = CoinMetricsAdapter()
        started = datetime.now(UTC)
        rows, requests = asyncio.run(
            adapter.fetch_pages_with_receipt(
                "timeseries/asset-metrics",
                {
                    "assets": args.asset,
                    "metrics": ",".join(metrics),
                    "start_time": args.start,
                    "end_time": args.end,
                    "frequency": "1d",
                    "page_size": "10000",
                },
            )
        )
        finished = datetime.now(UTC)
        run_id = "external-coinmetrics-" + uuid4().hex
        run = CollectionRun(
            collection_run_id=run_id,
            provider=adapter.name,
            collector_version="coinmetrics-api-v4/1",
            started_at=started,
            finished_at=finished,
            status="SUCCEEDED",
            requests=requests,
            observation_count=len(rows) * len(metrics),
        )
        observations = adapter.normalize_asset_metrics(
            rows,
            metrics=metrics,
            mappings={args.asset: args.canonical_asset},
            received_at=finished,
            run_id=run_id,
            run_revision=run.collection_run_revision,
            historical_request=True,
            rights=rights,
        )
        with ExternalIntelligenceStore(args.db) as store:
            store.record_collection_run(run)
            store.record_asset_mapping(
                AssetMapping(
                    adapter.name,
                    args.canonical_asset,
                    args.asset,
                    "coinmetrics-api-v4/1",
                )
            )
            inserted = sum(store.add_observation(item) for item in observations)
            snapshot = store.materialize_snapshot(finished, providers=(adapter.name,))
        print(
            json.dumps(
                {
                    "collection_run_id": run_id,
                    "collection_run_revision": run.collection_run_revision,
                    "dataset_snapshot_revision": snapshot["dataset_snapshot_revision"],
                    "observations_received": len(observations),
                    "semantic_revisions_inserted": inserted,
                    "pit_grade": "RECONSTRUCTED",
                    "capital_permission": False,
                },
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
