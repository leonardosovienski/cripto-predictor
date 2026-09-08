from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
REPO = WORK / 'cripto-v1.2'
ARCHIVE = REPO / 'docs/session_archive_20260907'
INCLUDE_DIRS = {
    'altcoin-data', 'altcoin-forward-data', 'altcoin-forward-probes',
    'altcoin-payoff-data', 'altcoin-payoff-results', 'altcoin-profit-data',
    'altcoin-results', 'altcoin-retro-data', 'altcoin-retro-results',
    'altcoin-reviewed-data', 'carry-data', 'core-wheel', 'public-sources',
    'build-artifacts', 'review-build', 'review-runtime-wheels',
}


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    ARCHIVE.mkdir(exist_ok=False)
    deliverables = ARCHIVE / 'deliverables'
    deliverables.mkdir()
    output_files = sorted((ROOT / 'outputs').iterdir())
    assert len(output_files) == 42 and all(p.is_file() for p in output_files)
    for p in output_files:
        shutil.copyfile(p, deliverables / p.name)
    shutil.copyfile(WORK / 'previous_prompt.txt', ARCHIVE / 'previous_prompt.txt')
    source = Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml')
    automation = tomllib.loads(source.read_text(encoding='utf-8'))
    assert automation['status'] == 'ACTIVE'
    assert automation['target_thread_id'] == '01a07d06-406f-7781-adad-0d0ea3ae9424'
    write_json(ARCHIVE / 'automation_snapshot.json', {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'timezone': 'America/Sao_Paulo',
        'source_sha256': digest(source),
        'configuration': automation,
        'live_automation_changed_in_this_closure': False,
        'migration_to_successor_task': 'REQUIRED_BEFORE_CLAIMING_UNINTERRUPTED_SCHEDULING',
    })
    shutil.copyfile(WORK / 'altcoin-reviewed-data/status.json', ARCHIVE / 'observer_status_snapshot.json')
    selected = [p for p in WORK.iterdir() if p.is_file()]
    for name in sorted(INCLUDE_DIRS):
        assert (WORK / name).is_dir(), name
        selected.extend(p for p in (WORK / name).rglob('*') if p.is_file()
                        and '__pycache__' not in p.parts and p.name != 'observer.lock')
    forbidden = {'.env', '.git', '.venv', 'auth.json', 'credentials.json'}
    assert not any(forbidden.intersection(p.relative_to(WORK).parts) for p in selected)
    index = {}
    zip_path = ARCHIVE / 'WORKSPACE_RESEARCH.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(selected):
            name = p.relative_to(WORK).as_posix()
            index[name] = {'sha256': digest(p), 'bytes': p.stat().st_size}
            z.write(p, name)
        z.writestr('WORKSPACE_FILES_SHA256.json', json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    verified = 0
    with zipfile.ZipFile(zip_path) as z:
        for name, record in index.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == record['sha256'], name
            assert digest(WORK / name) == record['sha256'], name
            verified += 1
    previous_review = json.loads((ROOT / 'outputs/CRIPTO_REVISAO_FINAL.json').read_text(encoding='utf-8'))
    old_package = deliverables / 'CRIPTO_REVISAO_FINAL_REPRODUCAO.zip'
    assert digest(old_package) == '99d2063d33b9e517b58c1c35e5fec2c16cd29b3f1f6b1a34ce15879c3439fbb3'
    prompt = (REPO / 'docs/NEXT_CHAT_PROMPT.md').read_bytes()
    assert prompt == (ROOT / 'outputs/PROMPT_NOVO_CHAT.txt').read_bytes()
    write_json(ARCHIVE / 'prompt_review.json', {
        'reviewed_against': ['previous_prompt.txt', 'docs/PROJECT_STATE_20260907.md',
                             'deliverables/CRIPTO_REVISAO_FINAL.json', 'automation_snapshot.json'],
        'manual_semantic_review': 'PASS',
        'preserved': ['absolute net profit objective', 'free research venue/asset choice',
                      'solo work', 'no real capital/accounts/orders/paid services',
                      '1045 tests refer to prior review', '140 weeks with zero selected trades',
                      'BTC +54.84 and ETH +34.62 USDT are separate assumed-cost scenarios',
                      'no verified investor profit', 'new registered historical research authorized',
                      'old consumed data remain adaptive', 'frozen families and observer preserved'],
        'added_for_chat_independence': ['tracked report paths', 'snapshot of all deliverables',
                                      'shared Git location and independent bundle',
                                      'successor heartbeat migration instruction',
                                      'data path and byte-sensitive freeze restoration notes',
                                      'missing original attachment disclosed', 'local commit versus push distinction'],
        'original_prompt_sha256': digest(ARCHIVE / 'previous_prompt.txt'),
        'revised_prompt_sha256': hashlib.sha256(prompt).hexdigest(),
        'scientific_reassessment_in_this_closure': False,
        'last_review_conclusion': previous_review['conclusion'],
    })
    write_json(ARCHIVE / 'inventory.json', {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        'prior_deliverables': 41, 'revised_prompt_deliverable': 1,
        'workspace_files_verified': verified,
        'workspace_directories_included': sorted(INCLUDE_DIRS),
        'workspace_root_files_included': True,
        'workspace_directories_excluded': sorted(p.name for p in WORK.iterdir()
                                               if p.is_dir() and p.name not in INCLUDE_DIRS),
        'exclusion_reason': 'Git source is committed separately; other directories contain virtual environments, caches, isolated test data, or redundant extracted/reproduced copies. __pycache__ and OS lock files excluded.',
        'original_attachment_available': False,
        'chat_deletion_performed': False,
        'automation_migrated': False,
        'files': {p.relative_to(ARCHIVE).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
                  for p in sorted(ARCHIVE.rglob('*')) if p.is_file()},
    })
    (ARCHIVE / '.gitattributes').write_text('* -text\n', encoding='utf-8')
    for doc_name in ['README.md', 'HANDOFF.md', 'docs/PROJECT_STATE_20260907.md']:
        p = REPO / doc_name
        existing = p.read_bytes()
        prefix = ('> Continuidade sem o chat antigo: `docs/SESSION_HANDOFF_20260907.md`; '
                  'prompt conferido: `docs/NEXT_CHAT_PROMPT.md`; '
                  'tag do fechamento: `cripto-session-20260907-final`.\n\n').encode('utf-8')
        p.write_bytes(prefix + existing)
    print(json.dumps({'deliverables': len(output_files), 'workspace_files_verified': verified,
                      'workspace_archive_bytes': zip_path.stat().st_size,
                      'workspace_archive_sha256': digest(zip_path)}, indent=2))


if __name__ == '__main__':
    main()
