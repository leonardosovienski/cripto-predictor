import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

work = Path(__file__).resolve().parent
repo = work / 'cripto-research'
evidence = repo / 'docs/evidence/absolute_research_20260908'
outputs = work.parent / 'outputs'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo).strip()
shutil.copyfile(evidence / 'DECISAO.md', outputs / 'CRIPTO_RESULTADOS.md')
shutil.copyfile(evidence / 'absolute-results-v3/results.json', outputs / 'CRIPTO_RESULTADOS.json')
shutil.copyfile(evidence / 'REPRODUZIR.md', outputs / 'COMO_REPRODUZIR.md')
target = outputs / 'CRIPTO_CODIGO_DADOS_REPRODUCAO.zip'
assert not target.exists()
files = subprocess.check_output(['git','ls-files','-z'],cwd=repo).decode('utf-8').split('\0')
entries = []
omitted = []
for name in files:
    if not name:
        continue
    p = repo / name
    if name.startswith('docs/session_archive_20260907/') or (p.suffix in {'.zip','.001','.002','.bundle'} and p != evidence / 'RESEARCH_DATA.zip'):
        omitted.append(name)
        continue
    assert p.is_file(), name
    entries.append((p, 'code/' + name))
metadata = {'source_commit':commit, 'branch':'codex/cripto-absolute-research-20260908', 'base_commit':'fbf4c714a092668bc1b82942ebdececd396e3ab7','files':{name:{'sha256':sha(p),'bytes':p.stat().st_size} for p,name in entries},'omitted_previous_session_recovery_archives':omitted,'omission_scope':'All new data/results and exact source files required for the new experiment remain included. Old large recovery packages are preserved in original Git/backup, not copied here.'}
with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p,name in entries:
        z.write(p,name)
    z.writestr('FILES_SHA256.json',json.dumps(metadata,ensure_ascii=False,indent=2))
    z.writestr('LEIA_PRIMEIRO.md','# Pesquisa de criptomoedas\n\nLeia `code/docs/evidence/absolute_research_20260908/DECISAO.md` e `REPRODUZIR.md` na mesma pasta.\n\nO código corresponde ao commit local '+commit+'. O pacote permite reproduzir os novos experimentos sem a pasta da tarefa antiga. Use os bytes exatos dos arquivos, incluindo finais de linha. Não copie dados sobre o observador atual.\n')
check = work / 'package-extracted-check'
assert not check.exists()
with zipfile.ZipFile(target) as z:
    z.extractall(check)
    assert z.testzip() is None
for name,record in metadata['files'].items():
    assert sha(check/name)==record['sha256'],name
delivery = {'source_commit':commit,'package':target.name,'package_sha256':sha(target),'package_bytes':target.stat().st_size,'package_files_verified':len(entries),'report_sha256':sha(outputs/'CRIPTO_RESULTADOS.md'),'data_archive_sha256':sha(evidence/'RESEARCH_DATA.zip')}
(outputs/'ENTREGA_SHA256.json').write_text(json.dumps(delivery,indent=2)+'\n',encoding='utf-8')
print(json.dumps(delivery,indent=2))
