"""Offline evidence envelope. No economic metadata defaults; no production integration."""
import json,gzip,pathlib,hashlib,datetime,decimal,urllib.parse,copy,re
VERSION='F01-real v3'
FIELDS='ASSET_IDENTITY CHAIN CONTRACT_ADDRESS VENUE MARKET_TYPE BASE QUOTE SETTLEMENT MARGIN_ASSET LINEAR_INVERSE CONTRACT_MULTIPLIER EXPIRY PRICE_TYPE UNIT CURRENCY DECIMALS SOURCE SOURCE_VERSION EVENT_TIME PUBLICATION_TIME INGESTION_TIME REVISION_TIME OBSERVED_VERSION'.split()
R=pathlib.Path(__file__).resolve().parents[1]
def digest(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(pathlib.Path(p).read_bytes())
def stamp(s):
 d=datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('Timezone required')
 epoch=datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc);dt=d-epoch
 return (dt.days*86400+dt.seconds)*1000000000+dt.microseconds*1000
def pointer(data,path):
 for key in path:data=data[key]
 return data
def decoded(p):
 raw=pathlib.Path(p).read_bytes();body=gzip.decompress(raw) if str(p).endswith('.gz') else raw
 return raw,body,json.loads(body)
def normalize(case,baseline):
 p=case['path'];raw,body,data=decoded(p)
 if digest(raw)!=baseline['read_only_hashes'][p]:raise ValueError('Physical receipt hash mismatch')
 fields={k:dict(status='UNKNOWN',value=None,reason='Not proven by the selected receipt; no implicit default') for k in FIELDS}
 e=dict(adapter=VERSION,case=case['id'],kind=case['kind'],fields=fields,receipt=p,receipt_hash=digest(raw),body_hash=digest(body),value=None,provenance={},eligibility='PARTIAL_ONLY',clock_notes='Receipt proves local possession by that instant, not first publication or trader availability; filesystem mtime is never evidence.')
 def setf(k,value,path=None,source=p,transform='identity',reason=None):
  original=pointer(decoded(source)[2],path) if path is not None else None
  e['fields'][k]=dict(status='PROVEN',value=value)
  e['provenance'][k]=dict(SOURCE=source,ORIGINAL_FIELD=path,ORIGINAL_VALUE=original,NORMALIZED_VALUE=value,TRANSFORMATION=transform,UNIT_TRANSFORMATION='none',RECEIPT=source,HASH=digest(pathlib.Path(source).read_bytes()),VERSION=digest(decoded(source)[1]),TIMESTAMP=None,reason=reason)
 def na(k,reason):fields[k]=dict(status='N/A',value=None,reason=reason)
 def value(v,path,transform='identity'):
  e['value']=str(v);setf('VALUE',str(v),path,transform=transform)
  # VALUE is part of provenance, not a 24th instrument field.
  fields.pop('VALUE')
 setf('OBSERVED_VERSION',digest(body),transform='sha256 of preserved decoded body',reason='Content version, not provider revision ID')
 meta=load(case['metadata']) if case.get('metadata') else {}
 mp=case.get('metadata');prefix=[]
 if case['kind'] in ['exchangeInfo','depth']:
  i=next(i for i,x in enumerate(meta['sources']) if x['name']==case['id']);prefix=['sources',i];meta=meta['sources'][i]
 url=meta.get('url',data.get('endpoint') if isinstance(data,dict) else None)
 if url:
  loc=['endpoint'] if not mp else prefix+['url'];src=mp or p
  setf('SOURCE',url,loc,src)
  setf('VENUE',urllib.parse.urlparse(url).netloc,loc,src,'URL hostname; source namespace, not legal counterparty')
  params=urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
  if 'symbol' in params:setf('ASSET_IDENTITY',params['symbol'][0],loc,src,'URL query symbol; venue symbol only, underlying identity NOT_PROVEN')
  # API path is evidenced, deployment/revision version is not inferred from v1/v3.
  e['api_path']=urllib.parse.urlparse(url).path
 for key in ['received_ns','retrieved_at_utc','known_at','received_at_utc']:
  if key in meta:
   n=meta[key] if key=='received_ns' else stamp(meta[key]);setf('INGESTION_TIME',n,prefix+[key],mp,'ns UTC; local receipt');break
 if 'sha256' in meta or 'raw_sha256' in meta:
  expected=meta.get('sha256',meta.get('raw_sha256'))
  if expected!=digest(body):raise ValueError('Recorded HTTP body hash mismatch')
  e['recorded_body_hash_verified']=True
 k=case['kind']
 if k=='klines':
  if not data:raise ValueError('Empty candle receipt')
  value(data[0][4],[0,4]);setf('EVENT_TIME',data[0][0]*1000000,[0,0],'{}'.format(p),'milliseconds to ns; candle open, not publication')
  setf('PRICE_TYPE','mark_candle_close' if 'markPriceKlines' in url else 'trade_candle_close',prefix+['url'],mp,'endpoint semantics and raw column 4; never executable')
  e['raw_event_fields']={'open':data[0][0],'close':data[0][6]};e['row_count']=len(data)
  e['semantic_note']='UNIT/CURRENCY/settlement unknown without dated instrument specification; no suffix parsing. Positional candle decoder uses preserved project schema; economic units unproved.'
 elif k=='funding':
  value(data[0]['fundingRate'],[0,'fundingRate']);setf('EVENT_TIME',data[0]['fundingTime']*1000000,[0,'fundingTime'],transform='milliseconds to ns')
  setf('PRICE_TYPE','fundingRate field; not account payment',[0,'fundingRate'],transform='named field semantics')
  setf('ASSET_IDENTITY',data[0]['symbol'],[0,'symbol'])
  e['additional_observation']={'markPrice':data[0].get('markPrice'),'type':'markPrice named field; no monetary conversion','pointer':[0,'markPrice']}
  e['semantic_note']='Rate interval, annualization, settlement and actual cash payment NOT_PROVEN. No fixed 8h assumption.'
 elif k=='exchangeInfo':
  i=next(i for i,x in enumerate(data['symbols']) if x['symbol']=='BTCUSDT');s=data['symbols'][i];q=['symbols',i]
  for a,z in [('ASSET_IDENTITY','symbol'),('BASE','baseAsset'),('QUOTE','quoteAsset'),('MARGIN_ASSET','marginAsset'),('MARKET_TYPE','contractType')]:
   if z in s:setf(a,s[z],q+[z])
  if s.get('isSpotTradingAllowed') is True:setf('MARKET_TYPE','SPOT_ALLOWED',q+['isSpotTradingAllowed'],transform='boolean capability, not proof of a particular execution')
  na('PRICE_TYPE','Instrument metadata record contains no observed price');na('UNIT','Metadata record is not a numeric market observation');na('CURRENCY','No monetary value observed')
  e['semantic_note']='baseAssetPrecision is exchange display/quantity precision, not on-chain token decimals. marginAsset is not settlement proof. deliveryDate sentinel not interpreted as actual expiry.'
  e['sampled_symbol_pointer']=q;e['declared_symbol_count']=len(data['symbols'])
 elif k=='depth':
  value(data['asks'][0][0],['asks',0,0]);setf('PRICE_TYPE','displayed_ask_not_fill',['asks'],transform='book side; no fill guarantee')
  if 'T' in data:setf('EVENT_TIME',data['T']*1000000,['T'],transform='milliseconds to ns; source transaction timestamp')
  e['semantic_note']='No executable-time or guaranteed quantity inference. No retroactive exchangeInfo join; metadata may be enriched separately with its own receipt clock.'
  e['raw_event_fields']={k:data[k] for k in ['E','T','lastUpdateId'] if k in data}
 elif k=='rpc':
  req=data['request'];res=data['response']['result'];setf('INGESTION_TIME',stamp(data['received_at']),['received_at'],transform='ISO UTC to ns')
  e['rpc_method']=req['method'];e['rpc_params']=req['params'];setf('SOURCE_VERSION',req['jsonrpc'],['request','jsonrpc'],transform='JSON-RPC envelope version only; contract implementation NOT_PROVEN')
  if req['method']=='eth_chainId':
   value(int(res,16),['response','result'],'hex to integer');setf('CHAIN',int(res,16),['response','result'],transform='hex to chain ID');setf('UNIT','chain identifier',['request','method'],transform='method semantics')
  elif req['method']=='eth_getBlockByNumber':
   value(int(res['number'],16),['response','result','number'],'hex to integer');setf('EVENT_TIME',int(res['timestamp'],16)*1000000000,['response','result','timestamp'],transform='hex seconds to ns; block time, not availability');setf('UNIT','block number',['request','method'],transform='method semantics');e['block_hash']=res['hash']
  elif req['method']=='web3_sha3':
   e['non_numeric_value']=res;e['decoded_signature']=bytes.fromhex(req['params'][0][2:]).decode();setf('UNIT','hash bytes',['request','method'],transform='method semantics')
  elif req['method']=='eth_call':
   setf('CONTRACT_ADDRESS',req['params'][0]['to'],['request','params',0,'to']);setf('ASSET_IDENTITY',req['params'][0]['to'],['request','params',0,'to'],transform='called contract only; not automatically underlying token')
   e['block_tag']=req['params'][1];e['call_data']=req['params'][0]['data'];e['non_numeric_value']=res
   if len(res)==66:value(int(res,16),['response','result'],'hex to integer; ABI economic role requires separate evidence')
   setf('UNIT','raw ABI bytes',['response','result'],transform='ABI encoding; not money, not inferred ray')
  for f in ['PRICE_TYPE','CURRENCY']:na(f,'RPC state/identifier is not an observed market price or monetary amount')
  e['semantic_note']='Endpoint chain receipt and selector receipt retained separately; no implicit cross-receipt join. ABI interpretation, historical proxy implementation and token decimals require explicit evidence links.'
 elif k=='empty':
  if data!=[]:raise ValueError('Expected preserved empty response')
  e['eligibility']='CORRECTLY_REJECTED';e['semantic_note']='No observations returned; absence is not zero price or delisting proof.'
 elif k=='mapping':
  e['eligibility']='UNSUPPORTED';e['semantic_note']='Retrospective enrichment artifact, not primary HTTP receipt; historical_feature_use=false; access date not precise publication.'
  e['mapping_scope']={a:data[a] for a in ['scope','source_access_date','historical_feature_use']};e['events']=data['events']
 # Provenance timestamps represent acquisition, never historical validity.
 for q in e['provenance'].values():q['TIMESTAMP']=fields['INGESTION_TIME']['value']
 return e
def validate(e,case,b):
 if not re.fullmatch('[0-9a-f]{64}',e.get('receipt_hash','')):raise ValueError('Invalid receipt hash')
 if e['value'] is not None and not decimal.Decimal(e['value']).is_finite():raise ValueError('Nonfinite')
 d=e['fields']['DECIMALS']
 if d['status']=='PROVEN' and (type(d['value']) is not int or not 0<=d['value']<=255):raise ValueError('Invalid decimals')
 if e!=normalize(case,b):raise ValueError('Canonical fields or provenance differ from sealed source reconstruction')
 return True
def available(e,cutoff):
 if type(cutoff) is not int:raise ValueError('Cutoff must be integer ns')
 f=e['fields'];known=f['INGESTION_TIME']
 if known['status']!='PROVEN':return False
 clocks=[known['value']]
 for k in ['PUBLICATION_TIME','REVISION_TIME','EVENT_TIME']:
  if f[k]['status']=='PROVEN':clocks.append(f[k]['value'])
 return max(clocks)<=cutoff
def economic_join(a,b):
 required=['ASSET_IDENTITY','CHAIN','CONTRACT_ADDRESS','VENUE','MARKET_TYPE','BASE','QUOTE','SETTLEMENT','MARGIN_ASSET','LINEAR_INVERSE','CONTRACT_MULTIPLIER','EXPIRY','PRICE_TYPE','UNIT','CURRENCY']
 for k in required:
  x,y=a['fields'][k],b['fields'][k]
  if x['status']=='PROVEN' and y['status']=='PROVEN' and x['value']!=y['value']:raise ValueError('Identity mismatch: '+k)
 for k in required:
  x,y=a['fields'][k],b['fields'][k]
  if x['status'] not in ['PROVEN','N/A'] or y['status'] not in ['PROVEN','N/A']:raise ValueError('Incomplete identity: '+k)
  if x!=y:raise ValueError('Different status or semantics: '+k)
 return True
