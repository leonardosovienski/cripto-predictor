import gzip
import hashlib
import json
import sys
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
import numpy as np

repo=Path(__file__).resolve().parent/'cripto-v1.2'
sys.path.insert(0,str(repo))
from scripts.observe_altcoin_forward import Ledger, sell_mark
data=repo.parent/'altcoin-forward-data'
ledger=Ledger(data/'ledger.jsonl')
snap_path=sorted((data/'snapshots').glob('*.json'))[-1]
snap=json.loads(snap_path.read_text())
base=json.loads(gzip.decompress((repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz').read_bytes()))
known={r['symbol']:r for r in base if r['period']=='current'}
old_scores={r['symbol']:r for r in json.loads((repo.parent/'altcoin-payoff-results/results.json').read_text())['payoff_snapshot']['ranked']}
parity=[{'symbol':r['symbol'],'max_feature_difference':float(np.max(np.abs(np.array(r['features'])-np.array(known[r['symbol']]['features'])))),'score_difference':r['score_log']-old_scores[r['symbol']]['score_log']} for r in snap['ranked'] if r['symbol'] in known]
raw=[]
for p in sorted((data/'raw').glob('*.json')):
 m=json.loads(p.read_text())
 body=gzip.decompress(p.with_suffix('.bin.gz').read_bytes())
 assert hashlib.sha256(body).hexdigest()==m['sha256']
 raw.append(m)
costs=[]
marks=json.loads((data/'preflight_marks.json').read_text())
for p in marks['cost_probe_1000']['positions']:
 if not p['entry']:
  costs.append({'symbol':p['symbol'],'error':p['reason']})
  continue
 e=p['entry']
 book=json.loads(gzip.decompress((data/p['source']['raw_file']).read_bytes()))
 cash=sell_mark(book,e['quantity_after_assumed_fee_and_extra_slippage']['0'])*Decimal('.999')
 loss=1-float(cash/Decimal(str(e['notional_usdt'])))
 costs.append({'symbol':p['symbol'],'notional_usdt':e['notional_usdt'],'spread_bps':e['spread_bps'],'buy_impact_from_best_ask_bps':e['buy_impact_from_best_ask_bps'],'hypothetical_same_book_roundtrip_loss_bps':loss*10000,'hypothetical_same_book_roundtrip_loss_usdt':loss*e['notional_usdt'],'source_known_at':p['source']['known_at'],'request_ms':p['source']['elapsed_ms']})
result={'known_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':hashlib.sha256(snap_path.read_bytes()).hexdigest(),'sample_size':snap['sample_size'],'currently_trading_after_exclusions':snap['currently_trading_after_exclusions'],'eligible_count':len(snap['ranked']),'selected':snap['selected'],'cash_weight':snap['cash_weight'],'prospective':False,'ranked':[{'symbol':s['symbol'],'status':s['status'],'score_log':s['score_log']} for s in snap['ranked']],'raw_responses_verified':len(raw),'raw_interval':[min(r['known_at'] for r in raw),max(r['known_at'] for r in raw)],'ledger_chain_valid':True,'clock_offset_seconds':snap['clock']['offset_seconds'],'feature_score_parity':parity,'event_catalogs':[{k:c[k] for k in ('catalog_id','reported_total','unique_articles','pagination_count_matches','complete_investability_event_feed')} for c in snap['announcements']],'costs':costs,'fee_status':'ASSUMED_10_BPS_PER_LEG_NOT_ACCOUNT_SPECIFIC','mark_status':'Visible book hypothetical roundtrip; not actual orders, fills, future costs or net investor P&L','economic_inputs':{'operator_venue':None,'operator_account_commissions':None,'operator_attainable_benchmark':None,'reporting_currency':'BRL','mark_currency':'USDT','fx_conversion_and_tax_route':None,'conditional_research_venue':'Binance public spot data','conditional_benchmark':'Dated Selic scenario from funding_carry_screen_20260907, not confirmed as user-attainable'},'readiness':{'public_feed':'AVAILABLE_OBSERVED','event_catalog_pagination':'COUNTS_VERIFIED','complete_interpreted_investability_events':'UNKNOWN','three_historical_exits':'BTT, CVP, VIDT remain censored','model_causal_tests':'EXECUTED','prospective_hypothetical_observer':'IMPLEMENTED_PENDING_FIRST_SLOT','executable_paper_fill_parity':'NOT_CERTIFIED','actual_account_costs':'UNKNOWN','formal_model_specific_attestation':'NOT_ISSUED','formal_proof':'NOT_PASSED','orders':False,'capital':False}}
(data/'audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
