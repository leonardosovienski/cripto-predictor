import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root=Path(__file__).resolve().parent/'cripto-v1.2'
evidence=root/'docs/evidence/altcoin_forward_20260907'
protocol=json.loads((evidence/'protocol.json').read_text())
protocol['universe']=protocol['universe'].replace('plus RLUSD, USDF, USDG, USDQ, EURR, U and', 'plus RLUSD and')
protocol['registration_amendments']=[{'known_at':datetime.now(timezone.utc).isoformat(),'before_first_prospective_decision':True,'change':'Only the verified known RLUSD category error is excluded additionally. Do not classify symbols such as U from their ticker alone. No addition/removal based on returns.'}]
protocol['mark_fee_accounting']='For a hypothetical 1000 USDT budget, consume displayed asks; deduct assumed 10bps buy fee from acquired base quantity. Additional slippage stresses are quantity haircuts. Exit consumes displayed bids and deducts assumed 10bps sell fee and the extra slippage haircut from quote proceeds. Daily v2 neighbor-score cost algebra remains frozen; book-mark accounting is a distinct declared observation proxy. Lot-size rounding, account restrictions and tax are not certified.'
protocol['synthetic_control_plan']='Seed 20260907: fixed 1600-observation two-cluster kNN200 positive/negative geometry control over 80 weeks, one censored-neighbor guard, 100 stipulated zero-log-drift week-common-shock replicates (two candidate queries each). Report qualification count without interpreting it as general null calibration. Conditional power grid: extra 5/10/20 annual percentage points over dated 11.3177% scenario, weekly paired log SD 1/3/5%, dependence multipliers 1/4, two-sided alpha 5%, power 80%. No observed market return feeds this grid.'
(evidence/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
files=['scripts/observe_altcoin_forward.py','scripts/check_altcoin_forward_design.py','scripts/prepare_altcoin_payoff.py','scripts/research_altcoin_analogs.py','scripts/collect_altcoin_analogs.py','docs/evidence/altcoin_forward_20260907/protocol.json','docs/evidence/altcoin_analogs_20260907/protocol.json','docs/evidence/altcoin_payoff_20260907/protocol.json']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
freeze={'known_at':datetime.now(timezone.utc).isoformat(),'repository_files':{f:sha(root/f) for f in files},'acquisition_sha256':sha(root.parent/'altcoin-data/acquisition.json'),'training_sha256':sha(root.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz'),'note':'Exact byte hashes; changing code/input requires a documented new freeze before later decisions. Local hashes do not supply independent trusted timestamps.'}
(evidence/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
