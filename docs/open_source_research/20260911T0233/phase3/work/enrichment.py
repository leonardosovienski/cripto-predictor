"""Explicit derivative evidence, never backfilled into the primary observations."""
import sys
sys.dont_write_bytecode=True
import pathlib,json,datetime,decimal,hashlib
import adapter_v3 as a
R=pathlib.Path(__file__).resolve().parents[1];b=a.load(R/'BASELINE.json');c={x['id']:x for x in b['sample']}
def data(id):return a.decoded(c[id]['path'])[2]
def ref(id,path):return {'receipt':c[id]['path'],'sha256':b['read_only_hashes'][c[id]['path']],'field':path}
out=[]
for id in ['spot_info','future_info']:
 d=data(id);meta=a.load(c[id]['metadata']);m=next(x for x in meta['sources'] if x['name']==id)
 for symbol in ['BTCUSDT','ETHUSDT','WBETHUSDT','USDCUSDT','FDUSDUSDT']:
  for i,s in enumerate(d['symbols']):
   if s['symbol']!=symbol:continue
   fields={k:{'value':s[k],'evidence':ref(id,['symbols',i,k]),'transformation':'identity'} for k in ['symbol','baseAsset','quoteAsset','marginAsset','contractType','isSpotTradingAllowed'] if k in s}
   out.append({'case':id+'_'+symbol,'kind':'EXPLICIT_METADATA_ENRICHMENT','fields':fields,'known_at_ns':m['received_ns'],'historical_validity_start':'UNKNOWN','settlement':'UNKNOWN','decimals':'UNKNOWN; precision fields are not chain decimals','historical_backfill_authorized':False})
chain=data('aave_001');selector=data('aave_018');call=data('aave_019');decl=bytes.fromhex(selector['request']['params'][0][2:]).decode()
assert decl=='getReserveNormalizedIncome(address)' and call['request']['params'][0]['data'][:10]==selector['response']['result'][:10]
assert chain['endpoint']==call['endpoint']==selector['endpoint']
monthpath=pathlib.Path('C:/Cripto/pesquisa-20260909/docs/evidence/aave_validation_20260910/history/month-00.json');month=a.load(monthpath)
v=int(call['response']['result'],16)
assert v==int(month['normalized_income_ray']) and int(call['request']['params'][1],16)==month['number']
assert call['request']['params'][0]['to']==month['pool'] and '0x'+call['request']['params'][0]['data'][-40:]==month['native_usdc']
decimal.getcontext().prec=80;scaled=str(decimal.Decimal(v)/decimal.Decimal(10**27))
src=pathlib.Path('C:/Cripto/pesquisa-20260909/scripts/recover_aave_history.py')
assert 'RAY = 10**27' in src.read_text()
out.append({'case':'AAVE_EXPLICIT_BUNDLE','kind':'LOCAL_DECODER_CORROBORATION_NOT_INDEPENDENT_PROVIDER','chain_id':int(chain['response']['result'],16),'pool':month['pool'],'underlying_contract':month['native_usdc'],'function':decl,'block_number':month['number'],'raw_value':str(v),'normalized_index':scaled,'unit':'RAY-scaled normalized-income index under preserved local decoder; not USDC money','unit_transform':'exact Decimal(raw)/10**27','known_at_ns':max(a.stamp(x['received_at']) for x in [chain,selector,call]),'semantic_decoder_evidence':{'path':str(src),'sha256':b['read_only_hashes'][str(src)],'line':18},'receipt_evidence':[ref('aave_001',['response','result']),ref('aave_018',['request','params',0]),ref('aave_018',['response','result']),ref('aave_019',['request','params']),ref('aave_019',['response','result'])],'normalized_reference':{'path':str(monthpath),'sha256':b['read_only_hashes'][str(monthpath)],'fields':['normalized_income_ray','number','pool','native_usdc']},'limits':['same provider; not F02','historical implementation source mapping NOT_PROVEN','block timestamp from derived month record not proven by selected primary header','token decimals 6 appears in preserved month record and raw aave_027=6; signature receipt for decimals not in this exact sample, therefore no new historical ABI certification','chain endpoint corroborated at collection, not omniscient proof of immutable historical semantics'],'historical_backfill_authorized':False})
(R/'EXPLICIT_ENRICHMENT.json').write_text(json.dumps({'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'separate_from_primary':True,'derived_cases':out,'scope':'No new receipts, no retrospective replacement, no market unit or settlement defaults'},indent=2,ensure_ascii=False),encoding='utf-8')
print('Derivative evidence cases:',len(out),'Aave raw index:',v,'scaled:',scaled)
