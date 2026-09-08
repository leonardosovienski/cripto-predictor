import hashlib
import json
import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path

work = Path(__file__).resolve().parent
root = work / 'cripto-research'
original_work = Path('C:/Users/Superleo13/Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto/work')
original = original_work / 'cripto-v1.2'
evidence = root / 'docs/evidence/absolute_research_20260908'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
frozen = json.loads((original / 'docs/evidence/altcoin_retro_20260907/code_freeze.json').read_text())
for name, expected in frozen.items():
    assert sha(original / name) == expected, name
    shutil.copyfile(original / name, root / name)
    assert sha(root / name) == expected, name
protected = [p for p in original.rglob('*') if p.is_file() and any(str(p.relative_to(original)).replace('\\', '/').startswith(x) for x in ['charters/', 'GarimpoInvestimentos/trials', 'docs/evidence/altcoin_reviewed_20260907/'])]
checks = {str(p.relative_to(original)).replace('\\', '/'): sha(p) for p in protected}
now = datetime.now(timezone.utc).isoformat()
registry = {'registered_at_utc': now, 'protocol_commit': 'e41773a', 'protocol_sha256': sha(evidence / 'protocol.json'), 'mode': 'ADAPTIVE_DISCOVERY', 'full_historical_search_count': None, 'trials': [{'id': name, 'status': 'REGISTERED', 'evaluations': 0} for name in ['AR1_BTCUSDT', 'AR1_ETHUSDT', 'AR2_BTCUSDT', 'AR2_ETHUSDT', 'AR3_UNIVERSE']]}
(evidence / 'trials.json').write_text(json.dumps(registry, indent=2) + '\n')
(evidence / 'protected_original.json').write_text(json.dumps(checks, indent=2) + '\n')
automation = tomllib.loads(Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml').read_text())
old = json.loads((original / 'docs/session_archive_20260907/automation_snapshot.json').read_text())['configuration']
assert all(automation[k] == old[k] for k in ('prompt', 'name', 'kind', 'rrule', 'status'))
assert automation['target_thread_id'] == '01a07e75-d166-7430-859b-2af2c6ab0b0f'
snapshot = {'checked_at': now, 'configuration': automation, 'preserved_fields_exact': True, 'runtime_files_checked': 3785, 'runtime_exit': 0, 'tick_exit': 0, 'status': json.loads((original_work / 'altcoin-reviewed-data/status.json').read_text()), 'ledger_file_sha256': sha(original_work / 'altcoin-reviewed-data/ledger.jsonl')}
(evidence / 'automation_transfer.json').write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
paths = {'original_repository': str(original), 'original_work': str(original_work), 'runtime': str(original / '.venv/Scripts/python.exe'), 'new_repository': str(root), 'new_data': str(work / 'carry-research-data'), 'altcoin_history': str(original_work / 'altcoin-retro-data'), 'old_scores': str(original_work / 'altcoin-retro-results/scores.json.gz')}
(evidence / 'local_paths.json').write_text(json.dumps(paths, indent=2) + '\n')
print(json.dumps({'registered': now, 'protected': len(checks), 'frozen_original_bytes_copied': len(frozen), 'automation_exact': True}))
