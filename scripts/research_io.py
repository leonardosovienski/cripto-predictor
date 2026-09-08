"""Strict bounded data and durable research storage, with no network capability."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encoded(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def strict_json(raw: bytes | str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Nonfinite JSON number: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def integer(value, minimum=0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError("Expected finite integer")
    return value


def write_atomic(path: Path, value) -> None:
    raw = encoded(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def exclusive(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "observer.lock").open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b" ")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise FileExistsError("Research observer is already running") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


class Ledger:
    def __init__(self, path: Path):
        self.path, self.rows = path, []
        if path.exists():
            raw = path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                raise ValueError("Incomplete ledger tail; preserve and investigate")
            for line in raw.splitlines():
                row = strict_json(line)
                recorded = row.pop("sha256")
                previous = self.rows[-1]["sha256"] if self.rows else "0" * 64
                if (
                    row["previous"] != previous
                    or row["sequence"] != len(self.rows)
                    or sha(encoded(row)) != recorded
                ):
                    raise ValueError("Damaged ledger chain")
                row["sha256"] = recorded
                if self.find(row["kind"], row["slot"]) is not None:
                    raise ValueError("Duplicate ledger event")
                self.rows.append(row)

    def find(self, kind: str, slot: str):
        return next((r for r in self.rows if r["kind"] == kind and r["slot"] == slot), None)

    def append(self, kind: str, slot: str, payload: dict, known_at: str):
        if self.find(kind, slot) is not None:
            raise ValueError("Duplicate ledger event")
        row = {
            "sequence": len(self.rows),
            "kind": kind,
            "slot": slot,
            "known_at": known_at,
            "previous": self.rows[-1]["sha256"] if self.rows else "0" * 64,
            "payload": payload,
        }
        row["sha256"] = sha(encoded(row))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as stream:
            stream.write(encoded(row) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.rows.append(row)
        return row
