import concurrent.futures
from datetime import datetime, UTC
import json
from pathlib import Path
import shutil
from restaurar import relocate_environment, run, sha

stage=Path(__file__).resolve().parent
root=stage/'teste-restauracao'
manifest=json.loads((stage/'MANIFESTO.json').read_text(encoding='utf-8'))
relocated=relocate_environment(root,manifest)
exceptions={r['path']:r['after'] for r in relocated}
def check(row):
    expected=exceptions.get(row['path'],row['sha256'])
    if sha(root/row['path'])!=expected:
        raise ValueError('Restored file changed: '+row['path'])
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for i,_ in enumerate(pool.map(check,manifest['files']),1):
        if i%10000==0:print('Rechecked',i,flush=True)
for row in manifest['runtime_files']:
    if sha(root/'runtime'/row['path'])!=row['sha256']:
        raise ValueError('Restored runtime changed: '+row['path'])
for name in ('MANIFESTO.json','LEIA-ME.md','validar.py','RETOMAR_NO_CODEX.md'):
    shutil.copyfile(stage/name,root/name)
repo=root/'projeto'
git=shutil.which('git')
head=run([git,'-C',repo,'rev-parse','HEAD'])
status=run([git,'-C',repo,'status','--short'])
assert head==manifest['git_head'] and status=='?? fred_test.csv'
python=root/'sessoes/20260907-altcoins/work/cripto-v1.2/.venv/Scripts/python.exe'
validation=run([python,stage/'validar.py',root])
assert json.loads(validation)['status']=='PASS'
tests=(stage/'migration-tests.log').read_text(encoding='utf-8-sig')
assert '55 passed' in tests
report={'files_verified':len(manifest['files']),'destination':str(root),'source_snapshot_utc':manifest['created_utc'],'verified_utc':datetime.now(UTC).isoformat(),'relocated_environment_files':relocated,'automation_installed':False,'git_restored':True,'git_head':head,'git_status':status,'validation':validation,'focused_tests':{'passed':55,'output':tests},'test_note':'Full extraction tested; embedded uv Python paths and Git newline settings corrected, then every restored file rehashed. Frozen sources, data and dependency files unchanged.'}
(root/'RESTAURACAO.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','files_rechecked':len(manifest['files']),'runtime_files':len(manifest['runtime_files']),'tests_passed':55,'git_status':status},indent=2))
