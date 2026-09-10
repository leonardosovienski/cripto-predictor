"""Register or inspect a separate carry window; explicit manual observation only.

Preparation and status use no network, accounts, scheduler or capital. Economic
rules and the original observer freeze remain unchanged. A new registration is
not an observed entry and is not an independent statistical sample.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts import observe_carry_forward as observer
from scripts.research_io import Ledger, encoded, sha, strict_json


def now():
    return datetime.now(UTC)


def timestamp(value):
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("Explicit UTC timestamp required")
    return instant


def new_protocol(original, start):
    if start.time() != datetime.min.time():
        raise ValueError("Entry must start at UTC midnight")
    duration = timestamp(original["end"]) - timestamp(original["start"])
    result = dict(original)
    result.update(
        id="carry-btc-manual-" + start.strftime("%Y%m%d") + "-v1",
        start=start.isoformat(),
        end=(start + duration).isoformat(),
        schedule_brasilia="Manual only, 21:15 Brasilia in each first UTC hour; no scheduler configured.",
    )
    return result


def prepare(directory, start, *, clock=now):
    original, original_freeze = observer.verify()
    instant = clock()
    if start < instant + timedelta(days=1):
        raise ValueError("Register at least 24 hours before a new entry; never backdate")
    protocol = new_protocol(original, start)
    protocol_bytes = encoded(protocol) + b"\n"
    registration = {
        "schema_version": 1,
        "registered_at_utc": instant.isoformat(),
        "original_freeze_sha256": original_freeze,
        "launcher_sha256": sha(Path(__file__).read_bytes()),
        "protocol_sha256": sha(protocol_bytes),
        "capital_permission": False,
        "scheduler_enabled": False,
        "collection_started": False,
    }
    # Refuse existing directories, including old ledgers or interrupted setups.
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "protocol.json").write_bytes(protocol_bytes)
    (directory / "registration.json").write_bytes(encoded(registration) + b"\n")
    return registration


def load(directory):
    original, original_freeze = observer.verify()
    raw = (directory / "registration.json").read_bytes()
    registration = strict_json(raw)
    protocol_bytes = (directory / "protocol.json").read_bytes()
    if (
        registration["schema_version"] != 1
        or registration["original_freeze_sha256"] != original_freeze
        or registration["launcher_sha256"] != sha(Path(__file__).read_bytes())
        or registration["protocol_sha256"] != sha(protocol_bytes)
        or registration["capital_permission"] is not False
        or registration["scheduler_enabled"] is not False
    ):
        raise ValueError("Registration freeze mismatch")
    protocol = strict_json(protocol_bytes)
    start = timestamp(protocol["start"])
    if protocol != new_protocol(original, start):
        raise ValueError("Economic rules differ from the preserved protocol")
    registered = timestamp(registration["registered_at_utc"])
    if start < registered + timedelta(days=1):
        raise ValueError("Registration must precede entry by at least 24 hours")
    return protocol, sha(raw)


def inspect(directory, *, clock=now):
    protocol, digest = load(directory)
    instant = clock()
    data = directory / "observations"
    ledger = Ledger(data / "ledger.jsonl")
    if any(row["payload"].get("freeze_sha256") != digest for row in ledger.rows):
        raise ValueError("Ledger belongs to another registration")
    for row in ledger.rows:
        if timestamp(row["known_at"]) > instant:
            raise ValueError("Local clock moved behind the durable ledger")
        payload = row["payload"]
        observer.verify_sources(
            data, payload.get("sources", payload.get("snapshot", {}).get("sources", []))
        )
    return observer.status(ledger, protocol, instant)


def observe(directory, mode):
    if mode not in {"preflight", "tick"}:
        raise ValueError("Explicit manual mode required")
    protocol, digest = load(directory)
    # Load operational settings only for an explicit connected invocation.
    from GarimpoInvestimentos.config import settings
    from GarimpoInvestimentos.core.api_guard import allow

    if not settings.API_GUARD_ENABLED or settings.API_GUARD_MAX_INGEST_ASSETS != 28:
        raise ValueError("Required daily ingestion guard unavailable")
    if not allow("ingest", "assets", 28).allowed:
        raise RuntimeError("Daily public ingestion budget exhausted")
    data = directory / "observations"
    source = observer.PublicSource(data)
    try:
        return observer.run(data, protocol, digest, source, mode)
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("prepare", "status", "preflight", "tick"), default="status"
    )
    parser.add_argument("--start", help="New entry midnight in UTC, for prepare only")
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            if not args.start:
                raise ValueError("prepare requires --start")
            result = prepare(args.directory, timestamp(args.start))
        elif args.start:
            raise ValueError("--start is only valid for prepare")
        elif args.mode == "status":
            result = inspect(args.directory)
        else:
            result = observe(args.directory, args.mode)
        print(encoded(result).decode())
    except Exception as exc:
        # Settings errors must not print private environment values.
        parser.exit(1, f"Carry registration failed: {type(exc).__name__}\n")


if __name__ == "__main__":
    main()
