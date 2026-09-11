import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

P=Path(r'C:\Cripto\pesquisa-20260909')
R=Path(r'C:\Cripto\operacao\relatorios\CAPABILITY_TRANSFER_20260911T0525')
result=[]
for args in [['-m','ruff','check','GarimpoInvestimentos/research','GarimpoInvestimentos/cli.py','tests/test_research_capabilities.py'],['-m','ruff','format','--check','GarimpoInvestimentos/research','GarimpoInvestimentos/cli.py','tests/test_research_capabilities.py']]:
    r=subprocess.run([sys.executable,*args],cwd=P,capture_output=True,text=True)
    result.append(dict(command=args,exit_code=r.returncode,output=r.stdout+r.stderr))
(R/'FINAL_CHECKS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
assert all(x['exit_code']==0 for x in result),result
wheels=list((R/'wheel').glob('*.whl'))
assert len(wheels)==1,wheels
w=wheels[0]
with zipfile.ZipFile(w) as z:
    files=z.namelist()
    pkg=[x for x in files if x.startswith('GarimpoInvestimentos/research/')]
    assert len([x for x in pkg if x.endswith('.py')])==7,pkg
# Run directly from wheel outside checkout, with existing runtime dependencies.
script=R/'work/wheel_smoke.py'
script.write_text('''import json,sys
sys.path.insert(0,sys.argv[1])
import GarimpoInvestimentos.research.__main__ as m
assert sys.argv[1] in m.__file__,m.__file__
result=m.evaluate(m.demo_config())
assert len(result)==4
print(json.dumps({'module':m.__file__,'outputs':list(result)}))
''',encoding='utf-8')
r=subprocess.run([sys.executable,str(script),str(w)],cwd=R,capture_output=True,text=True)
receipt=dict(wheel=str(w),sha256=hashlib.sha256(w.read_bytes()).hexdigest(),package_files=pkg,smoke_exit=r.returncode,smoke_output=r.stdout+r.stderr,build_method='uv build --wheel (isolated)',initial_build_failure='hatchling.build unavailable in --no-isolation environment')
(R/'WHEEL_CHECK.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
assert r.returncode==0
