"""Isolated phase-2 research. Does not import production configuration or make requests."""
import ast,dataclasses,datetime,decimal,gzip,hashlib,itertools,json,math,pathlib,socket,time
from dataclasses import dataclass,replace
from decimal import Decimal as D
from fractions import Fraction as Q
import numpy as np
from scipy.stats import norm
ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
decimal.getcontext().prec=40
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def denied(*a,**kw):raise RuntimeError('No network authorized in phase2 offline experiment')
socket.socket.connect=denied;socket.create_connection=denied
def reject(fn):
 try:fn();return False
 except (ValueError,TypeError):return True

@dataclass(frozen=True)
class Instrument:
 venue:str;market:str;base_asset:str;quote_asset:str;settlement_asset:str
 chain:str;contract:str;expiry:str;multiplier:str;payoff:str;quantity_unit:str;price_unit:str
 def __post_init__(self):
  if any(not isinstance(v,str) or not v for v in dataclasses.asdict(self).values()):raise ValueError('Explicit identity required; use N/A for structural absence')
  if self.market not in ['spot','perpetual','future']:raise ValueError('Unsupported instrument type; no guessed options identity')
  m=D(self.multiplier)
  if not m.is_finite() or m<=0:raise ValueError('Bad multiplier')
  if self.market=='future' and self.expiry=='N/A':raise ValueError('Future requires expiry')
  if self.market=='spot' and self.payoff!='spot':raise ValueError('Inconsistent payoff')
  if self.market!='spot' and self.payoff not in ['linear','inverse']:raise ValueError('Unsupported derivative payoff')
  if self.price_unit!=self.quote_asset+'/'+self.base_asset:raise ValueError('Price unit contradicts explicit assets')
  if self.payoff=='spot' and (self.quantity_unit!=self.base_asset or self.settlement_asset!=self.quote_asset):raise ValueError('Unsupported spot quantity/settlement')
  if self.payoff=='linear' and (self.settlement_asset!=self.quote_asset or self.quantity_unit not in [self.base_asset,'contract']):raise ValueError('Unsupported linear settlement/quantity')
  if self.payoff=='inverse' and (self.settlement_asset!=self.base_asset or self.quantity_unit!=self.quote_asset+'_contract'):raise ValueError('Unsupported inverse settlement/quantity')
  object.__setattr__(self,'multiplier',format(m.normalize(),'f'))

@dataclass(frozen=True)
class Observation:
 instrument:Instrument;event_at:int;published_at:int;received_at:int;value:str;receipt_hash:str
 def __post_init__(self):
  if not self.event_at<=self.published_at<=self.received_at:raise ValueError('Clock order')
  if len(self.receipt_hash)!=64 or any(c not in '0123456789abcdefABCDEF' for c in self.receipt_hash):raise ValueError('Receipt identity required')
  if not D(self.value).is_finite():raise ValueError('Finite value required')

def asof(rows,instrument,decision):
 eligible=[r for r in rows if r.instrument==instrument and r.event_at<=decision and max(r.published_at,r.received_at)<=decision]
 if not eligible:return None
 clocks={}
 for row in eligible:
  key=(row.event_at,row.published_at,row.received_at)
  clocks.setdefault(key,set()).add((row.value,row.receipt_hash))
 if any(len(values)>1 for values in clocks.values()):raise ValueError('Ambiguous same-clock versions require reconciliation')
 return max(eligible,key=lambda r:(r.event_at,r.published_at,r.received_at))

def convert(amount,source,target,fx,decision):
 if not D(amount).is_finite():raise ValueError('Finite monetary amount required')
 if source==target:return D(amount)
 if fx is None or fx.instrument.base_asset!=source or fx.instrument.quote_asset!=target or fx.instrument.payoff!='spot' or max(fx.published_at,fx.received_at)>decision:raise ValueError('Observed direct FX required')
 if D(fx.value)<=0:raise ValueError('Positive FX required')
 return D(amount)*D(fx.value)

def f01():
 b=Instrument('venueA','spot','BTC','USD','USD','N/A','BTC/USD','N/A','1','spot','BTC','USD/BTC')
 perp=replace(b,market='perpetual',payoff='linear',contract='BTC-PERP',quantity_unit='contract')
 token=replace(b,base_asset='USDC',chain='eip155:1',contract='0xsyntheticUSDC',price_unit='USD/USDC',quantity_unit='USDC')
 pairs=[('quote',b,replace(b,quote_asset='USDT',settlement_asset='USDT',price_unit='USDT/BTC',contract='BTC/USDT')),('payoff_settlement',perp,replace(perp,payoff='inverse',settlement_asset='BTC',multiplier='100',quantity_unit='USD_contract')),('chain',token,replace(token,chain='eip155:42161')),('venue',b,replace(b,venue='venueB'))]
 pair_results=[{'case':n,'distinct':a!=z,'left':dataclasses.asdict(a),'right':dataclasses.asdict(z)} for n,a,z in pairs]
 fields=[n.target.id for c in ast.parse((REPO/'.venv/Lib/site-packages/predictor_core/data/contracts.py').read_text(encoding='utf-8')).body if isinstance(c,ast.ClassDef) and c.name=='MarketDataPoint' for n in c.body if isinstance(n,ast.AnnAssign)]
 missing=[k for k in dataclasses.asdict(b) if k not in fields]
 old=Observation(b,10,11,11,'100','a'*64);new=Observation(b,10,12,14,'90','b'*64)
 temporal=[{'case':'published before event','rejected':reject(lambda:replace(old,published_at=9))},{'case':'receipt before publication','rejected':reject(lambda:replace(old,received_at=10))}]
 revision={'before_receipt':asof([old,new],b,13).value,'after_receipt':asof([old,new],b,14).value,'naive_latest_would_use':'90','old_bytes_unchanged':old.value=='100'}
 fx=Observation(replace(b,base_asset='USDT',quote_asset='USD',contract='USDT/USD',quantity_unit='USDT',price_unit='USD/USDT'),10,11,11,'0.97','c'*64)
 conversion={'missing_fx_rejected':reject(lambda:convert('100','USDT','USD',None,12)),'future_fx_rejected':reject(lambda:convert('100','USDT','USD',fx,10)),'usd':str(convert('100','USDT','USD',fx,12)),'exact_fraction':str(Q(100)*Q(97,100))}
 invalid=reject(lambda:replace(b,multiplier='0'))
 normal=replace(b,multiplier='1.0')==b
 passed=all(x['distinct'] for x in pair_results) and all(x['rejected'] for x in temporal) and revision['before_receipt']=='100' and revision['after_receipt']=='90' and conversion['missing_fx_rejected'] and conversion['future_fx_rejected'] and conversion['usd']=='97.00' and invalid and normal
 return {'status':'PASS_NARROW_ENGINEERING' if passed else 'REJECT_ADAPTER','passed':passed,'pairs':pair_results,'baseline_fields':fields,'missing_explicit_fields':missing,'baseline_limit':'Field absence demonstrates no explicit typed representation; symbol/source strings may encode some identity. No observed production collision or provider truth certified.','temporal':temporal,'revision':revision,'conversion':conversion,'invalid_multiplier_rejected':invalid,'equivalent_multiplier_canonicalized':normal,'scope':'spot, linear/inverse perpetual/future only; options deliberately unsupported until strike/right/exercise contract exists'}

def f02():
 p=pathlib.Path('C:/Cripto/operacao/relatorios/REVISAO_COMPLETA_20260909/remaining_six_20260910/aave_second_source')
 result=read(p/'result.json');baseline=read(ROOT/'BASELINE.json')
 files={str(p/n):sha(p/n) for n in ['protocol.json','started.json','result.json']}
 unchanged=all(baseline['inputs'].get(k)==v for k,v in files.items())
 raw=list((p/'raw').glob('*.json'))
 return {'status':'BLOCKED_ACCESS_UNCHANGED','scientific_result':'INCONCLUSIVE','prior_attempt':result,'receipt_count':len(raw),'access_change_evidence':False,'hashes_unchanged':unchanged,'new_calls':0,'quota_consumed':0,'claim':'No separate-source comparison or historical implementation mapping established','pass_preservation':unchanged}

def universe_asof(events,decision):
 known={}
 for r in events:
  if max(r['published'],r['received'])<=decision:
   if r['asset'] not in known or (r['published'],r['received'])>(known[r['asset']]['published'],known[r['asset']]['received']):known[r['asset']]=r
 return sorted(k for k,r in known.items() if r['start']<=decision and (r['end'] is None or decision<r['end']))

def f03():
 p=pathlib.Path('C:/Cripto/restaurado-20260908/sessoes/20260907-altcoins/work/altcoin-retro-data')
 a=read(p/'acquisition.json');samples=[];files={str(p/'acquisition.json'):sha(p/'acquisition.json')}
 required=read(ROOT/'PROTOCOL.json')['F03']['required_fields']
 for name in ['BTCUSDT','ETHUSDT','FTTUSDT','USDCUSDT']:
  f=p/'pairs'/(name+'.json.gz')
  if not f.exists():samples.append({'symbol':name,'status':'ABSENT','gate':'BLOCKED_DATA'});continue
  raw=f.read_bytes();x=json.loads(gzip.decompress(raw));columns=x['columns'];metadata=x['metadata']
  # No price, return, ranking, model or payoff inspected/output. Only schema/date/quality metadata.
  coverage={key:key in columns or key in metadata for key in required}
  samples.append({'symbol':name,'status':'PRESENT','columns':columns,'metadata_keys':list(metadata),'rows_declared':metadata['rows'],'first_open_ms':metadata['first_open_ms'],'last_open_ms':metadata['last_open_ms'],'collected_at':metadata['finalized_at_utc'],'missing_required_evidence':[k for k,v in coverage.items() if not v],'missing_internal_days':metadata['missing_internal_days'],'gate':'BLOCKED_PIT_EVIDENCE' if not all(coverage.values()) else 'REQUIRES_SEMANTIC_REVIEW'})
  files[str(f)]=hashlib.sha256(raw).hexdigest()
 identity_path=pathlib.Path('C:/Cripto/restaurado-20260908/sessoes/20260907-altcoins/work/altcoin-retro-package/docs/evidence/altcoin_payoff_20260907/identity_events.json')
 identity=read(identity_path);files[str(identity_path)]=sha(identity_path)
 events=[{'asset':s,'start':0,'end':None,'published':0,'received':0} for s in ['BTC','FTT','USDC']]+[{'asset':'NEW','start':10,'end':None,'published':12,'received':13},{'asset':'FTT','start':0,'end':20,'published':18,'received':18}]
 expected={9:['BTC','FTT','USDC'],12:['BTC','FTT','USDC'],15:['BTC','FTT','NEW','USDC'],21:['BTC','NEW','USDC']}
 controls=[]
 for t,oracle in expected.items():
  observed=universe_asof(events,t);naive=universe_asof(events,21)
  controls.append({'decision':t,'expected':oracle,'asof':observed,'naive_current_survivors':naive,'asof_pass':observed==oracle,'naive_wrong':naive!=oracle})
 pairs=a['pairs']
 return {'status':'BLOCKED_DATA_FOR_ECONOMIC_TEST','synthetic_gate_passed':all(x['asof_pass'] for x in controls),'negative_control_detected':sum(x['naive_wrong'] for x in controls),'membership_controls':controls,'panel_declared_rows':a['total_rows'],'pair_count':len(pairs),'missing_days_metadata_sum':sum(x['missing_internal_days'] for x in pairs),'pairs_with_missing_days':sum(x['missing_internal_days']>0 for x in pairs),'samples':samples,'identity_events':{'count':len(identity['events']),'scope':identity['scope'],'historical_feature_use':identity['historical_feature_use'],'source_access_date':identity['source_access_date']},'input_hashes':files,'pit_fraction':'NOT_ESTIMABLE from acquired schema; missing explicit evidence is not proof no public historical information existed','new_ranking_or_returns_calculated':False,'existing_frozen_selection_changed':False,'reason':'Selected sample schemas lack row-level historical publication/receipt and dated eligibility; 13 posthoc identity events are explicitly not a complete historical universe. Full new-family hedge/cost contract and unused evaluation period also absent.'}

class Ledger:
 def __init__(self,spot_cash,future_cash):self.spot=D(spot_cash);self.future=D(future_cash);self.base=D(0);self.short=D(0);self.margin=D(0);self.events=[]
 def record(self,name):
  assert self.spot>=0 and self.future-self.margin>=0
  self.events.append({'event':name,'spot_cash':str(self.spot),'future_cash':str(self.future),'future_locked_margin':str(self.margin),'future_free_cash':str(self.future-self.margin),'spot_btc':str(self.base),'future_short_btc':str(self.short)})
 def buy_spot(self,q,p,fee):self.spot-=q*p*(1+fee);self.base+=q;self.record('spot buy')
 def short_future(self,q,p,fee):
  margin=q*p*D('.2');cost=q*p*fee
  if self.future<margin+cost:raise ValueError('Insufficient future-venue cash; no cross-venue transfer')
  self.future-=cost;self.margin=margin;self.short=q;self.record('future partial fill')
 def sell_spot(self,q,p,fee):
  if q>self.base:raise ValueError('Cannot sell more spot than held')
  self.spot+=q*p*(1-fee);self.base-=q;self.record('spot sell')
 def close_future(self,p,entry,fee):self.future+=self.short*(entry-p)-self.short*p*fee;self.short=D(0);self.margin=D(0);self.record('future close')

def f04():
 cases=[]
 for fill in ['0','0.5','1']:
  for delay,unwind in [(0,'100'),(1,'99'),(10,'95')]:
   q=D(fill);u=D(unwind);fee=D('.001');l=Ledger('110','50');l.buy_spot(D(1),D(100),fee);l.short_future(q,D(101),fee)
   orphan=D(1)-q
   locked={'spot_inventory_cost':'100','future_margin':str(l.margin),'orphan_btc':str(orphan),'orphan_capital_seconds':str(orphan*100*delay),'matched_spot_capital_seconds':str(q*100*86400),'future_margin_seconds':str(l.margin*86400)}
   l.sell_spot(orphan,u,fee);l.sell_spot(q,D(100),fee);l.close_future(D(100),D(101),fee)
   pnl=l.spot+l.future-D(160)
   fq=Q(fill);fu=Q(unwind);ff=Q(1,1000)
   reference=-Q(100)*(1+ff)+(1-fq)*fu*(1-ff)+fq*100*(1-ff)+fq*(101-100)-fq*(101+100)*ff
   fees=D('0.1')+orphan*u*fee+q*100*fee+q*201*fee
   gross=orphan*(u-100)+q
   expected=D(reference.numerator)/D(reference.denominator)
   cases.append({'fill_fraction':fill,'delay_seconds':delay,'orphan_unwind_price':unwind,'net_pnl_usd':str(pnl),'closed_form_fraction':str(reference),'error':str(abs(pnl-expected)),'gross_pnl_usd':str(gross),'fees_usd':str(fees),'economic_sign':'POSITIVE' if pnl>0 else 'NONPOSITIVE','net_on_total_capital':str(pnl/160),'additional_all_in_cost_break_even_usd':str(max(D(0),pnl)),'capital':locked,'ledger':l.events,'all_positions_closed':l.base==0 and l.short==0,'pass':abs(pnl-expected)<=D('1e-10') and abs(gross-fees-pnl)<=D('1e-10')})
 def invalid_margin():
  l=Ledger('160','0');l.buy_spot(D(1),D(100),D('.001'));l.short_future(D(1),D(101),D('.001'))
 margin_reject=reject(invalid_margin)
 orphan_reject=reject(lambda:Ledger('110','50').sell_spot(D(1),D(100),D('.001')))
 return {'status':'PASS_ACCOUNTING_ROBUSTNESS_NOT_DEMONSTRATED','passed':all(x['pass'] and x['all_positions_closed'] for x in cases) and margin_reject and orphan_reject,'cases':cases,'insufficient_local_margin_rejected':margin_reject,'unbacked_spot_sale_rejected':orphan_reject,'scenario_net_range':[str(min(D(x['net_pnl_usd']) for x in cases)),str(max(D(x['net_pnl_usd']) for x in cases))],'positive_scenarios':sum(D(x['net_pnl_usd'])>0 for x in cases),'not_empirical_probability':'Scenarios equiprobable only as enumeration; count is not an estimated probability. Delay-price map imposed, not fitted.','not_modeled':['actual queue/fill probabilities','funding and interest','intraperiod futures margin calls/mark-to-market','venue default/transfers','personal fees/taxes/FX','market impact and liquidity of forced unwind']}

def f05():
 n=160;rho=.6;rep=400;bs=299;block=8;rng=np.random.default_rng(2026091105)
 x=np.empty((rep,n));x[:,0]=rng.normal(size=rep)
 for t in range(1,n):x[:,t]=rho*x[:,t-1]+math.sqrt(1-rho*rho)*rng.normal(size=rep)
 analytic=(n+2*sum((n-k)*rho**k for k in range(1,n)))/n**2
 covariance=rho**np.abs(np.subtract.outer(np.arange(n),np.arange(n)))
 oracle=float(covariance.sum()/n**2);z=float(norm.ppf(.975));mean=x.mean(1)
 naive_half=z*x.std(1,ddof=1)/math.sqrt(n);exact_half=z*math.sqrt(analytic)
 cover={'iid_normal':int(np.sum(np.abs(mean)<=naive_half)),'known_covariance':int(np.sum(np.abs(mean)<=exact_half)),'circular_block8':0};width=[]
 for row in x:
  starts=rng.integers(0,n,size=(bs,n//block));indices=(starts[:,:,None]+np.arange(block))%n
  means=row[indices].reshape(bs,n).mean(1);lo,hi=np.quantile(means,[.025,.975]);cover['circular_block8']+=int(lo<=0<=hi);width.append(float(hi-lo))
 rows=[]
 for name,count in cover.items():
  rate=count/rep;rows.append({'method':name,'covered':count,'repetitions':rep,'coverage':rate,'mc_standard_error':math.sqrt(rate*(1-rate)/rep),'mean_interval_width':float(2*naive_half.mean()) if name=='iid_normal' else 2*exact_half if name=='known_covariance' else float(np.mean(width)),'registered_coverage_threshold_pass':rate>=.90})
 magnitudes=np.random.default_rng(2026091106).normal(size=(8,4));signs=np.array(list(itertools.product([-1,1],repeat=8)))
 stats=signs@magnitudes/8;maxstats=stats.max(1);selected=np.argmax(stats,axis=1)
 raw=[];adj=[]
 for i in range(256):
  threshold=stats[i,selected[i]];raw.append(float(np.mean(stats[:,selected[i]]>=threshold-1e-12)));adj.append(float(np.mean(maxstats>=threshold-1e-12)))
 # Independently enumerate scalar means for each sign vector, no matrix multiplication.
 scalar=np.array([[sum(int(s[k])*float(magnitudes[k,j]) for k in range(8))/8 for j in range(4)] for s in signs])
 maxerror=float(np.max(np.abs(scalar-stats)))
 raw_reject=sum(p<=.05 for p in raw);adj_reject=sum(p<=.05 for p in adj)
 label_start=list(range(30));label_end=[i+1 for i in range(30)];available=label_end.copy();label_end[5]=25;available[5]=25;available[3]=22
 boundaries=[]
 for cutoff in [15,20,25]:
  train=[i for i in range(cutoff-2)];kept=[i for i in train if label_end[i]<cutoff and available[i]<cutoff]
  expected=[i for i in train if max(label_end[i],available[i])<cutoff]
  boundaries.append({'cutoff':cutoff,'rowgap_train_count':len(train),'interval_and_availability_kept':kept,'forbidden_before':[i for i in train if i not in kept],'forbidden_after':sum(max(label_end[i],available[i])>=cutoff for i in kept),'oracle_pass':kept==expected})
 passed=abs(analytic-oracle)<1e-10 and .90<=cover['known_covariance']/rep<=.99 and adj_reject/256<=.05 and maxerror<1e-10 and all(r['oracle_pass'] and r['forbidden_after']==0 for r in boundaries)
 return {'status':'PASS_REFERENCE_TESTS_MARKET_INFERENCE_BLOCKED' if passed else 'REFERENCE_TEST_FAILURE','passed':passed,'analytic_mean_variance':analytic,'matrix_mean_variance':oracle,'effective_n_known_ar1':1/analytic,'iid_n':n,'intervals':rows,'multiplicity':{'patterns':256,'candidate_strategies':4,'unadjusted_selected_rejections':raw_reject,'unadjusted_family_error':raw_reject/256,'maxT_rejections':adj_reject,'maxT_family_error':adj_reject/256,'scalar_reference_error':maxerror,'assumption':'joint block-sign symmetry under complete null and fixed complete candidate family. Does not prove strong control under arbitrary partial null or market dependence.','magnitudes':magnitudes.tolist()},'label_boundaries':boundaries,'market_economic_ci_computed':False,'limits':'AR1 Gaussian stationarity and known covariance are synthetic oracle assumptions. Fixed block8 not retuned; undercoverage reported as result. No real complete trial ledger or PIT labels supplied for new family.'}

def main():
 protocol=read(ROOT/'PROTOCOL.json');baseline=read(ROOT/'BASELINE.json')
 assert sha(ROOT/'BASELINE.json')==protocol['baseline_sha256']
 assert all(sha(pathlib.Path(p))==h for p,h in baseline['inputs'].items())
 started=datetime.datetime.now(datetime.UTC).isoformat();t=time.perf_counter()
 results={}
 for name,fn in [('F01',f01),('F02',f02),('F03',f03),('F04',f04),('F05',f05)]:
  results[name]=fn();print(name,results[name]['status'],flush=True)
 out={'initiative':'20260911T0233','phase':2,'started_at':started,'completed_at':datetime.datetime.now(datetime.UTC).isoformat(),'elapsed_seconds':time.perf_counter()-t,'protocol_sha256':sha(ROOT/'PROTOCOL.json'),'implementation_sha256':sha(pathlib.Path(__file__)),'seed_and_design':protocol,'results':results,'new_network_calls':0,'orders':0}
 with (ROOT/'RESULTS.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
 assert results['F01']['passed'] and results['F04']['passed'] and results['F05']['passed'] and results['F03']['synthetic_gate_passed'] and results['F02']['pass_preservation']
 print('All engineering controls passed; economic blocks are retained.')
if __name__=='__main__':main()
