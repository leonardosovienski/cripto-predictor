import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path

repo=Path(__file__).resolve().parent/'cripto-v1.2'
evidence=repo/'docs/evidence/altcoin_profit_20260907'
files=['scripts/observe_altcoin_forward.py','scripts/plan_absolute_profit.py','scripts/prepare_altcoin_payoff.py','scripts/research_altcoin_analogs.py','scripts/collect_altcoin_analogs.py','docs/evidence/altcoin_profit_20260907/protocol.json','docs/evidence/altcoin_analogs_20260907/protocol.json','docs/evidence/altcoin_payoff_20260907/protocol.json']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze={'known_at':datetime.now(timezone.utc).isoformat(),'repository_files':{f:sha(repo/f) for f in files},'acquisition_sha256':sha(repo.parent/'altcoin-data/acquisition.json'),'training_sha256':sha(repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz'),'note':'User-directed v4 scope. Frozen before new full-universe preflight. Training/scorer unchanged; no comparative portfolios. Legacy v3 uses its preserved Git revision or original reproduction archive, not this changed recorder.'}
(evidence/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(sha(evidence/'freeze.json'))
