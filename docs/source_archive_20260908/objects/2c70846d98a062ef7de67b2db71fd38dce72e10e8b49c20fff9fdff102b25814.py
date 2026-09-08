"""Build the user-facing export only after successful independent restoration."""
from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

STAGE = Path(__file__).resolve().parent
OUTPUT = STAGE.parents[1]/'outputs'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    restored=STAGE/'teste-restauracao'
    result=json.loads((restored/'RESTAURACAO.json').read_text(encoding='utf-8'))
    validation=json.loads(result['validation'])
    assert validation['status']=='PASS'
    assert result['git_restored'] is True
    assert result['git_status']=='?? fred_test.csv'
    manifest=json.loads((STAGE/'MANIFESTO.json').read_text(encoding='utf-8'))
    changed=[]
    for row in manifest['files']:
        source=Path(row['source'])
        st=source.stat()
        if (st.st_mtime_ns,st.st_size)!=(row['mtime_ns'],row['size']):
            changed.append(row['source'])
    if changed:raise ValueError('Sources changed since snapshot: '+str(changed))
    old_automation=Path(r'C:\Users\Superleo13\.codex\automations\observar-altcoins-semanalmente\automation.toml')
    if sha(old_automation) != sha(STAGE/'configuracao/automation-original.toml'):
        raise ValueError('Automation changed after snapshot.')
    critical=[]
    names={'ledger.jsonl','automation-original.toml','fred_test.csv'}
    for row in manifest['files']:
        if Path(row['path']).name in names:
            if sha(Path(row['source'])) != row['sha256']:
                raise ValueError('Source changed: '+row['source'])
            critical.append({'path':row['path'],'sha256':row['sha256']})
    report={'status':'PASS','verified_at_utc':datetime.now(UTC).isoformat(),'source_files':len(manifest['files']),'runtime_files':len(manifest['runtime_files']),'source_files_plus_runtime':len(manifest['files'])+len(manifest['runtime_files']),'logical_bytes':manifest['logical_bytes']+manifest['runtime_bytes'],'unique_payloads':manifest['unique_objects'],'git_head':result['git_head'],'git_status':result['git_status'],'restoration_on_different_path':True,'tested_on_other_physical_computer':False,'runtime_and_observers':validation,'critical_files':critical,'automation_installed':False,'note':'Source state unchanged at packaging. Snapshot cannot include later collections.'}
    report['focused_tests']=result['focused_tests']
    report['relocated_environment_files']=result['relocated_environment_files']
    report['restoration_test_note']=result['test_note']
    (STAGE/'VALIDACAO.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    filename='CRIPTO_MIGRACAO_WINDOWS_20260908.zip'
    archive=OUTPUT/filename
    with zipfile.ZipFile(archive,'w',allowZip64=True,compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(STAGE/'dados.zip','dados.zip',compress_type=zipfile.ZIP_STORED)
        for name in ('MANIFESTO.json','LEIA-ME.md','RETOMAR_NO_CODEX.md','restaurar.py','validar.py','VALIDACAO.json'):
            z.write(STAGE/name,name)
        for row in manifest['runtime_files']:
            z.write(STAGE/'runtime'/row['path'],'runtime/'+row['path'])
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise ValueError('Final ZIP CRC error: '+bad)
        with z.open('dados.zip') as f:
            if hashlib.file_digest(f,'sha256').hexdigest()!=sha(STAGE/'dados.zip'):
                raise ValueError('Nested payload ZIP changed')
    digest=sha(archive)
    (OUTPUT/(filename+'.sha256')).write_text(digest+'  '+filename+'\n',encoding='ascii')
    shutil.copyfile(STAGE/'LEIA-ME.md',OUTPUT/'CRIPTO_MIGRACAO_WINDOWS_20260908_GUIA.md')
    shutil.copyfile(STAGE/'VALIDACAO.json',OUTPUT/'CRIPTO_MIGRACAO_WINDOWS_20260908_VALIDACAO.json')
    print(json.dumps({'status':'PASS','archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest,'logical_bytes':report['logical_bytes'],'files':report['source_files_plus_runtime']},indent=2))
if __name__=='__main__':main()
