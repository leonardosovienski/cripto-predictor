"""Rebuild the collected snapshot using recorded responses only."""
import gzip
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

repo=Path(__file__).resolve().parent/'cripto-v1.2'
sys.path.insert(0,str(repo))
from scripts.observe_altcoin_forward import snapshot
data=repo.parent/'altcoin-forward-data'
cache={}
for p in (data/'raw').glob('*.json'):
 meta=json.loads(p.read_text())
 u=urlparse(meta['url'])
 key=(u.path,tuple(sorted((k,v[0]) for k,v in parse_qs(u.query).items())))
 body=gzip.decompress(p.with_suffix('.bin.gz').read_bytes())
 assert hashlib.sha256(body).hexdigest()==meta['sha256']
 cache[key]=(json.loads(body),meta)
class RecordedSource:
 def get(self,endpoint,params=None):
  path='/bapi/composite/v1/public/cms/article/list/query' if endpoint=='cms' else '/api/v3/'+endpoint
  return cache[(path,tuple(sorted((k,str(v)) for k,v in (params or {}).items())))]
original=json.loads(next((data/'snapshots').glob('*.json')).read_text())
rebuilt=snapshot(RecordedSource(),datetime.fromisoformat(original['anchor_utc']),repo.parent/'altcoin-data',repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz')
original.pop('recorded_after_acquisition')
rebuilt.pop('recorded_after_acquisition')
assert rebuilt==original
(data/'replay_validation.json').write_text(json.dumps({'offline_snapshot_semantically_identical':True,'ignored_field':'recorded_after_acquisition (new execution clock only)','public_requests_made':0,'eligible_count':len(rebuilt['ranked']),'selected':rebuilt['selected']},indent=2))
print((data/'replay_validation.json').read_text())
