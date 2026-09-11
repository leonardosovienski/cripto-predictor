import sys
sys.dont_write_bytecode=True
import pathlib,json,hashlib,gzip
import adapter_v3b as a
R=pathlib.Path(__file__).resolve().parents[1];OUT=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else R/'tests_first';OUT.mkdir(parents=True,exist_ok=True)
def read(n):return json.loads((R/n).read_bytes())
contracts=read('INSTRUMENT_CONTRACTS.json');clocks=read('CLOCK_MATRIX.json');obs=read('OBSERVATION_SEMANTICS.json');tests=[]
def check(id,fn,want='ACCEPTED',kind='positive'):
 try:detail=fn();status='ACCEPTED'
 except a.Unsupported as e:detail=str(e);status='UNSUPPORTED'
 except ValueError as e:detail=str(e);status='REJECTED'
 passed=status in want if isinstance(want,list) else status==want
 tests.append({'id':id,'kind':kind,'status':status,'expected':want,'passed':passed,'detail':detail})
for id,c in contracts.items():
 for k,f in c['fields'].items():
  if f['status']!='PROVEN':continue
  for j,e in enumerate(f['evidence']):
   p=pathlib.Path(e['path']);raw=p.read_bytes();d=json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
   for part in e['pointer']:d=d[part]
   value=f['value'];expected=d
   if k=='venue':expected=d.split('/')[2]
   if k=='market_type' and isinstance(value,dict):expected={'isSpotTradingAllowed':d}
   if k=='expiry':value=value['deliveryDate_raw']
   def verify(value=value,expected=expected,raw=raw,e=e):
    if value!=expected or hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError('Field provenance mismatch')
    return True
   check(id+'_'+k+'_literal',verify)
 check(id+'_incomplete',lambda c=c:a.require_contract(c),['UNSUPPORTED'],'unknown')
 for k,v in [('quantity_unit','contract'),('price_unit','USD/BTC'),('multiplier','100'),('settlement_asset','USDC'),('payoff','PnL in margin asset USDT'),('linear_inverse','inverse')]:
  check(id+'_claim_'+k,lambda c=c,k=k,v=v:a.require_contract(c,{k:v}),['REJECTED','UNSUPPORTED'],'negative')
 check(id+'_roundtrip',lambda c=c:json.loads(json.dumps(c))==c)
 check(id+'_wrong_quote',lambda c=c:a.require_contract(c,{'quote_asset':'USD'}),['REJECTED'],'negative')
for o in obs:
 check(o['case']+'_same_metric',lambda o=o:a.require_metric(o,o['type']))
 if o['type']=='trade_candle_close':check(o['case']+'_trade_as_mark',lambda o=o:a.require_metric(o,'mark_candle_close'),['REJECTED'],'negative')
 if o['type']=='mark_candle_close':check(o['case']+'_mark_as_fill',lambda o=o:a.require_metric(o,'executable_fill'),['REJECTED'],'negative')
check('declared_units_BTC_times_USDT_per_BTC',lambda:a.dimension_product({'BTC':1},{'USDT':1,'BTC':-1},{'USDT':1}))
check('wrong_currency_dimension',lambda:a.dimension_product({'BTC':1},{'USD':1,'BTC':-1},{'USDT':1}),['REJECTED'],'negative')
check('contract_as_base_dimension',lambda:a.dimension_product({'contract':1},{'USDT':1,'BTC':-1},{'USDT':1}),['REJECTED'],'negative')
temporal=[]
for c in clocks:
 t=c['clocks']['LOCAL_RECEIPT_TIME']['value']
 if t is None:continue
 contract=contracts['BTC_SPOT'] if c['id'].startswith('spot') else contracts['BTC_PERPETUAL']
 cutoffs=[t-1,t,t+24*3600*10**9]
 candidate=c['preserved_candidates']
 if c['id'].startswith('future_') and 'T' in candidate:cutoffs.append(max(candidate['T']*10**6,t))
 for cutoff in cutoffs:
  result=a.states(c,cutoff,contract)
  temporal.append({'case':c['id'],'cutoff':cutoff,'state':result,'expected_observed':cutoff>=t,'passed':result['OBSERVED']==(cutoff>=t) and result['ECONOMICALLY_ELIGIBLE'] is False})
result={'adapter':a.VERSION,'adapter_sha256':hashlib.sha256((R/'work/adapter_v3b.py').read_bytes()).hexdigest(),'tests':tests,'temporal_tests':temporal,'summary':{'positive':sum(t['kind']=='positive' for t in tests),'negative':sum(t['kind']=='negative' for t in tests),'unknown':sum(t['kind']=='unknown' for t in tests),'total_controls':len(tests),'failed':sum(not t['passed'] for t in tests),'temporal_controls':len(temporal),'temporal_failed':sum(not t['passed'] for t in temporal),'economic_admissions':sum(t['state']['ECONOMICALLY_ELIGIBLE'] for t in temporal),'scope':'Positive economic algebra uses declared units only; no complete real contract implied'}}
(OUT/'RESULTS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
assert all(t['passed'] for t in tests+temporal)
print(json.dumps(result['summary']))
