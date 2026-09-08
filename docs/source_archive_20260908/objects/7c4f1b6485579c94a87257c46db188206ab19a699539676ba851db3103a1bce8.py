import hashlib
import json
import shutil
from pathlib import Path

work = Path(__file__).resolve().parent
archive = work / 'cripto-v1.2/docs/session_archive_20260907'
original = archive / 'WORKSPACE_RESEARCH.zip'
expected = hashlib.sha256(original.read_bytes()).hexdigest()
parts = []
with original.open('rb') as source:
    number = 1
    while block := source.read(64 * 1024 * 1024):
        path = archive / f'WORKSPACE_RESEARCH.zip.{number:03d}'
        with path.open('xb') as target:
            target.write(block)
        parts.append(path)
        number += 1
assert hashlib.sha256(b''.join(p.read_bytes() for p in parts)).hexdigest() == expected
backup = work / 'session-workspace-full.zip'
assert not backup.exists()
shutil.move(str(original), str(backup))
inventory_path = archive / 'inventory.json'
inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
record = inventory['files'].pop('WORKSPACE_RESEARCH.zip')
inventory['workspace_archive'] = {**record, 'parts': [p.name for p in parts],
                                'reassembly': 'Concatenate part bytes in listed order; no decompression between parts.'}
for p in parts:
    inventory['files'][p.name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(archive / '.gitattributes').write_text('* -text\ndeliverables/** -diff\n', encoding='utf-8')
print(json.dumps({'parts': [p.name for p in parts], 'sha256': expected}))
