import datetime as dt
import hashlib
import importlib.metadata as im
import json
import pathlib
import platform
import sqlite3
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
def git(*args):
    return subprocess.check_output(['git',*args],cwd=REPO,text=True).strip()
files=git('ls-files').splitlines()
selected=[p for p in files if p.endswith('.py') and p.startswith(('GarimpoInvestimentos/','scripts/','tests/'))]
inventory=[{'path':p,'bytes':(REPO/p).stat().st_size,'sha256':hashlib.sha256((REPO/p).read_bytes()).hexdigest()} for p in selected]
result={'observed_at':dt.datetime.now(dt.UTC).isoformat(),'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'status':git('status','--short'),'remote_main':git('ls-remote','https://github.com/leonardosovienski/cripto-predictor.git','refs/heads/main'),'python':platform.python_version(),'platform':platform.platform(),'versions':{},'inventory':inventory,'coverage':'Inventory is not reading or execution. Protected evaluators and data not opened.'}
for package in ['predictor-core','predictor-ops','numpy','scipy','scikit-learn','ccxt','hmmlearn','pytest','ruff','httpx','pandas']:
    try: result['versions'][package]=im.version(package)
    except im.PackageNotFoundError: result['versions'][package]='NOT_INSTALLED'
for name,path in [('feature_store','C:/Cripto/operacao/saidas/feature_store.db'),('quota','C:/Cripto/operacao/dados/api_guard_budget.db')]:
    db=sqlite3.connect('file:'+path+'?mode=ro',uri=True)
    db.execute('PRAGMA query_only=ON')
    schemas=db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall()
    result[name]={'path':path,'tables':[r[0] for r in schemas],'schema':dict(schemas)}
    if name=='feature_store':
        result[name]['counts']={r[0]:db.execute('SELECT count(*) FROM "'+r[0]+'"').fetchone()[0] for r in schemas if r[0] in ['predictions','market_snapshots','prediction_inputs','raw_market_data']}
        if 'market_snapshots' in result[name]['tables']:
            rows=db.execute('SELECT payload_json FROM market_snapshots').fetchall()
            result[name]['snapshots']=[{k:json.loads(r[0]).get(k) for k in ['feature_version','symbol','interval','available_at','collected_at','raw_http_response_preserved']} for r in rows]
    db.close()
for p in ['docs/NEXT_CHAT_PROMPT.md','charters/scientific_state.json','GarimpoInvestimentos/trials.json','uv.lock']:
    result.setdefault('preservation',{})[p]=hashlib.sha256((REPO/p).read_bytes()).hexdigest()
(ROOT/'baseline.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['inventory','quota','feature_store']},ensure_ascii=False))
print(json.dumps({'feature_store':{k:v for k,v in result['feature_store'].items() if k!='schema'}},ensure_ascii=False))
