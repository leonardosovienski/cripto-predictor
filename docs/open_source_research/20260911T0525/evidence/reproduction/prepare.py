import pathlib,json,hashlib,datetime,subprocess,urllib.request,concurrent.futures
P=pathlib.Path;R=P(__file__).resolve().parents[1];REPO=P('C:/Cripto/pesquisa-20260909');OLD=REPO/'docs/open_source_research/20260911T0233'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2),encoding='utf-8')
protected=list(OLD.rglob('*'))+list((REPO/'charters').rglob('*'))+list((REPO/'observation_plans').rglob('*'))+[REPO/n for n in ['GarimpoInvestimentos/trials.json','docs/NEXT_CHAT_PROMPT.md','uv.lock','pyproject.toml']]
code=list((REPO/'GarimpoInvestimentos').rglob('*.py'))+list((REPO/'tests').glob('*.py'))
write('BASELINE.json',{'registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'HEAD':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'protected':{str(p):sha(p) for p in protected if p.is_file()},'code_before':{str(p):sha(p) for p in code},'historical_baseline_HEAD':'e4f8974beadc02aed63c7f94cf3d80cb27d4dd7f','allowed':'new research package, tests, CLI dispatch, README; no frozen trials/snapshots; no capital; no remote push'})
projects={
'freqtrade/freqtrade':['freqtrade/plugins/pairlist/VolumePairList.py','freqtrade/plugins/pairlist/AgeFilter.py','tests/plugins/test_pairlist.py','LICENSE'],
'stefan-jansen/alphalens-reloaded':['src/alphalens/performance.py','src/alphalens/utils.py','tests/test_performance.py','LICENSE'],
'hummingbot/hummingbot':['hummingbot/core/data_type/in_flight_order.py','test/hummingbot/core/data_type/test_in_flight_order.py','LICENSE'],
'skfolio/skfolio':['src/skfolio/model_selection/_combinatorial.py','tests/test_model_selection/test_combinatorial.py','LICENSE'],
'mlflow/mlflow':['mlflow/store/tracking/file_store.py','tests/store/tracking/test_file_store.py','LICENSE'],
'microsoft/qlib':['qlib/workflow/__init__.py','qlib/data/dataset/handler.py','LICENSE'],
'QuantConnect/Lean':['Common/Algorithm/Framework/Portfolio/PortfolioConstructionModel.cs','Algorithm/Selection/UniverseSelection.cs','LICENSE'],
'robertmartin8/PyPortfolioOpt':['pypfopt/efficient_frontier/efficient_frontier.py','tests/test_efficient_frontier.py','LICENSE.txt']}
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Cripto-Capability-Research','Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'})
 with urllib.request.urlopen(req,timeout=35) as r:return r.read()
def project(item):
 repo,paths=item;dest=R/'upstream'/repo.replace('/','__');dest.mkdir(parents=True,exist_ok=True);result={'repo':repo,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
 try:
  commit=json.loads(get('https://api.github.com/repos/'+repo+'/commits?per_page=1'))[0]['sha'];result['commit']=commit
  for path in paths:
   url=f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
   try:
    raw=get(url);p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);result['files'].append({'path':path,'url':url,'sha256':sha(p),'bytes':len(raw),'status':'OK'})
   except Exception as e:result['files'].append({'path':path,'url':url,'status':'UNAVAILABLE','error':type(e).__name__})
 except Exception as e:result['error']=repr(e)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:out=list(pool.map(project,projects.items()))
write('UPSTREAM.json',out);print(json.dumps([{'repo':x['repo'],'commit':x.get('commit'),'files':[(f['path'],f['status']) for f in x['files']]} for x in out],indent=2))
