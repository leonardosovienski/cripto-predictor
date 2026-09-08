import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

root = Path(__file__).resolve().parent / 'altcoin-forward-probes'
root.mkdir(exist_ok=True)
urls = {
 'exchangeInfo': 'https://data-api.binance.vision/api/v3/exchangeInfo',
 'depth_btc': 'https://data-api.binance.vision/api/v3/depth?symbol=BTCUSDT&limit=100',
 'delistings': 'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50&catalogId=161',
 'updates': 'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50&catalogId=49',
}
with httpx.Client(timeout=20, follow_redirects=True) as client:
 for name,url in urls.items():
  start=time.perf_counter()
  r=client.get(url)
  meta={'url':url,'known_at':datetime.now(timezone.utc).isoformat(),'status':r.status_code,'elapsed_ms':(time.perf_counter()-start)*1000,'sha256':hashlib.sha256(r.content).hexdigest()}
  (root/f'{name}.bin.gz').write_bytes(gzip.compress(r.content,mtime=0))
  (root/f'{name}.json').write_text(json.dumps(meta,indent=2))
  try:
   data=r.json()
   meta['keys']=list(data) if isinstance(data,dict) else 'array'
   if name=='exchangeInfo': meta['symbols']=len(data.get('symbols',[]))
   if name in ('delistings','updates'): meta['sample']=str(data)[:1700]
  except Exception: meta['body_prefix']=r.text[:100]
  print(json.dumps({'name':name,**meta}))
