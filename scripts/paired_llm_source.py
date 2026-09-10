"""Bounded read-only adapters for the paired diagnostic; no SDK retries or orders."""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from scripts.research_io import encoded, sha, strict_json

DAY_MS = 86_400_000


def stamp():
    return datetime.now(UTC)


def bars_from_binance(rows, received):
    """Keep only entire closed UTC bars; normalize end millisecond to close boundary."""
    if not isinstance(rows, list):
        raise ValueError("Expected Binance candle list")
    result = []
    for row in rows:
        if (
            not isinstance(row, list)
            or len(row) < 8
            or type(row[0]) is not int
            or type(row[6]) is not int
        ):
            raise ValueError("Invalid Binance candle")
        opening, closing = row[0], row[6]
        if opening % DAY_MS or closing != opening + DAY_MS - 1:
            raise ValueError("Nonstandard daily candle")
        if closing + 1 > int(received.timestamp() * 1000):
            continue
        result.append(
            {
                "close_utc": datetime.fromtimestamp((closing + 1) / 1000, UTC).isoformat(),
                **dict(zip(("open", "high", "low", "close", "volume_btc"), map(float, row[1:6]))),
            }
        )
    return result


class Source:
    def __init__(self, directory, *, client=None):
        from GarimpoInvestimentos.config import settings
        from GarimpoInvestimentos.security.redaction import configured_secret_values

        self.settings = settings
        if (
            not settings.API_GUARD_ENABLED
            or settings.API_GUARD_MAX_INGEST_ASSETS != 28
            or settings.API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER != 8
            or settings.API_GUARD_MAX_LLM_CALLS_PER_PROVIDER != 6
        ):
            raise ValueError("Required persistent 28/8/6 guards unavailable")
        self.directory = directory
        self.client = client or httpx.Client(timeout=45, trust_env=False, follow_redirects=False)
        self.secrets = configured_secret_values()
        self.records = []
        self.calls, self.bytes = 0, 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def guard(self, stage, key, limit):
        from GarimpoInvestimentos.core.api_guard import allow

        if not allow(stage, key, limit).allowed:
            raise ValueError("Persistent daily budget exhausted")

    def request(
        self, name, method, url, *, public_params=None, params=None, body=None, headers=None
    ):
        from GarimpoInvestimentos.security.redaction import safe_redact_text

        def redact(value: Any) -> Any:
            # Redact JSON string VALUES rather than a serialized document: a
            # URL redactor may consume JSON delimiters following a credential.
            if isinstance(value, str):
                return safe_redact_text(value, self.secrets)
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, dict):
                return {
                    safe_redact_text(key, self.secrets): redact(item) for key, item in value.items()
                }
            return value

        if self.calls >= 8:
            raise ValueError("Physical request budget exhausted")
        self.calls += 1
        start, mono = stamp(), time.monotonic()
        record = {
            "name": name,
            "url": url,
            "public_params": public_params,
            "started_utc": start.isoformat(),
            "request_json": body,
            "physical_attempt": self.calls,
            "retries": 0,
        }
        result = None
        try:
            with self.client.stream(
                method, url, params=params, json=body, headers=headers
            ) as response:
                record["http_status"] = response.status_code
                raw = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    raw.extend(chunk)
                    self.bytes += len(chunk)
                    if len(raw) > 3_000_000 or self.bytes > 12_000_000:
                        raise ValueError("Response byte limit")
                # Redact before serialization/hashing/persistence. Never retain headers
                # or an authenticated URL, even when the provider echoes its inputs.
                record["response_text"] = safe_redact_text(raw.decode("utf-8"), self.secrets)
                result = redact(strict_json(bytes(raw)))
                record["response_json"] = result
                del record["response_text"]
                response.raise_for_status()
        except Exception as exc:
            record["error_type"] = type(exc).__name__
            raise
        finally:
            received = stamp()
            record.update(
                received_utc=received.isoformat(), elapsed_seconds=time.monotonic() - mono
            )
            safe = encoded(redact(record))
            self.directory.mkdir(parents=True, exist_ok=True)
            name_on_disk = uuid.uuid4().hex + ".json"
            with (self.directory / name_on_disk).open("xb") as stream:
                stream.write(safe + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            self.records.append(
                {
                    "file": name_on_disk,
                    "sha256": sha(safe + b"\n"),
                    "received_utc": received.isoformat(),
                    "name": name,
                }
            )
        if abs((received - start).total_seconds() - record["elapsed_seconds"]) > 1:
            raise ValueError("Local clock moved during request")
        return result, received

    def market(self):
        self.guard("ingest", "assets", 28)
        current, received = self.request(
            "binance_time", "GET", "https://api.binance.com/api/v3/time"
        )
        if not isinstance(current, dict) or type(current.get("serverTime")) is not int:
            raise ValueError("Invalid public clock response")
        if abs(current["serverTime"] / 1000 - received.timestamp()) > 5:
            raise ValueError("Public clock differs from local clock")
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 201}
        raw, received = self.request(
            "binance_market",
            "GET",
            "https://api.binance.com/api/v3/klines",
            public_params=params,
            params=params,
        )
        return bars_from_binance(raw, received)[-200:]

    def news(self):
        self.guard("news", "serpapi", 8)
        params = {"engine": "google_news", "q": "Bitcoin", "hl": "en", "gl": "us"}
        data, received = self.request(
            "serpapi_news",
            "GET",
            "https://serpapi.com/search.json",
            public_params=params,
            params={**params, "api_key": self.settings.SERP_API_KEY},
        )
        if (
            not isinstance(data, dict)
            or data.get("error")
            or not isinstance(data.get("news_results"), list)
        ):
            raise ValueError("News response unavailable")
        flattened = []
        for row in data["news_results"]:
            flattened.extend(row.get("stories", [row]))
        selected = []
        for row in flattened:
            try:
                published = datetime.fromisoformat(row["iso_date"])
                if published.tzinfo is None:
                    continue
                published = published.astimezone(UTC)
            except (KeyError, TypeError, ValueError):
                continue
            if received - timedelta(days=7) <= published <= received:
                selected.append(
                    {
                        "title": row["title"],
                        "published_utc": published.isoformat(),
                        "url": row.get("link"),
                        "source": row.get("source"),
                    }
                )
            if len(selected) == 5:
                break
        if not selected:
            raise ValueError("No news with verifiable publication timestamp")
        return selected

    def generate(self, prompt, p):
        self.guard("llm", "gemini", 6)
        config = {
            "temperature": p["temperature"],
            "responseMimeType": "application/json",
            "maxOutputTokens": p["max_output_tokens"],
            "thinkingConfig": {"thinkingBudget": p["thinking_budget"]},
        }
        data, _ = self.request(
            "gemini",
            "POST",
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + p["model"]
            + ":generateContent",
            body={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": config,
            },
            headers={"x-goog-api-key": self.settings.GEMINI_API_KEY},
        )
        if not isinstance(data, dict) or data.get("modelVersion") != p["model"]:
            raise ValueError("Unexpected model version")
        candidates = data.get("candidates", [])
        if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
            raise ValueError("Incomplete model response")
        parts = candidates[0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts if not part.get("thought", False))

    def outcomes(self, p):
        start = datetime.fromisoformat(p["start_utc"]).replace(hour=0)
        # At most 94 days covers all 84 slots, delayed full-bar anchor and target.
        end = min(stamp(), start + timedelta(days=94))
        if end <= start:
            raise ValueError("Outcome window has not started")
        self.guard("ingest", "assets", 28)
        params = {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "limit": 100,
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000) - 1,
        }
        data, received = self.request(
            "binance_outcomes",
            "GET",
            "https://api.binance.com/api/v3/klines",
            public_params=params,
            params=params,
        )
        return {
            "source": "binance_spot",
            "symbol": "BTCUSDT",
            "received_utc": received.isoformat(),
            "bars": bars_from_binance(data, received),
            "sources": self.records,
        }
