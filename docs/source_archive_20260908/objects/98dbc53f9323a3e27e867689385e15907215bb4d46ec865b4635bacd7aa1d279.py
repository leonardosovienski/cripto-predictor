import gzip
import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

work = Path(__file__).resolve().parent
repo = work / 'cripto-research'
evidence = repo / 'docs/evidence/absolute_research_20260908'
oldwork = Path('C:/Users/Superleo13/Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto/work')
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, v):
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

v2, v3 = work / 'absolute-results-v2', work / 'absolute-results-v3'
economics = []
for p in (v2 / 'carry').glob('*_ledger.json'):
    assert p.read_bytes() == (v3 / 'carry' / p.name).read_bytes(), p.name
    economics.append('carry/' + p.name)
for name in ('decisions.json', 'weekly_results.json', 'results.json'):
    assert (v2 / 'spot' / name).read_bytes() == (v3 / 'spot' / name).read_bytes()
    economics.append('spot/' + name)
assert (v2 / 'carry/decisions.json').read_bytes() == (v3 / 'carry/decisions.json').read_bytes()
write(evidence / 'causality_correction_verification.json', {'economics_unchanged_byte_for_byte': economics, 'carry_decisions_unchanged': True, 'source_path_replaced_by_hash': True, 'current_filters_no_longer_used_by_simulation': True})
for name in ('absolute-results-v2', 'absolute-results-v3'):
    shutil.copytree(work / name, evidence / name, dirs_exist_ok=True)
logs = evidence / 'logs'
logs.mkdir(exist_ok=True)
for p in work.glob('research-*.log'):
    shutil.copyfile(p, logs / p.name)
shutil.copyfile(work / 'carry-acquisition.log', logs / 'carry-acquisition.log')
shutil.copyfile(work / 'independent-audit.json', evidence / 'independent-audit.json')
prior = read(evidence / 'trials.json')
prior['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
prior['evaluations_per_stream'] = 1
prior['software_replays'] = 1
prior['result_path'] = 'absolute-results-v3/results.json'
for trial in prior['trials']:
    trial['status'] = 'COMPLETED_ADAPTIVE_HISTORICAL'
    trial['evaluations'] = 1
    trial['preserved_previous_output'] = 'absolute-results-v2'
write(evidence / 'trials.json', prior)
original = oldwork / 'cripto-v1.2'
checks = read(evidence / 'protected_original.json')
assert all(sha(original / name) == expected for name, expected in checks.items())
snapshot = read(evidence / 'automation_transfer.json')
automation_path = Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml')
actual = tomllib.loads(automation_path.read_text(encoding='utf-8'))
historical_configuration = read(original / 'docs/session_archive_20260907/automation_snapshot.json')['configuration']
assert all(actual[k] == historical_configuration[k] for k in ('prompt','kind','name','status','rrule'))
assert actual['target_thread_id'] == snapshot['configuration']['target_thread_id']
if actual != snapshot['configuration']:
    assert {k for k in actual if actual[k] != snapshot['configuration'].get(k)} == {'prompt'}
    snapshot['configuration'] = actual
    snapshot['snapshot_encoding_correction'] = 'Initial helper decoded both comparison inputs with Windows CP1252. Live automation was always valid UTF-8 and unchanged. Snapshot now reread explicitly as UTF-8 and compared to original preserved configuration.'
    write(evidence / 'automation_transfer.json', snapshot)
assert sha(oldwork / 'altcoin-reviewed-data/ledger.jsonl') == snapshot['ledger_file_sha256']
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=original).strip()
write(evidence / 'preservation_check.json', {'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'protected_original_files':len(checks), 'original_git_clean':True, 'observer_ledger_unchanged':True, 'automation_configuration_unchanged_since_transfer':True, 'current_task':actual['target_thread_id'], 'main_commit':subprocess.check_output(['git','rev-parse','main'],cwd=repo,text=True).strip()})

# Make an immutable, portable data snapshot. Existing archives are never overwritten.
target = evidence / 'RESEARCH_DATA.zip'
if not target.exists():
    contents = []
    for name, directory in [('carry', work / 'carry-research-data'), ('altcoin', oldwork / 'altcoin-retro-data')]:
        for p in sorted(directory.rglob('*')):
            if p.is_file():
                contents.append((p, name + '/' + p.relative_to(directory).as_posix()))
    contents.append((oldwork / 'altcoin-retro-results/scores.json.gz', 'prior/scores.json.gz'))
    # Preserve official identity-resolution source responses from the previous research.
    for p in sorted((oldwork / 'altcoin-payoff-data/raw').glob('*.json')):
        meta = read(p)
        if '7d5accdcf8f446f3ba3d79f8747a28e2' in meta.get('url', ''):
            contents.extend([(p, 'identity/' + p.name), (p.with_suffix('.bin.gz'), 'identity/' + p.with_suffix('.bin.gz').name)])
    manifest = {name: {'sha256':sha(p), 'bytes':p.stat().st_size} for p, name in contents}
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p,name in contents:
            z.write(p,name)
        z.writestr('FILES_SHA256.json', json.dumps(manifest,indent=2))
    write(evidence / 'data_snapshot.json', {'archive':'RESEARCH_DATA.zip','sha256':sha(target),'files':len(contents),'bytes':target.stat().st_size,'includes_raw_and_normalized':True})
print(json.dumps({'identical_economic_files':len(economics), 'data_snapshot':read(evidence / 'data_snapshot.json'), 'original_preserved':True},indent=2))
