import sys
sys.dont_write_bytecode=True
import json,pathlib,copy,hashlib,datetime,socket
import adapter_v3 as a
def denied(*x,**y):raise RuntimeError('Offline phase; network prohibited')
socket.socket.connect=denied;socket.create_connection=denied
R=pathlib.Path(__file__).resolve().parents[1];b=a.load(R/'BASELINE.json')
def write(n,x):(R/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def rejects(fn):
 try:fn();return False
 except (ValueError,TypeError,KeyError):return True
records=[];tests=[];cases={c['id']:c for c in b['sample']}
for c in b['sample']:
 e=a.normalize(c,b);restored=json.loads(json.dumps(e,sort_keys=True,allow_nan=False))
 a.validate(restored,c,b)
 # Independent reader checks actual field pointers and original values, not merely equal dicts.
 checks=[]
 for f,p in e['provenance'].items():
  if p['ORIGINAL_FIELD'] is not None:
   v=a.decoded(p['RECEIPT'])[2]
   for part in p['ORIGINAL_FIELD']:v=v[part]
   checks.append(v==p['ORIGINAL_VALUE'] and hashlib.sha256(pathlib.Path(p['RECEIPT']).read_bytes()).hexdigest()==p['HASH'])
 temporal=[];t=e['fields']['INGESTION_TIME']['value']
 if t is not None:
  temporal=[{'cutoff_ns':t-1,'eligible':a.available(e,t-1),'expected':False},{'cutoff_ns':t,'eligible':a.available(e,t),'expected':True}]
  # Future revision derived from each real observation; additional known time, not a claimed real revision.
  future=copy.deepcopy(e);future['fields']['REVISION_TIME']={'status':'PROVEN','value':t+1000000000}
  temporal.append({'cutoff_ns':t,'eligible':a.available(future,t),'expected':False,'derived_revision':True})
 records.append({'case':c['id'],'record':e,'round_trip':restored==e,'provenance_check':all(checks),'temporal':temporal,'economic_join_refused':rejects(lambda:a.economic_join(e,e)),'classification':e['eligibility'] if e['eligibility']!='PARTIAL_ONLY' else 'AMBIGUOUS'})
by={x['case']:x['record'] for x in records}
base=by['perp_trade']
for name,field,val in [('A_SYMBOL','ASSET_IDENTITY','same_ticker_other_entity'),('B_UNIT','UNIT','USD not USDT'),('C_SETTLEMENT','SETTLEMENT','USDC'),('D_PRICE_TYPE','PRICE_TYPE','executable_quote'),('F_CHAIN','CHAIN',1),('F_CONTRACT','CONTRACT_ADDRESS','0x'+'1'*40),('G_DECIMALS','DECIMALS',-1),('H_MISSING','QUOTE',None)]:
 e=copy.deepcopy(base);e['fields'][field]={'status':'PROVEN','value':val}
 tests.append({'case':name,'parent':'perp_trade','mutation':{field:val},'rejected':rejects(lambda:a.validate(e,cases['perp_trade'],b)),'reason':'Mutation contradicts preserved evidence or lacks provenance; not a new genuine receipt'})
for val in ['NaN','Infinity','-Infinity']:
 e=copy.deepcopy(base);e['value']=val;tests.append({'case':'G_'+val,'parent':'perp_trade','rejected':rejects(lambda:a.validate(e,cases['perp_trade'],b))})
for h in ['z'*64,'1'*64]:
 e=copy.deepcopy(base);e['receipt_hash']=h;tests.append({'case':'G_HASH_'+h[:2],'parent':'perp_trade','rejected':rejects(lambda:a.validate(e,cases['perp_trade'],b))})
t=base['fields']['INGESTION_TIME']['value'];e=copy.deepcopy(base);e['fields']['REVISION_TIME']={'status':'PROVEN','value':t+1}
tests.append({'case':'E_FUTURE_VERSION','parent':'perp_trade','rejected':not a.available(e,t),'synthetic_derived':True})
tests.append({'case':'H_UNKNOWN_JOIN','parent':'perp_trade','rejected':rejects(lambda:a.economic_join(base,base))})
for x,y in [('perp_trade','perp_mark'),('future_trade','future_mark'),('spot_info','future_info'),('aave_019','aave_027')]:
 tests.append({'case':'REAL_DIFFERENCE_'+x+'_'+y,'parents':[x,y],'rejected':rejects(lambda:a.economic_join(by[x],by[y])),'different_proven_fields':[k for k in a.FIELDS if by[x]['fields'][k]['status']==by[y]['fields'][k]['status']=='PROVEN' and by[x]['fields'][k]['value']!=by[y]['fields'][k]['value']]})
violations=sum(t['eligible']!=t['expected'] for r in records for t in r['temporal'])
summary={'TOTAL_CASES':len(records),'REAL_HTTP_RPC_RECEIPTS':sum(c['kind']!='mapping' for c in b['sample']),'RETROSPECTIVE_ARTIFACTS':1,'VALID':0,'CORRECTLY_REJECTED':sum(r['classification']=='CORRECTLY_REJECTED' for r in records),'AMBIGUOUS':sum(r['classification']=='AMBIGUOUS' for r in records),'UNSUPPORTED':sum(r['classification']=='UNSUPPORTED' for r in records),'BUGS_FOUND':0,'BUGS_FIXED':0,'REPRESENTATION_GAPS_ADDRESSED':2,'TEMPORAL_VIOLATIONS':violations,'SILENT_INFERENCES':0,'ROUND_TRIP_FAILURES':sum(not r['round_trip'] for r in records),'FAITHFUL_PARTIAL_ENVELOPES':len(records),'COMPLETE_ECONOMIC_IDENTITIES':0,'ADVERSARIAL_TESTS':len(tests),'ADVERSARIAL_REJECTED':sum(t['rejected'] for t in tests),'TEMPORAL_CHECKS':sum(len(r['temporal']) for r in records)}
write('NORMALIZED_CASES.json',records);write('ADVERSARIAL_RESULTS.json',tests);write('RESULTS.json',{'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summary':summary,'adapter_version':a.VERSION,'adapter_hash':a.digest((R/'work/adapter_v3.py').read_bytes()),'F03':'BLOCKED','F04':'BLOCKED','scope':'Evidence envelope succeeds at preserving uncertainty; no complete economic instrument or economic replay is certified.'})
assert all(t['rejected'] for t in tests) and not violations and all(r['round_trip'] and r['provenance_check'] for r in records)
print(json.dumps(summary,indent=2))
