import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

repo=Path(__file__).resolve().parent/'cripto-v1.2'
evidence=repo/'docs/evidence/altcoin_forward_20260907'
path=evidence/'freeze.json'
old=path.read_bytes()
(evidence/'freeze_preflight.json').write_bytes(old)
freeze=json.loads(old)
freeze['known_at']=datetime.now(timezone.utc).isoformat()
freeze['previous_freeze_sha256']=hashlib.sha256(old).hexdigest()
freeze['amendment']='Add current-catalog status diffs and verification of the preceding snapshot; no signal, price, cost or selection changes. Forty-four tests pass. Before first prospective decision. Original preflight used freeze_preflight.json and remains preserved.'
freeze['repository_files']['scripts/observe_altcoin_forward.py']=hashlib.sha256((repo/'scripts/observe_altcoin_forward.py').read_bytes()).hexdigest()
path.write_text(json.dumps(freeze,indent=2)+'\n')
print(hashlib.sha256(path.read_bytes()).hexdigest())
