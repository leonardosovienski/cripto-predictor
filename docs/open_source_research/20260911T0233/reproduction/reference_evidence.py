import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[1]
OLD=ROOT.parent
DEST=ROOT/'external';DEST.mkdir(exist_ok=True)
deep=json.loads((OLD/'deep_sources.json').read_text(encoding='utf-8'))
def get(url,path):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'CriptoResearchAudit/1.0'})
        with urllib.request.urlopen(req,timeout=20) as r:
            b=r.read(3_000_001)
            if len(b)>3_000_000:raise ValueError('Document limit')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
            return dict(url=url,status=r.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),path=str(path),observed_at=dt.datetime.now(dt.UTC).isoformat())
    except Exception as e:return dict(url=url,status='UNAVAILABLE',error=type(e).__name__+': '+str(e))
def collect(d):
    repo=d['repository'];folder=DEST/repo.replace('/','__');receipts=[]
    for name in ['LICENSE','LICENSE.md','LICENSE.txt']:
        rec=get('https://raw.githubusercontent.com/'+repo+'/'+d['ref']+'/'+name,folder/name)
        receipts.append(rec)
        if rec['status']==200:break
    atom=get('https://github.com/'+repo+'/releases.atom',folder/'releases.atom');receipts.append(atom)
    releases=[]
    if atom['status']==200:
        tree=ET.fromstring(pathlib.Path(atom['path']).read_bytes())
        ns={'a':'http://www.w3.org/2005/Atom'}
        for entry in tree.findall('a:entry',ns)[:2]:
            releases.append({key:entry.findtext('a:'+key,namespaces=ns) for key in ['title','updated','content']})
    return dict(id=d['id'],repository=repo,receipts=receipts,releases=releases)
with cf.ThreadPoolExecutor(max_workers=3) as pool:result=list(pool.map(collect,deep))
(ROOT/'maintenance_licenses.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{'id':x['id'],'license':[(pathlib.Path(r.get('path','')).name,r['status']) for r in x['receipts'][:-1]],'releases':[(r['title'],r['updated']) for r in x['releases']]} for x in result]))
