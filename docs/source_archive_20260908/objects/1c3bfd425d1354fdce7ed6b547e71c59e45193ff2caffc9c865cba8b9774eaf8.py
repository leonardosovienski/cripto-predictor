import json, os, sys, collections, shutil
from pathlib import Path
BASE = Path(r'C:\Users\Superleo13')
TASK = BASE / 'Documents/Codex/2026-09-07/files-pasted-by-the-user-quero'
ROOTS = {
    'projeto': BASE / 'cripto-predictor',
    'sessoes/20260907-pesquisa': TASK,
    'sessoes/20260907-altcoins': BASE / 'Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto',
    'sessoes/20260826': BASE / 'Documents/Codex/2026-08-26/contexto-e-papel-atue-como-um',
    'backups-anteriores': BASE / 'Documents/CriptoBackup',
}
EXCLUDE = {'.git', '__pycache__', '.pytest_cache', '.ruff_cache', '.mypy_cache', '.pyright', 'node_modules'}
def scan():
    files, omitted, links, envs = [], [], [], []
    for label, root in ROOTS.items():
        for folder, dirs, names in os.walk(root, followlinks=False):
            p = Path(folder)
            if p == TASK / 'work/migracao' or (p / 'pyvenv.cfg').is_file():
                if (p/'pyvenv.cfg').is_file(): envs.append(str(p))
                omitted.append({'path': str(p), 'reason': 'virtualenv' if (p/'pyvenv.cfg').is_file() else 'migration staging'})
                dirs[:] = []
                continue
            for d in list(dirs):
                c = p / d
                if c.is_symlink() or c.is_junction():
                    links.append(str(c)); dirs.remove(d)
                elif d in EXCLUDE:
                    dirs.remove(d); omitted.append({'path':str(c), 'reason':'git database via bundle' if d == '.git' else 'rebuildable cache'})
            for name in names:
                f = p/name
                if name == '.git':
                    omitted.append({'path':str(f),'reason':'worktree pointer replaced by restoration'}); continue
                if p == TASK / 'outputs' and name.startswith('CRIPTO_MIGRACAO_'):
                    continue
                if f.is_symlink(): links.append(str(f)); continue
                rel = label + '/' + f.relative_to(root).as_posix()
                files.append({'source':str(f), 'archive':rel, 'size':f.stat().st_size})
    groups=collections.defaultdict(lambda: [0,0])
    for f in files:
        parts=f['archive'].split('/')
        key='/'.join(parts[:4] if parts[0]=='sessoes' else parts[:2])
        groups[key][0]+=1;groups[key][1]+=f['size']
    out={'roots':{k:str(v) for k,v in ROOTS.items()},'files':files,'omitted':omitted,'links':links,'virtualenvs':envs}
    (TASK/'work/migracao').mkdir(exist_ok=True)
    (TASK/'work/migracao/inventory.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({'files':len(files),'bytes':sum(f['size'] for f in files),'free':shutil.disk_usage(TASK).free,'virtualenvs':envs,'links':links,'largest_groups':sorted(groups.items(),key=lambda x:x[1][1],reverse=True)[:35],'sensitive_names':[f['archive'] for f in files if Path(f['source']).name.lower() in {'.env','credentials.json','auth.json','id_rsa','id_ed25519'}]},indent=2))
if __name__=='__main__':scan()
