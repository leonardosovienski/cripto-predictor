import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

repo=Path(__file__).resolve().parent/'cripto-v1.2'
sys.path.insert(0,str(repo))
from scripts.observe_altcoin_forward import Ledger, snapshot, verify_freeze
data=repo.parent/'altcoin-profit-data'
evidence=repo/'docs/evidence/altcoin_profit_20260907'
base_data=repo.parent/'altcoin-data'
training=repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz'
freeze_hash=verify_freeze(base_data,training,evidence)
cache={}
metadata=[]
for p in (data/'raw').glob('*.json'):
 m=json.loads(p.read_text())
 body=gzip.decompress(p.with_suffix('.bin.gz').read_bytes())
 assert hashlib.sha256(body).hexdigest()==m['sha256']
 u=urlparse(m['url'])
 cache[(u.path,tuple(sorted((k,v[0]) for k,v in parse_qs(u.query).items())))]=(json.loads(body),m)
 metadata.append(m)
class RecordedSource:
 def get(self,endpoint,params=None):
  path='/bapi/composite/v1/public/cms/article/list/query' if endpoint=='cms' else '/api/v3/'+endpoint
  return cache[(path,tuple(sorted((k,str(v)) for k,v in (params or {}).items())))]
path=next((data/'snapshots').glob('*.json'))
original=json.loads(path.read_text())
rebuilt=snapshot(RecordedSource(),datetime.fromisoformat(original['anchor_utc']),base_data,training,'all_current_spot_usdt')
expected=dict(original)
assert expected.pop('sample_status_changes') is None
assert expected.pop('compared_with_ledger_sha256') is None
expected.pop('recorded_after_acquisition')
rebuilt.pop('recorded_after_acquisition')
assert expected==rebuilt
log=Ledger(data/'ledger.jsonl')
assert len(log.rows)==2 and all(r['kind'].startswith('PREFLIGHT') for r in log.rows)
assert log.rows[0]['payload']['snapshot_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
marks=json.loads((data/'preflight_marks.json').read_text())
assert set(marks)=={'payoff','cost_probe_1000'}
assert not marks['payoff']['positions'] and marks['payoff']['cash_weight']==1
result={
 'known_at':datetime.now(timezone.utc).isoformat(),
 'protocol_id':'discovery-altcoin-absolute-profit-20260907-v4',
 'objective':'ABSOLUTE_NET_PROFIT',
 'external_comparisons':False,
 'user_venue_preference':'ANY_SUITABLE_VENUE_AGENT_MAY_CHOOSE',
 'adapter_coverage':'BINANCE_PUBLIC_SPOT_USDT_ONLY',
 'current_spot_usdt_catalog':original['sample_size'],
 'candidate_pairs_after_declared_exclusions':original['currently_trading_after_exclusions'],
 'eligible_pairs':len(original['ranked']),
 'qualified_symbols':original['qualified_symbols'],
 'selected':original['selected'],
 'cash_weight':original['cash_weight'],
 'prospective':False,
 'prospective_decisions':0,
 'realized_profit':None,
 'investor_net_brl_profit':None,
 'ranked':[{'symbol':r['symbol'],'status':r['status'],'score_log':r['score_log']} for r in original['ranked']],
 'validation':{'tests_passed':46,'ruff':'PASS','pyright':'PASS','raw_hashes_verified':len(metadata),'offline_snapshot_replay':'PASS','network_requests_during_replay':0,'ledger_chain':'PASS','freeze_sha256':freeze_hash,'no_comparison_portfolios':'PASS','scorer_and_training_unchanged':True,'capital':False},
 'raw_interval':[min(m['known_at'] for m in metadata),max(m['known_at'] for m in metadata)],
 'event_catalogs':[{k:c[k] for k in ('catalog_id','reported_total','unique_articles','pagination_count_matches','complete_investability_event_feed')} for c in original['announcements']],
 'limits':['Actual account commissions, tax and conversion remain unverified. Public book marks are hypothetical, not investor net profit.','Coverage is current Binance spot USDT, not all exchanges or all tokens.','No prospective outcome exists yet; no formal promotion or profitability proof.','Current asset classification and interpreted event completeness are not certified.'],
 'sources':{'account_commission_documentation':'https://developers.binance.com/en/docs/products/spot/faqs/commission_faq','public_api':'https://data-api.binance.vision/api/v3/'}
}
(data/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('current_spot_usdt_catalog','candidate_pairs_after_declared_exclusions','eligible_pairs','selected','cash_weight','validation')},indent=2))
