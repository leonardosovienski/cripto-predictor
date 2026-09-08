import base64
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path

names = ('numpy', 'scikit-learn', 'scipy', 'httpx', 'predictor-core', 'predictor-ops', 'distlib', 'virtualenv')
result = {}
for name in names:
    package = metadata.distribution(name)
    checked, missing, mismatches = 0, [], []
    for item in package.files or []:
        if item.hash is None:
            continue
        path = item.locate()
        if not path.exists():
            missing.append(str(item))
            continue
        body = path.read_bytes()
        actual = base64.urlsafe_b64encode(hashlib.new(item.hash.mode, body).digest()).rstrip(b'=').decode()
        checked += 1
        if actual != item.hash.value:
            normalized = base64.urlsafe_b64encode(hashlib.new(item.hash.mode, body.replace(b'\r\n', b'\n')).digest()).rstrip(b'=').decode()
            mismatches.append({'path': str(item), 'matches_after_lf_normalization': normalized == item.hash.value})
    result[name] = {'version': package.version, 'files_checked': checked, 'missing': missing, 'mismatches': mismatches}
work = Path(__file__).resolve().parent
(work / 'review-runtime-integrity.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({name: {'checked': row['files_checked'], 'missing': len(row['missing']), 'mismatched': len(row['mismatches'])} for name, row in result.items()}, indent=2))
