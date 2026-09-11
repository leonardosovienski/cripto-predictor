import pathlib,subprocess,sys,json,time
R=pathlib.Path(__file__).resolve().parents[1];REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
checks=[('ruff',[sys.executable,'-m','ruff','check','GarimpoInvestimentos/research','GarimpoInvestimentos/cli.py','tests/test_research_capabilities.py']),('format',[sys.executable,'-m','ruff','format','--check','GarimpoInvestimentos/research','GarimpoInvestimentos/cli.py','tests/test_research_capabilities.py']),('types',[sys.executable,'-m','pyright','--pythonpath',sys.executable,'GarimpoInvestimentos/research']),('full_suite',[sys.executable,'-m','pytest','-q','--junitxml='+str(R/'full_suite.xml')]),('secrets',[sys.executable,'scripts/scan_secrets.py','.']),('wheel',[sys.executable,'-m','build','--wheel','--no-isolation','--outdir',str(R/'wheel')])]
result=[]
for name,cmd in checks:
 start=time.perf_counter()
 with (R/(name+'.log')).open('w',encoding='utf-8') as f:p=subprocess.run(cmd,cwd=REPO,stdout=f,stderr=subprocess.STDOUT)
 result.append({'check':name,'exit_code':p.returncode,'seconds':time.perf_counter()-start,'command':cmd});(R/'CHECKS.json').write_text(json.dumps(result,indent=2));print(name,p.returncode,flush=True)
 # Continue independent checks and preserve all failures.
sys.exit(int(any(r['exit_code'] for r in result)))
