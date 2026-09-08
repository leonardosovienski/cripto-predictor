import concurrent.futures
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

work = Path(__file__).parent
dest = work / 'carry-data'
dest.mkdir(exist_ok=True)
end = datetime(2026, 9, 7, tzinfo=UTC)
start = end - timedelta(days=365)
start_ms, end_ms = int(start.timestamp()*1000), int(end.timestamp()*1000)
manifest = []

def fetch(name, url, params):
    now = datetime.now(UTC).isoformat()
    r = httpx.get(url, params=params, timeout=25, follow_redirects=True)
    rec = {'artifact': name + '.json', 'url': str(r.url), 'known_at': now,
           'http_status': r.status_code, 'sha256': hashlib.sha256(r.content).hexdigest()}
    manifest.append(rec)
    (dest / rec['artifact']).write_bytes(r.content)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError(f'{name}: expected array, got {type(data).__name__}')
    return data

def asset(symbol):
    cursor = start_ms
    rows = []
    page = 0
    while cursor < end_ms:
        part = fetch(f'{symbol}_funding_{page}', 'https://fapi.binance.com/fapi/v1/fundingRate',
                     {'symbol': symbol, 'startTime': cursor, 'endTime': end_ms-1, 'limit':1000})
        if not part: break
        rows.extend(part)
        new_cursor = max(row['fundingTime'] for row in part) + 1
        if new_cursor <= cursor: raise ValueError('pagination did not advance')
        cursor = new_cursor
        page += 1
        if len(part) < 1000: break
        if page > 12: raise ValueError('unexpected excessive pagination')
    timestamps = [row['fundingTime'] for row in rows]
    if len(set(timestamps)) != len(rows): raise ValueError('duplicate timestamp')
    if not all(start_ms <= ts < end_ms for ts in timestamps): raise ValueError('out of cutoff event')
    rows.sort(key=lambda row: row['fundingTime'])
    (dest / f'{symbol}_funding.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    # Two endpoint prices (not fills), plus daily spot range to bound collateral stress.
    spot = fetch(f'{symbol}_spot_daily', 'https://api.binance.com/api/v3/klines',
                 {'symbol':symbol,'interval':'1d','startTime':start_ms,'endTime':end_ms,'limit':500})
    mark = fetch(f'{symbol}_mark_daily', 'https://fapi.binance.com/fapi/v1/markPriceKlines',
                 {'symbol':symbol,'interval':'1d','startTime':start_ms,'endTime':end_ms,'limit':500})
    print(symbol, 'funding',len(rows),'spot_days',len(spot),'mark_days',len(mark), flush=True)
    return {'symbol':symbol,'funding_count':len(rows),'first':timestamps[0] if rows else None,
            'last':timestamps[-1] if rows else None}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(asset, ['BTCUSDT','ETHUSDT']))
for code, name in [(1178,'selic_effective'),(432,'selic_policy')]:
    fetch(name, f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados',
          {'formato':'json','dataInicial':'04/09/2026','dataFinal':'07/09/2026'})
(dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(dest/'download_summary.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print(json.dumps(results))
