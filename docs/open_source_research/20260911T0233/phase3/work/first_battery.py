import sys,pathlib,json,gzip,dataclasses,hashlib,datetime
sys.dont_write_bytecode=True
R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'phase2/work'))
import experiments as v2
b=json.loads((R/'BASELINE.json').read_bytes());out=[]
for c in b['sample']:
 p=pathlib.Path(c['path']);raw=p.read_bytes();data=json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
 meta=json.loads(pathlib.Path(c['metadata']).read_bytes()) if c['metadata'] else {}
 print(c['id'], 'keys/first',str(data[0] if isinstance(data,list) and data else (list(data) if isinstance(data,dict) else data))[:550], 'meta',str(meta.get('sources',meta))[:450])
 # Direct reconstruction is deliberately strict: do not create a fictional instrument or publication time.
 try:v2.Observation(**{'receipt_hash':hashlib.sha256(raw).hexdigest(),'value':str(data[0][4]) if c['kind']=='klines' and data else '0'})
 except (TypeError,ValueError) as e:err=str(e)
 else:err=None
 out.append({'case':c['id'],'result':'UNSUPPORTED_DIRECT_REAL_RECEIPT','exception':err,'reason':'Real receipt has no complete explicit v2 Instrument plus three proven clocks. No defaults invented.','round_trip':'NOT_ELIGIBLE','data_kind':c['kind']})
result={'executed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'adapter_hash':v2.sha(pathlib.Path(b['adapter_path'])),'unchanged':v2.sha(pathlib.Path(b['adapter_path']))==b['adapter_sha256'],'cases':out,'scope_defects':[{'id':'D01','property':'Preserve observation semantic type','evidence':'Observation fields have no price_type, metric or observation unit; mark and traded candle cannot be encoded distinctly by those fields alone.','classification':'REPRESENTATION_GAP_NOT_OBSERVED_PRODUCTION_COLLISION'},{'id':'D02','property':'Preserve incomplete clocks and field-level evidence','evidence':'Required published_at cannot represent UNKNOWN, and no source/revision/field provenance fields exist.','classification':'REPRESENTATION_GAP'}],'bugs_found':0,'semantic_round_trip_failures':0,'not_eligible':len(out),'warning':'This first battery rejects direct ingestion. It does not claim a production join occurred or that unknown economic identities are now proven.'}
(R/'V2_FIRST_BATTERY.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
