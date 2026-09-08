import json
import sys
from pathlib import Path

work = Path(__file__).resolve().parent
sys.path.insert(0, str(work / "cripto-research"))
from scripts.immediate_public import Source, utc
from scripts.research_io import write_atomic

data = work / "immediate-audit-data"
samples = json.loads((data / "live_samples.json").read_bytes())
begin = samples[0]["snapshot"]["quote_ns"] // 1000000
end = samples[-1]["snapshot"]["quote_ns"] // 1000000
target = work / "immediate-intra-hour-check"
target.mkdir(exist_ok=False)
write_atomic(target / "decision.json", {"known_at":utc(), "purpose":"Check public settlements strictly inside the observed five-minute window; do not change frozen PnL", "start_ms":begin+1, "end_ms":end-1})
source = Source(target)
try:
    rows, meta = source.get("funding", {"symbol":"BTCUSDT", "startTime":begin+1, "endTime":end-1, "limit":1000})
    if not isinstance(rows, list):
        raise ValueError("Unexpected funding response")
    result = {"status":"NO_SETTLEMENTS_RETURNED" if not rows else "EVENTS_REQUIRE_REVIEW", "public_events":rows, "source":meta,
              "begin_ms":begin, "end_ms":end,"frozen_accounts_changed":False,"actual_account_receipts_certified":False}
    write_atomic(target / "result.json", result)
    print(json.dumps({"status":result["status"],"events":len(rows)}))
finally:
    source.client.close()
