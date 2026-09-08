"""Run only after the pushed commit's four CI jobs succeed."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

WORK = Path(__file__).resolve().parent
REPO = WORK / 'git-main-integration'
MAIN = Path('C:/Users/Superleo13/cripto-predictor')
OUT = WORK.parent / 'outputs'
BEFORE = json.loads((WORK / 'git-consolidation-before.json').read_bytes())


def command(args, cwd=REPO):
    p = subprocess.run(args, cwd=cwd, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors='replace') + p.stdout.decode(errors='replace'))
    return p.stdout.decode('utf-8').strip()


def git(*args, cwd=REPO):
    return command(['git', '-c', 'core.safecrlf=false', *args], cwd=cwd)


def heads():
    return {name: sha for sha, name in (line.split() for line in git('ls-remote', '--heads', 'origin').splitlines())}


target = git('rev-parse', 'HEAD')
run_id = sys.argv[1]
run = json.loads(command(['gh', 'run', 'view', run_id, '--json', 'headSha,status,conclusion,jobs,url']))
assert run['headSha'] == target and run['conclusion'] == 'success' and run['status'] == 'completed', run
required = {'quality', 'all-extras', 'container', 'python-314-experimental'}
passed = {j['name'] for j in run['jobs'] if j['conclusion'] == 'success'}
assert required <= passed, (required, passed)
remote = heads()
assert remote['refs/heads/main'] == target, remote
for ref in BEFORE['refs']:
    git('merge-base', '--is-ancestor', ref['sha'], target)
for name, sha in remote.items():
    git('merge-base', '--is-ancestor', sha, target)
assert git('diff', '--name-only', cwd=MAIN) == ''
assert git('diff', '--cached', '--name-only', cwd=MAIN) == ''
fred = MAIN / 'fred_test.csv'
fred_hash = hashlib.sha256(fred.read_bytes()).hexdigest()

# Only fast-forward main; unrelated untracked files must survive unchanged.
git('merge', '--ff-only', target, cwd=MAIN)
assert hashlib.sha256(fred.read_bytes()).hexdigest() == fred_hash
worktrees = []
for block in git('worktree', 'list', '--porcelain').split('\n\n'):
    fields = dict(line.split(' ', 1) for line in block.splitlines() if ' ' in line)
    if fields.get('branch') and fields['branch'] != 'refs/heads/main':
        folder = Path(fields['worktree'])
        before_status = git('status', '--porcelain=v1', cwd=folder)
        names = git('ls-files', '-z', cwd=folder).split('\0')
        hashes = {n: hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in names if n and (folder/n).is_file()}
        git('switch', '--detach', fields['HEAD'], cwd=folder)
        assert git('rev-parse', 'HEAD', cwd=folder) == fields['HEAD']
        assert git('status', '--porcelain=v1', cwd=folder) == before_status
        assert all(hashlib.sha256((folder/n).read_bytes()).hexdigest() == h for n,h in hashes.items())
        worktrees.append({'path':str(folder), 'head':fields['HEAD'], 'tracked_files_preserved':len(hashes), 'uncommitted_status_preserved':True})

# Atomic, expected-value deletion protects against concurrent remote changes.
extras = {n:s for n,s in remote.items() if n != 'refs/heads/main'}
if extras:
    git('push', '--atomic', *['--force-with-lease='+n+':'+s for n,s in extras.items()], 'origin', *[':'+n for n in extras])
git('fetch', '--prune', 'origin')
local_extras = [n for n in git('for-each-ref','--format=%(refname:short)','refs/heads').splitlines() if n != 'main']
if local_extras:
    git('branch', '-d', *local_extras)
assert git('for-each-ref','--format=%(refname:short)','refs/heads') == 'main'
assert heads() == {'refs/heads/main':target}
assert git('rev-parse','main') == target == git('rev-parse','origin/main')
assert git('status','--porcelain=v1',cwd=MAIN) == '?? fred_test.csv'
with ZipFile(OUT/'GIT_ALTERACOES_LOCAIS_PRESERVADAS_20260908.zip') as archive:
    manifest = json.loads(archive.read('FILES_SHA256.json'))
    roots = {'git-final':Path('C:/Users/Superleo13/Documents/Codex/2026-08-26/contexto-e-papel-atue-como-um/work/git-final'), 'main-untracked':MAIN}
    assert all(hashlib.sha256((roots[n.split('/',1)[0]]/n.split('/',1)[1]).read_bytes()).hexdigest()==h for n,h in manifest.items())
preserved = {
    Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml'):'3b70e3f068c41ef3c964fed543ba388f8237b6f207ce49f5a4ff3c8caec95cfb',
    Path('C:/Users/Superleo13/Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto/work/altcoin-reviewed-data/ledger.jsonl'):'42e96f95f1765784e12cbf9fed2d77d26cbd0f268bbbaf46bcdf3715ec6141a5',
    WORK/'carry-forward-data/ledger.jsonl':'ba505dc92ac32645294106342b6be93a3905a4c5ab89570db1a28c3f20896a18',
}
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in preserved.items())
report = {
    'completed_utc':datetime.now(timezone.utc).isoformat(),
    'repository':'https://github.com/leonardosovienski/cripto-predictor',
    'main_commit':target, 'local_branches':['main'], 'remote_branches':['main'],
    'all_original_21_refs_ancestor_of_main':True,
    'original_refs':BEFORE['refs'],
    'remote_branches_removed':extras,
    'local_branches_removed':local_extras,
    'ci':run,
    'preserved_worktrees':worktrees,
    'uncommitted_files_preserved':len(manifest),
    'automation_and_observer_ledgers_preserved':True,
    'historical_tag_preserved':git('rev-parse','cripto-session-20260907-final^{}'),
    'main_untracked_file_preserved':'fred_test.csv',
}
(OUT/'GIT_MAIN_CONCLUIDO_20260908.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(OUT/'GIT_MAIN_CONCLUIDO_20260908.md').write_text(
    '# Publicação e consolidação concluídas\n\n'
    + 'Main local e GitHub: `'+target+'`. Somente a branch `main` permanece nos dois locais.\n\n'
    + 'Todas as 21 referências anteriores são ancestrais da main. Conflitos foram conciliados preservando correções posteriores; os commits originais permanecem no histórico.\n\n'
    + 'Validação local: 1.170 testes passaram. Os quatro jobs do [CI do commit publicado]('+run['url']+') passaram, incluindo container.\n\n'
    + 'Trinta entregas de código/dados/relatórios estão versionadas. Os bytes e hashes científicos foram preservados.\n\n'
    + 'As outras branches foram apagadas após a validação. As pastas dos observadores permanecem nos commits originais, com HEAD destacado. Automação e diários conservaram os hashes. Os 337 arquivos locais da cópia de segurança também permaneceram intactos; alterações antigas sem commit e fred_test.csv não foram apagados nem publicados como código vigente.\n\n'
    + 'Backups locais verificados: `GIT_BACKUP_TODAS_BRANCHES_20260908.bundle` e `GIT_ALTERACOES_LOCAIS_PRESERVADAS_20260908.zip`. Detalhes completos no JSON que acompanha este relatório.\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('main_commit','local_branches','remote_branches','all_original_21_refs_ancestor_of_main','uncommitted_files_preserved','automation_and_observer_ledgers_preserved')},indent=2))
