import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts import paired_llm as paired
from scripts.paired_llm_source import bars_from_binance
from scripts.research_io import encoded


class Clock:
    def __init__(self):
        self.t = datetime(2026, 9, 10, 12, tzinfo=UTC)

    def __call__(self):
        return self.t


class Source:
    def __init__(self, clock):
        self.clock = clock
        self.records = []
        self.prompts = []
        self.fail_call = None
        self.bad_json = False
        self.crash = False
        self.delay = timedelta(seconds=1)

    def market(self):
        end = self.clock().replace(hour=0, minute=0, second=0, microsecond=0)
        return [
            {
                "close_utc": (end - timedelta(days=199 - i)).isoformat(),
                "open": 100 + i,
                "high": 102 + i,
                "low": 99 + i,
                "close": 101 + i,
                "volume_btc": 1,
            }
            for i in range(200)
        ]

    def news(self):
        return [
            {
                "title": "Observed headline",
                "published_utc": (self.clock() - timedelta(hours=1)).isoformat(),
            }
        ]

    def generate(self, prompt, protocol):
        self.prompts.append(prompt)
        self.clock.t += self.delay
        if self.crash:
            raise KeyboardInterrupt()
        if len(self.prompts) == self.fail_call:
            raise TimeoutError("synthetic failure")
        if self.bad_json:
            return '{"opportunity_score":true,"summary":"invalid"}'
        return json.dumps(
            {
                "opportunity_score": 70 if "Observed headline" in prompt else 30,
                "summary": "synthetic diagnostic",
            }
        )


@pytest.fixture
def run(tmp_path, monkeypatch):
    root = tmp_path / "code"
    root.mkdir()
    (root / "executor.py").write_text("original code")
    monkeypatch.setattr(paired, "ROOT", root)
    monkeypatch.setattr(paired, "FREEZE_FILES", ("executor.py",))
    monkeypatch.setattr(paired, "environment", lambda: {"runtime": "test"})
    clock = Clock()
    start = clock() + timedelta(days=2)
    directory = tmp_path / "registered"
    paired.prepare(directory, start, clock=clock)
    source = Source(clock)
    return directory, start, clock, source


def test_status_never_creates_ledger_or_network(run):
    directory, start, clock, source = run
    assert paired.inspect(directory, clock=clock)["counts"] == {"FUTURE": 84}
    assert not (directory / "ledger.jsonl").exists()
    clock.t = start + timedelta(days=1, hours=2)
    assert paired.inspect(directory, clock=clock)["counts"]["MISSED"] == 2
    assert source.prompts == []


def test_pair_inputs_are_identical_except_news_and_anchor_is_future_full_bar(run):
    directory, start, clock, source = run
    clock.t = start
    result = paired.tick(directory, source, clock=clock)
    assert result["state"] == "PAIRED"
    a, b = [json.loads(text.split("CONTEXTO:\n", 1)[1]) for text in source.prompts]
    assert a["market"] == b["market"]
    assert len(a["market"]["bars"]) == 200
    assert a["news"] and b["news"] == []
    assert result["anchor_close_utc"] == (start.replace(hour=0) + timedelta(days=2)).isoformat()
    assert result["target_close_utc"] == (start.replace(hour=0) + timedelta(days=9)).isoformat()
    before = (directory / "ledger.jsonl").read_bytes()
    assert paired.tick(directory, source, clock=clock)["state"] == "ALREADY_ATTEMPTED_NO_REPLAY"
    assert len(source.prompts) == 2 and before == (directory / "ledger.jsonl").read_bytes()


@pytest.mark.parametrize("failure", ["timeout", "invalid_json", "crash", "late"])
def test_failures_are_durable_and_never_replayed(run, failure):
    directory, start, clock, source = run
    clock.t = start
    source.fail_call = 2 if failure == "timeout" else None
    source.bad_json = failure == "invalid_json"
    source.crash = failure == "crash"
    source.delay = timedelta(hours=1) if failure == "late" else timedelta(seconds=1)
    if failure == "crash":
        with pytest.raises(KeyboardInterrupt):
            paired.tick(directory, source, clock=clock)
    else:
        assert paired.tick(directory, source, clock=clock)["state"] == "PAIR_FAILED"
    count = len(source.prompts)
    clock.t = start + timedelta(minutes=59)
    if failure == "late":
        # Never move backwards behind durable evidence merely to replay a slot.
        with pytest.raises(ValueError):
            paired.tick(directory, source, clock=clock)
    else:
        assert paired.tick(directory, source, clock=clock)["state"] == "ALREADY_ATTEMPTED_NO_REPLAY"
    assert len(source.prompts) == count


def test_missing_market_bars_fail_before_llm(run):
    directory, start, clock, source = run
    clock.t = start
    old = source.market
    source.market = lambda: old()[:-1]
    assert paired.tick(directory, source, clock=clock)["state"] == "INPUT_FAILED"
    assert source.prompts == []


def test_future_news_is_rejected_before_llm(run):
    directory, start, clock, source = run
    clock.t = start
    source.news = lambda: [
        {"title": "Future", "published_utc": (clock() + timedelta(hours=1)).isoformat()}
    ]
    assert paired.tick(directory, source, clock=clock)["state"] == "INPUT_FAILED"
    assert source.prompts == []


def test_changed_code_environment_and_ledger_rejected(run, monkeypatch):
    directory, start, clock, source = run
    clock.t = start
    paired.tick(directory, source, clock=clock)
    with (directory / "ledger.jsonl").open("ab") as stream:
        stream.write(b'{"incomplete":')
    with pytest.raises(ValueError):
        paired.inspect(directory, clock=clock)
    (paired.ROOT / "executor.py").write_text("changed")
    with pytest.raises(ValueError):
        paired.load(directory, clock=clock)


def test_no_backdated_registration_or_outside_slot_calls(run, tmp_path):
    directory, start, clock, source = run
    with pytest.raises(ValueError):
        paired.prepare(tmp_path / "bad", clock(), clock=clock)
    with pytest.raises(ValueError):
        paired.tick(directory, source, clock=clock)
    clock.t = start + timedelta(hours=2)
    with pytest.raises(ValueError):
        paired.tick(directory, source, clock=clock)
    assert source.prompts == []


def test_outcomes_use_eight_exact_closes_not_rows_and_constant_scores_undefined(run):
    directory, start, clock, source = run
    for offset in (0, 1, 7, 14):
        clock.t = start + timedelta(days=offset)
        paired.tick(directory, source, clock=clock)
    clock.t = start + timedelta(days=24)
    bars = [
        {"close_utc": (start.replace(hour=0) + timedelta(days=i)).isoformat(), "close": 100 + i * i}
        for i in range(25)
    ]
    prices = {
        "source": "binance_spot",
        "symbol": "BTCUSDT",
        "received_utc": clock().isoformat(),
        "bars": bars,
    }
    result = paired.evaluate(directory, prices, clock=clock, synthetic=True)
    assert result["daily_overlapping"]["n"] == 4
    assert result["nonoverlapping"]["n"] == 3
    assert result["daily_overlapping"]["primary_difference"] is None
    assert result["logical_llm_requests"] == 8
    assert result["counts"]["MISSED"] == 20
    prices["bars"] = [
        bar
        for bar in bars
        if bar["close_utc"] != (start.replace(hour=0) + timedelta(days=5)).isoformat()
    ]
    assert (
        paired.evaluate(directory, prices, clock=clock, synthetic=True)["daily_overlapping"]["n"]
        == 2
    )
    prices["source"] = "other"
    with pytest.raises(ValueError):
        paired.evaluate(directory, prices, clock=clock)


def test_rank_correlation_reference_with_ties():
    assert paired.ranks([20, 10, 20, 30]) == [2.5, 1, 2.5, 4]
    assert paired.spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1)
    assert paired.spearman([1, 2, 3], [30, 20, 10]) == pytest.approx(-1)
    assert paired.spearman([1, 1, 1], [30, 20, 10]) is None


def test_source_evidence_tampering_is_rejected(run):
    directory, start, clock, source = run
    clock.t = start
    folder = directory / "sources"
    folder.mkdir()
    name = "a" * 32 + ".json"
    raw = encoded({"started_utc": clock().isoformat(), "received_utc": clock().isoformat()})
    (folder / name).write_bytes(raw)
    source.records = [{"file": name, "sha256": paired.sha(raw)}]
    paired.tick(directory, source, clock=clock)
    (folder / name).write_bytes(b"changed")
    with pytest.raises(ValueError):
        paired.inspect(directory, clock=clock)


def test_binance_candles_are_closed_and_daily():
    t = datetime(2026, 9, 10, tzinfo=UTC)
    ms = int(t.timestamp() * 1000)
    daily = [ms, "100", "110", "90", "105", "3", ms + 86400000 - 1, "315"]
    assert bars_from_binance([daily], t + timedelta(hours=23)) == []
    assert (
        bars_from_binance([daily], t + timedelta(days=1))[0]["close_utc"]
        == (t + timedelta(days=1)).isoformat()
    )
    daily[6] -= 1
    with pytest.raises(ValueError):
        bars_from_binance([daily], t + timedelta(days=1))


@pytest.mark.parametrize(
    "text",
    [
        '{"opportunity_score":NaN,"summary":"x"}',
        '{"opportunity_score":101,"summary":"x"}',
        '{"opportunity_score":50,"opportunity_score":60,"summary":"x"}',
        '{"opportunity_score":true,"summary":"x"}',
    ],
)
def test_invalid_llm_score_is_never_neutral(text):
    with pytest.raises(ValueError):
        paired.score(text)


def test_json_redaction_preserves_structure_and_never_saves_key(tmp_path, monkeypatch):
    import httpx

    from GarimpoInvestimentos.config import settings
    from scripts.paired_llm_source import Source as ConnectedSource

    for name, value in (
        ("API_GUARD_ENABLED", True),
        ("API_GUARD_MAX_INGEST_ASSETS", 28),
        ("API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER", 8),
        ("API_GUARD_MAX_LLM_CALLS_PER_PROVIDER", 6),
    ):
        monkeypatch.setattr(settings, name, value)
    secret = "synthetic-private-token-for-test"
    payload = {
        "search_metadata": {"json_endpoint": "https://example.test/search?api_key=" + secret},
        "news_results": [{"title": 'Quoted "headline"', "iso_date": "2026-09-10T00:00:00Z"}],
    }
    client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    )
    with ConnectedSource(tmp_path, client=client) as source:
        source.secrets = (secret,)
        result, _ = source.request("test", "GET", "https://example.test")
        assert result["news_results"][0]["title"] == 'Quoted "headline"'
    for path in tmp_path.iterdir():
        raw = path.read_text()
        assert secret not in raw
        assert isinstance(json.loads(raw), dict)


def test_outcomes_require_original_source_and_reject_modified_price(run):
    directory, start, clock, source = run
    clock.t = start + timedelta(days=20)
    ms = int(start.replace(hour=0).timestamp() * 1000)
    raw_bar = [ms, "100", "110", "90", "105", "3", ms + 86400000 - 1, "315"]
    raw = {
        "name": "binance_outcomes",
        "url": "https://api.binance.com/api/v3/klines",
        "http_status": 200,
        "public_params": {"symbol": "BTCUSDT", "interval": "1d"},
        "started_utc": clock().isoformat(),
        "received_utc": clock().isoformat(),
        "response_json": [raw_bar],
    }
    raw_bytes = encoded(raw)
    folder = directory / "sources"
    folder.mkdir()
    name = "b" * 32 + ".json"
    (folder / name).write_bytes(raw_bytes)
    prices = {
        "source": "binance_spot",
        "symbol": "BTCUSDT",
        "received_utc": clock().isoformat(),
        "bars": bars_from_binance([raw_bar], clock()),
        "sources": [{"file": name, "sha256": paired.sha(raw_bytes)}],
    }
    assert (
        paired.evaluate(directory, prices, clock=clock)["evidence_kind"]
        == "RECORDED_PUBLIC_ACQUISITION"
    )
    prices["bars"][0]["close"] = 999
    with pytest.raises(ValueError):
        paired.evaluate(directory, prices, clock=clock)
    prices.pop("sources")
    with pytest.raises(ValueError):
        paired.evaluate(directory, prices, clock=clock)


def test_changed_runtime_is_refused(run, monkeypatch):
    directory, start, clock, source = run
    monkeypatch.setattr(paired, "environment", lambda: {"runtime": "different"})
    with pytest.raises(ValueError):
        paired.load(directory, clock=clock)
