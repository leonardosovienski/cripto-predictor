import concurrent.futures
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

dest = Path(__file__).parent / 'public-sources'
dest.mkdir(exist_ok=True)
urls = {
    'fees': 'https://www.binance.com/bapi/futures/v1/public/future/common/trade-fee',
    'funding': 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3',
    'treasury': 'https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json',
    'selic': 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json',
    'selic_effective': 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados/ultimos/1?formato=json',
}

def get(item):
    name, url = item
    rec = {'name': name, 'url': url, 'accessed_at': datetime.now(UTC).isoformat()}
    try:
        r = httpx.get(url, timeout=22, follow_redirects=True)
        rec.update(status=r.status_code, sha256=hashlib.sha256(r.content).hexdigest())
        (dest / (name + '.txt')).write_bytes(r.content)
        try:
            rec['data'] = r.json()
        except ValueError:
            rec['data'] = 'NON_JSON'
    except httpx.HTTPError as exc:
        rec['error'] = type(exc).__name__
    return rec

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(get, urls.items()))
(dest / 'manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
for rec in results:
    print(json.dumps(rec, ensure_ascii=False)[:3500])
