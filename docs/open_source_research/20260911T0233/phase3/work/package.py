import pathlib,json,hashlib,shutil,zipfile
R=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((R/'BASELINE.json').read_bytes());bundle=R/'receipt_bundle';bundle.mkdir(exist_ok=True);index=[]
paths=set()
for c in b['sample']:
 paths.add(c['path'])
 if c['metadata']:paths.add(c['metadata'])
for p in b['read_only_hashes']:
 if p.endswith(('history\\month-00.json','scripts\\recover_aave_history.py')):paths.add(p)
for name in sorted(paths):
 p=pathlib.Path(name);dest=bundle/(sha(p)[:16]+'_'+p.name);shutil.copy2(p,dest);assert sha(dest)==b['read_only_hashes'][name]
 index.append({'original':name,'bundled':str(dest.relative_to(R)),'sha256':sha(dest)})
(R/'RECEIPT_BUNDLE_INDEX.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
files={str(p.relative_to(R)):sha(p) for p in sorted(R.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
(R/'MANIFEST.json').write_text(json.dumps({'initiative':'20260911T0233','phase':3,'files':files},indent=2),encoding='utf-8')
destinations=[pathlib.Path('C:/Cripto/pesquisa-20260909/docs/open_source_research/20260911T0233/phase3'),pathlib.Path('C:/Users/leona/Documents/Codex/2026-09-10/le/outputs/cripto-fase3-20260911/relatorio')]
for d in destinations:
 d.mkdir(parents=True,exist_ok=True)
 for rel,h in files.items():
  target=d/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/rel,target);assert sha(target)==h
 shutil.copy2(R/'MANIFEST.json',d/'MANIFEST.json')
z=destinations[1].parent/'cripto-fase3.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
 for p in sorted(destinations[1].rglob('*')):
  if p.is_file():f.write(p,p.relative_to(destinations[1]))
with zipfile.ZipFile(z) as f:assert f.testzip() is None
print(json.dumps({'files':len(files)+1,'receipt_bundle_files':len(index),'zip_bytes':z.stat().st_size,'report':str(destinations[1]/'REPORT.md'),'zip':str(z)}))
