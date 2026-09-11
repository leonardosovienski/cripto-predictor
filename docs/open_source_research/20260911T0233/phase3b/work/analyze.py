import pathlib,json,gzip,hashlib,datetime,statistics,decimal,math,functools,socket,sys
P=pathlib.Path;R=P(__file__).resolve().parents[1];BASE=json.loads((R/'BASELINE.json').read_bytes());OLD=R.parent/'phase3'
def no_network(*a,**k):raise RuntimeError('Phase 3B offline only')
socket.socket.connect=no_network;socket.create_connection=no_network
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def read(p):return json.loads(P(p).read_bytes())
def decode(p):return json.loads(gzip.decompress(P(p).read_bytes()) if str(p).endswith('.gz') else P(p).read_bytes())
def utc(ns):return datetime.datetime.fromtimestamp(ns//1000000000,datetime.timezone.utc).isoformat()
def ns(iso):
 d=datetime.datetime.fromisoformat(iso.replace('Z','+00:00'));delta=d-datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)
 return (delta.days*86400+delta.seconds)*10**9+delta.microseconds*1000
def write(n,x):(R/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def ref(p,pointer,clock=None):return {'path':str(p),'sha256':sha(p),'pointer':pointer,'evidence_clock_ns':clock}
D=P('C:/Cripto/restaurado-20260908/sessoes/20260907-pesquisa/work/btc-execution-diagnostic-v1');PROBE=D.parent/'basis-capability-probe'
sources=read(D/'diagnostic.json')['sources'];sm={x['name']:x for x in sources}
body_checks=[]
for m in sources:
 p=D/'raw'/(m['name']+'.bin.gz');body=gzip.decompress(p.read_bytes());passed=hashlib.sha256(body).hexdigest()==m['sha256']
 body_checks.append({'case':m['name'],'passed':passed,'recorded_sha256':m['sha256']});assert passed
for name in ['docs','info']:
 m=read(PROBE/(name+'.meta.json'));passed=sha(PROBE/(name+'.raw'))==m['sha256'];body_checks.append({'case':'probe_'+name,'passed':passed,'recorded_sha256':m['sha256']});assert passed
write('BODY_HASH_CHECKS.json',body_checks)
fields=read(R/'PROTOCOL.json')['contract_fields'];contracts={}
for id,symbol,name in [('BTC_SPOT','BTCUSDT','spot_info'),('BTC_PERPETUAL','BTCUSDT','future_info'),('BTC_DATED','BTCUSDT_261225','future_info')]:
 p=D/'raw'/(name+'.bin.gz');d=decode(p);i=next(i for i,x in enumerate(d['symbols']) if x['symbol']==symbol);row=d['symbols'][i];clock=sm[name]['received_ns'];q=['symbols',i]
 cells={f:{'value':None,'status':'UNKNOWN','epistemic_label':'NOT_PROVEN','evidence':[],'evidence_clock':None,'retroactive':False,'why':'No explicit admissible economic specification in bounded saved bundle'} for f in fields}
 def proven(k,v,key,note=''):
  cells[k]={'value':v,'status':'PROVEN','epistemic_label':'CURRENT_ONLY','evidence':[ref(p,q+[key],clock)],'evidence_clock':clock,'retroactive':False,'why':note or 'Literal field in received metadata; effective historical period not established'}
 cells['venue']={'value':sm[name]['url'].split('/')[2],'status':'PROVEN','epistemic_label':'CURRENT_ONLY','evidence':[ref(D/'diagnostic.json',['sources',sources.index(sm[name]),'url'],clock)],'evidence_clock':clock,'retroactive':False,'why':'Host namespace; not a legal-counterparty or settlement certification'}
 for k,key in [('base_asset','baseAsset'),('quote_asset','quoteAsset'),('margin_asset','marginAsset')]:
  if key in row:proven(k,row[key],key)
 if 'contractType' in row:proven('market_type',row['contractType'],'contractType')
 else:proven('market_type',{'isSpotTradingAllowed':row['isSpotTradingAllowed']},'isSpotTradingAllowed','Spot capability flag in spot endpoint; not proof of a fill')
 if id=='BTC_DATED':proven('expiry',{'deliveryDate_raw':row['deliveryDate'],'utc_under_preserved_ms_decoder':utc(row['deliveryDate']*10**6)},'deliveryDate','Raw date explicitly declared; UTC rendering uses the preserved project millisecond decoder. Does not back-prove older contracts.')
 if id=='BTC_SPOT':
  cells['funding_semantics']={'value':None,'status':'N/A','epistemic_label':'STRUCTURAL_SCOPE','evidence':[],'evidence_clock':None,'retroactive':False,'why':'This row studies the spot metadata contract, not a funding event or margin loan. Any financing would require a separate contract.'}
 cells['price_type']['why']='Instrument has multiple observations; type belongs to each receipt, not a single interchangeable instrument price. See OBSERVATION_SEMANTICS.json.'
 cells['contract_version']['why']='Only body content hash preserved; no effective economic specification version/change history.'
 cells['valid_from']['why']='onboardDate, where present, is a claim in later metadata, not publication/knowledge time or proof that all terms were effective since then.'
 cells['valid_until']['why']='No dated change log or end of validity for the full economic terms.'
 contracts[id]={'symbol':symbol,'fields':cells,'observed_metadata_hash':hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest(),'metadata_receipt_time_ns':clock,'raw_onboardDate':row.get('onboardDate'),'raw_deliveryDate':row.get('deliveryDate'),'raw_pricePrecision':row.get('pricePrecision'),'raw_quantityPrecision':row.get('quantityPrecision'),'complete_for_replay':False,'notional_formula':'UNSUPPORTED: quantity/price units and economic contract not fully proven','pnl_formula':'UNSUPPORTED','margin_formula':'UNSUPPORTED','settlement_formula':'UNSUPPORTED'}
write('INSTRUMENT_CONTRACTS.json',contracts)
clock_rows=[]
def clock_case(id,p,meta,kind,meta_path,meta_ptr=[]):
 data=decode(p);cf={k:{'status':'UNKNOWN','value':None} for k in read(R/'PROTOCOL.json')['clock_fields']}
 def put(k,v,origin,unit,domain,meaning,status='PROVEN'):
  cf[k]={'status':status,'value':v,'origin':origin,'unit':unit,'clock_domain':domain,'meaning':meaning}
 receipt=meta.get('received_ns');request=meta.get('request_start_ns')
 if receipt is None:
  for key in ['retrieved_at_utc','known_at','retrieved_utc']:
   if key in meta:receipt=ns(meta[key]);break
 if request is None and meta.get('request_started_utc'):request=ns(meta['request_started_utc'])
 if receipt is not None:put('LOCAL_RECEIPT_TIME',receipt,ref(meta_path,meta_ptr,receipt),'ns UTC','local_wall_clock','After client.send returned for diagnostic; retrieval/known metadata elsewhere; separate ingestion write time not logged')
 if request is not None:put('LOCAL_REQUEST_TIME',request,ref(meta_path,meta_ptr,receipt),'ns UTC','local_wall_clock','Before HTTP send for diagnostic')
 candidates={}
 if kind=='depth' and isinstance(data,dict):
  candidates={k:data[k] for k in ['E','T','lastUpdateId'] if k in data}
  if 'T' in data:put('SOURCE_EVENT_TIME',data['T'],ref(p,['T'],receipt),'candidate ms; decoder convention, archived depth unit specification absent','remote_unreconciled','Literal T field; economic event meaning and cross-clock mapping NOT_PROVEN',status='RAW_PROVEN_SEMANTICS_NOT_PROVEN')
  if 'E' in data:candidates['E_role']='Named E preserved; no automatic publication/response-time assignment'
 elif kind=='exchangeInfo':candidates={'serverTime':data.get('serverTime'),'role':'Body timestamp; cannot equate with actual response production time'}
 elif kind=='klines':
  put('SOURCE_EVENT_TIME',data[0][0],ref(p,[0,0],receipt),'ms under saved REST decoder','source_dataset','Open-time field; source publication time absent',status='RAW_PROVEN_SEMANTICS_PARTIAL');candidates={'close_time':data[0][6],'rows':len(data)}
 elif kind=='funding':
  put('SOURCE_EVENT_TIME',data[0]['fundingTime'],ref(p,[0,'fundingTime'],receipt),'ms under saved decoder','source_dataset','fundingTime named field; not actual account settlement',status='RAW_PROVEN_SEMANTICS_PARTIAL')
 if meta.get('server_date'):candidates['http_server_date']={'raw':meta['server_date'],'resolution':'1 second text','role':'HTTP Date header; not first publication or calibrated response time'}
 return {'id':id,'receipt':ref(p,[],receipt),'kind':kind,'clocks':cf,'preserved_candidates':candidates,'state_rules':{'OBSERVED':'true iff local receipt <= cutoff in same local time domain','EVENT_OCCURRED':'timestamp is attached; occurrence by local cutoff NOT_PROVEN when domain/meaning unresolved','ECONOMICALLY_ELIGIBLE':'false until complete scoped economic identity, specification validity and temporal bridge are proven'},'clock_mapping':'NOT_PROVEN'}
for i,m in enumerate(sources):clock_rows.append(clock_case(m['name'],D/'raw'/(m['name']+'.bin.gz'),m,'exchangeInfo' if m['name'].endswith('info') else 'depth',D/'diagnostic.json',['sources',i]))
p3=read(OLD/'BASELINE.json')
for c in p3['sample']:
 if c['id'] in ['spot_BTCUSDT','perp_trade','perp_mark','future_trade','future_mark','funding']:clock_rows.append(clock_case(c['id'],P(c['path']),read(c['metadata']),c['kind'],P(c['metadata'])))
clock_rows.append(clock_case('probe_info',PROBE/'info.raw',read(PROBE/'info.meta.json'),'exchangeInfo',PROBE/'info.meta.json'))
docmeta=read(PROBE/'docs.meta.json');docclock=ns(docmeta['retrieved_utc'])
docclocks={k:{'status':'UNKNOWN','value':None} for k in read(R/'PROTOCOL.json')['clock_fields']}
docclocks['LOCAL_RECEIPT_TIME']={'status':'PROVEN','value':docclock,'origin':ref(PROBE/'docs.meta.json',['retrieved_utc'],docclock),'unit':'ns UTC converted from ISO','clock_domain':'local_wall_clock','meaning':'retrieved_utc metadata; original publication not established'}
clock_rows.append({'id':'probe_docs','receipt':ref(PROBE/'docs.raw',[],docclock),'kind':'documentation','clocks':docclocks,'preserved_candidates':{},'clock_mapping':'NOT_PROVEN','state_rules':{'OBSERVED':'retrieved by local collection timestamp','EVENT_OCCURRED':'documentation original publication UNKNOWN','ECONOMICALLY_ELIGIBLE':'not a complete historical instrument specification'}})
write('CLOCK_MATRIX.json',clock_rows)
future=[]
for m in sources:
 if m['name'].startswith('future_') and m['name']!='future_info':
  p=D/'raw'/(m['name']+'.bin.gz');x=decode(p);future.append({'id':m['name'],'request_ns':m['request_start_ns'],'receipt_ns':m['received_ns'],'T_raw':x['T'],'E_raw':x['E'],'lastUpdateId':x['lastUpdateId'],'T_minus_receipt_ms':str(decimal.Decimal(x['T']*10**6-m['received_ns'])/10**6),'round_trip_ms':str(decimal.Decimal(m['received_ns']-m['request_start_ns'])/10**6),'E_minus_T_raw':x['E']-x['T'],'physical_sha256':sha(p)})
deltas=[decimal.Decimal(x['T_minus_receipt_ms']) for x in future]
code=D.parent/'basis-delivery-stage/scripts/diagnose_btc_execution.py';freeze=P('C:/Cripto/pesquisa-20260909/docs/evidence/basis_research_20260908/implementation_freeze_v1.json')
assert sha(code)==read(freeze)['files']['scripts/diagnose_btc_execution.py']
probeinfo=read(PROBE/'info.meta.json');probebody=(PROBE/'info.raw').read_bytes();diagbody=gzip.decompress((D/'raw/future_info.bin.gz').read_bytes())
clock_findings={'status':'CAUSE_UNKNOWN','difference_unit_caveat':'410.3008 ms is exact conditional on T being epoch milliseconds. Local nanoseconds are proven by frozen source; archived depth documentation does not prove T/E event semantics or clock calibration.','book_pairs':12,'positive_remote_minus_local':sum(x>0 for x in deltas),'delta_ms_min':str(min(deltas)),'delta_ms_max':str(max(deltas)),'delta_ms_median':str(statistics.median(deltas)),'samples':future,'monotonicity':{k:all(future[i][k]<future[i+1][k] for i in range(11)) for k in ['request_ns','receipt_ns','T_raw','E_raw','lastUpdateId']},'local_receipt_after_request':all(x['receipt_ns']>=x['request_ns'] for x in future),'local_encoded_resolution_gcd_ns':functools.reduce(math.gcd,[v for x in future for v in [x['request_ns'],x['receipt_ns']]]),'resolution_limit':'Observed integer granularity is not clock accuracy or proof of synchronization; time.time_ns is a wall clock and can jump. No contemporaneous monotonic/NTP/PTP logs.','collector':{'source':ref(code,{'lines':[134,135,136,137,138,139,142,145,146]}),'freeze':ref(freeze,['files','scripts/diagnose_btc_execution.py']),'hash_matches_freeze':True,'monotonic_clock_logged':False,'clock_offset_logged':False,'response_headers_logged':False,'disk_ingestion_or_normalization_time_logged':False},'metadata_body_repeated':{'identical':probebody==diagbody,'first_receipt':probeinfo['retrieved_utc'],'second_receipt_ns':sm['future_info']['received_ns'],'serverTime_raw':json.loads(diagbody)['serverTime'],'meaning':'Body timestamp is not fresh response-time evidence. Static metadata/cache/snapshot possible; causal mechanism not proven.'}}
write('CLOCK_INVESTIGATION.json',clock_findings)
sem=[]
for c in p3['sample']:
 if c['id'] not in ['spot_BTCUSDT','perp_trade','perp_mark','future_trade','future_mark','funding','spot_00','future_00']:continue
 typ='fundingRate_observation' if c['kind']=='funding' else 'displayed_ask_not_fill' if c['kind']=='depth' else 'mark_candle_close' if 'mark' in c['id'] else 'trade_candle_close'
 sem.append({'case':c['id'],'type':typ,'evidence':ref(P(c['path']),[0,'fundingRate'] if c['kind']=='funding' else ['asks',0,0] if c['kind']=='depth' else [0,4]),'source_locator':c['metadata'],'supports_executable_fill':False,'index_price':'ABSENT from this bounded sample','historical_specification':'CURRENT_ONLY for received metadata; RETROACTIVE_ASSUMPTION if imposed on earlier candles','unit_contract':'NOT_PROVEN for full economic replay'})
write('OBSERVATION_SEMANTICS.json',sem)
fc=next(c for c in p3['sample'] if c['id']=='funding');fd=decode(fc['path']);fm=read(fc['metadata']);times=[x['fundingTime'] for x in fd]
write('FUNDING_CONTRACT.json',{'status':'FUNDING_REPLAY_NOT_PROVEN','receipt':ref(P(fc['path']),[],ns(fm['known_at'])),'RATE':{'status':'PROVEN','value':fd[0]['fundingRate'],'pointer':[0,'fundingRate'],'meaning':'Named numeric rate observation, not account cash'},'REFERENCE_TIMESTAMP':{'status':'PROVEN_RAW','value':fd[0]['fundingTime'],'unit':'ms under preserved decoder'},'predicted':'NOT_PROVEN','published':'retrieved from fundingRate endpoint by local receipt; original publication UNKNOWN','realized_settled_cash':'NOT_PROVEN','INTERVAL_EVENT':{'observed_rows':len(times),'observed_deltas_raw':sorted(set(b-a for a,b in zip(times,times[1:]))),'contractual_interval':'NOT_PROVEN; observed spacing is not a guaranteed schedule'},'POSITION_BASIS':'NOT_PROVEN','PAYMENT_DIRECTION':'NOT_PROVEN','PAYMENT_CURRENCY':'NOT_PROVEN','ELIGIBILITY_TIME':'NOT_PROVEN','rateType_literal':fd[0].get('rateType'),'markPrice_literal':fd[0].get('markPrice'),'no_rate_to_cash_conversion':True})
print(json.dumps({'contracts':{k:[f for f,x in v['fields'].items() if x['status']=='PROVEN'] for k,v in contracts.items()},'clock_receipts':len(clock_rows),'positive_T_deltas':clock_findings['positive_remote_minus_local'],'delta_range':[str(min(deltas)),str(max(deltas))],'same_info_body':probebody==diagbody},indent=2))
