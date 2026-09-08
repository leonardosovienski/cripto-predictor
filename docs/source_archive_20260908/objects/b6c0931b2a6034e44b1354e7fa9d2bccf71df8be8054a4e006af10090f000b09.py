import hashlib
import json
import shutil
import subprocess
from pathlib import Path

WORK = Path(__file__).resolve().parent
SOURCE = WORK / 'cripto-research'
ORIGINAL = Path('C:/Users/Superleo13/Documents/Codex/2026-09-07/files-mentioned-by-the-user-cripto/work/cripto-v1.2')
DEST = WORK / 'git-main-integration'
EVIDENCE = DEST / 'docs/evidence/git_consolidation_20260908'
OUT = WORK.parent / 'outputs'
FREEZES = [
    'absolute_research_20260908/reproduction_freeze.json',
    'basis_research_20260908/implementation_freeze.json',
    'basis_research_20260908/execution_planner_freeze.json',
    'chat_review_20260908/new_code_freeze.json',
    'altcoin_reviewed_20260907/freeze.json',
    'carry_forward_20260908/code_freeze.json',
    'immediate_audit_20260908/freeze.json',
]
expected = {}
for freeze in FREEZES:
    name = 'docs/evidence/' + freeze
    raw = (SOURCE / name).read_bytes()
    record = json.loads(raw)
    files = record.get('files', record.get('repository_files', record))
    for path, digest in files.items():
        assert isinstance(digest, str) and len(digest) == 64, (path, digest)
        assert path not in expected or expected[path] == digest, path
        expected[path] = digest
    expected[name] = hashlib.sha256(raw).hexdigest()
registry = json.loads((SOURCE / 'docs/evidence/basis_research_20260908/trials.json').read_bytes())
expected['docs/evidence/basis_research_20260908/protocol.json'] = registry['protocol_sha256']
for manifest_name in [
    'docs/evidence/absolute_research_20260908/absolute-results-v2/FILES_SHA256.json',
    'docs/evidence/absolute_research_20260908/absolute-results-v3/FILES_SHA256.json',
    'docs/evidence/basis_research_20260908/results-v2/FILES_SHA256.json',
]:
    manifest_path = SOURCE / manifest_name
    raw = manifest_path.read_bytes()
    for name, digest in json.loads(raw).items():
        relative = (manifest_path.parent / name).relative_to(SOURCE).as_posix()
        expected[relative] = digest
    expected[manifest_name] = hashlib.sha256(raw).hexdigest()
restored = []
for name, digest in expected.items():
    raw = (SOURCE / name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest and (ORIGINAL / name).is_file():
        raw = (ORIGINAL / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, ('source differs', name)
    current = (DEST / name).read_bytes()
    assert current.replace(b'\r\n', b'\n') == raw.replace(b'\r\n', b'\n'), ('semantic difference', name)
    if current != raw:
        (DEST / name).write_bytes(raw)
        restored.append(name)
(DEST / '.gitattributes').write_text(
    '# Frozen research evidence must retain the exact original bytes on every platform.\n'
    '# Do not normalize these files or rewrite their published SHA256 manifests.\n'
    + ''.join('/' + name + ' -text\n' for name in sorted(expected)), encoding='utf-8')
archive = DEST / 'docs/session_archive_20260908/deliverables'
archive.mkdir(parents=True, exist_ok=True)
manifest = {}
for file in sorted(OUT.iterdir()):
    if file.is_file() and not file.name.startswith('GIT_'):
        assert file.stat().st_size < 100 * 1024 * 1024, file
        shutil.copyfile(file, archive / file.name)
        manifest[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
(archive.parent / 'DELIVERABLES_SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
# Text delivery hashes also need stable checkout bytes.
with (DEST / '.gitattributes').open('a', encoding='utf-8') as f:
    f.write('/docs/session_archive_20260908/deliverables/** -text\n')
before = json.loads((WORK / 'git-consolidation-before.json').read_bytes())
refs = []
for ref in before['refs']:
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', ref['sha'], 'HEAD'], cwd=DEST)
    assert result.returncode == 0, ref['ref']
    refs.append({**ref, 'ancestor_consolidated_history': True})
report = {
    'original_refs': refs,
    'original_remote_heads': before['actual_remote_heads'],
    'checked_history_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=DEST,text=True).strip(),
    'restored_exact_bytes': restored,
    'frozen_files_and_manifests': expected,
    'original_manifest_hashes_unchanged': True,
    'deliverables_archived': manifest,
    'uncommitted_files': 'Preserved in original worktrees and verified local ZIP; not published as current code.',
    'backups': {name: {'sha256': hashlib.sha256((OUT/name).read_bytes()).hexdigest(), 'bytes': (OUT/name).stat().st_size}
        for name in ['GIT_BACKUP_TODAS_BRANCHES_20260908.bundle', 'GIT_ALTERACOES_LOCAIS_PRESERVADAS_20260908.zip']},
}
(EVIDENCE / 'reconciliation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'refs_ancestry_verified': len(refs), 'files_and_manifests_frozen':len(expected), 'restored_byte_exact':len(restored), 'deliverables_archived':len(manifest)}, indent=2))
