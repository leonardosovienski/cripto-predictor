import pathlib,json,hashlib,shutil,zipfile
R=pathlib.Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
b=json.loads((R/'BASELINE.json').read_bytes());inputs=R/'input_bundle';inputs.mkdir(exist_ok=True)
names=set(b['additional_inputs']);p3=json.loads((R.parent/'phase3/BASELINE.json').read_bytes())
for c in p3['sample']:
 if c['id'] in ['spot_BTCUSDT','perp_trade','perp_mark','future_trade','future_mark','funding']:
  names.add(c['path']);names.add(c['metadata'])
index=[]
for p in sorted(names):
 path=pathlib.Path(p);h=sha(path);target=inputs/(h[:16]+'_'+path.name);shutil.copy2(path,target);assert sha(target)==h
 index.append({'original_path':p,'bundle_path':str(target.relative_to(R)),'sha256':h})
(R/'INPUT_BUNDLE_INDEX.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
request=pathlib.Path('C:/Users/leona/.codex/attachments/7ccbe530-f462-478b-b92f-fc0149c000e7/pasted-text.txt');shutil.copy2(request,R/'USER_REQUEST.md')
files={str(p.relative_to(R)):sha(p) for p in sorted(R.rglob('*')) if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts}
(R/'MANIFEST.json').write_text(json.dumps({'initiative':'20260911T0233','phase':'3B','files':files},indent=2),encoding='utf-8')
destinations=[pathlib.Path('C:/Cripto/pesquisa-20260909/docs/open_source_research/20260911T0233/phase3b'),pathlib.Path('C:/Users/leona/Documents/Codex/2026-09-10/le/outputs/cripto-fase3b-20260911/relatorio')]
for d in destinations:
 d.mkdir(parents=True,exist_ok=True)
 for name,h in files.items():
  target=d/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/name,target);assert sha(target)==h
 shutil.copy2(R/'MANIFEST.json',d/'MANIFEST.json')
z=destinations[-1].parent/'cripto-fase3b.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as f:
 for p in sorted(destinations[-1].rglob('*')):
  if p.is_file():f.write(p,p.relative_to(destinations[-1]))
with zipfile.ZipFile(z) as f:assert f.testzip() is None
assert all(sha(p)==h for p,h in b['protected_hashes'].items())
print(json.dumps({'files':len(files)+1,'inputs':len(index),'zip_bytes':z.stat().st_size,'report':str(destinations[-1]/'REPORT.md'),'zip':str(z)}))
