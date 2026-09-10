"""Immutable observations: reject conflicts before atomically appending new keys."""

from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from GarimpoInvestimentos.durable_io import atomic_write, file_lock


def validate_observation(symbol: str, timestamp: int, values: dict[str, float]) -> None:
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9]{2,30}", symbol):
        raise ValueError("symbol invalido")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("timestamp deve ser inteiro nao negativo em ms")
    for name, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} deve ser finito")


def unique_records[T](records: Sequence[T], timestamp: str) -> list[T]:
    by_time: dict[int, T] = {}
    symbols = set()
    for row in records:
        symbols.add(getattr(row, "symbol"))
        key = getattr(row, timestamp)
        if key in by_time and by_time[key] != row:
            raise ValueError(f"Observacoes conflitantes no timestamp {key}")
        by_time[key] = row
    if len(symbols) > 1:
        raise ValueError("CSV exige um unico symbol")
    return [by_time[key] for key in sorted(by_time)]


def load_records[T](
    path: Path, fields: list[str], parse: Callable[[dict], T], timestamp: str
) -> list[T]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"Cabecalho invalido: {path}")
        records = [parse(row) for row in reader]
    return unique_records(records, timestamp)


def save_records(
    records: list[Any], path: Path, fields: list[str], load: Callable, timestamp: str
) -> int:
    with file_lock(path):
        existing = load(path)
        combined = unique_records([*existing, *records], timestamp)
        added = len(combined) - len(existing)
        if added:
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(asdict(record) for record in combined)
            atomic_write(path, output.getvalue().encode("utf-8-sig"))
        return added


def validate_page(records: Sequence, symbol: str, timestamp: str, start: int, end: int) -> None:
    previous = start - 1
    for row in records:
        current = getattr(row, timestamp)
        if row.symbol != symbol or not start <= current <= end or current <= previous:
            raise ValueError("Pagina fora do intervalo, symbol divergente ou cursor sem progresso")
        previous = current
