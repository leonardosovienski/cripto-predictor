import pathlib,json,urllib.request,hashlib,concurrent.futures,datetime
root=pathlib.Path(__file__).resolve().parents[1]
deep=json.loads((root.parent/'deep_sources.json').read_text())
refs={r['id']:r for r in deep}
urls=[('R41','paper.pdf','https://www.bis.org/publ/work1087.pdf'),('R42','paper.pdf','https://www.nber.org/system/files/working_papers/w25882/w25882.pdf'),('R43','paper.pdf','https://jmlr.org/papers/volume11/cawley10a/cawley10a.pdf'),('R44','paper.pdf','https://arxiv.org/pdf/2208.06046')]
for rid,p in [('R03','crates/execution/src/models/fill.rs'),('R03','nautilus_trader/backtest/models.pyx'),('R27','COPYING'),('R39','LICENSE.TXT')]:
 r=refs[rid];urls.append((rid,p,f"https://raw.githubusercontent.com/{r['repository']}/{r['ref']}/{p}"))
def fetch(arg):
 rid,name,url=arg;row={'id':rid,'url':url,'observed_at':datetime.datetime.now(datetime.UTC).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Research review'}),timeout=25) as r:
   data=r.read(12_000_001);row.update(status=r.status,content_type=r.headers.get('Content-Type'),bytes=len(data))
  if len(data)>12_000_000:raise ValueError('cap')
  p=root/'external'/rid/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  row.update(path=str(p),sha256=hashlib.sha256(data).hexdigest(),is_pdf=data.startswith(b'%PDF'))
 except Exception as e:row.update(error=type(e).__name__)
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,urls))
(root/'additional_sources.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k not in ('url','path','sha256')} for r in rows],indent=2))
