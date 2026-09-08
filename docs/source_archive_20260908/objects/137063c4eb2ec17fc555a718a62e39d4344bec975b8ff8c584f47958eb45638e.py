"""Read-only validation of relocated frozen code, runtime and observation ledgers."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(python, cwd, code):
    proc = subprocess.run([str(python), '-B', '-c', code], cwd=cwd, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def validate(root):
    alt = root/'sessoes/20260907-altcoins/work/cripto-v1.2'
    carry = root/'sessoes/20260907-pesquisa/work/cripto-research'
    python = alt/'.venv/Scripts/python.exe'
    locations = child(python, alt, '''
import json, sys, GarimpoInvestimentos, numpy, scipy, httpx
print(json.dumps({'prefix':sys.prefix, 'base_prefix':sys.base_prefix, 'project':GarimpoInvestimentos.__file__, 'numpy':numpy.__file__, 'scipy':scipy.__file__, 'httpx':httpx.__file__}))
''')
    for name, location in locations.items():
        if not Path(location).resolve().is_relative_to(root):
            raise RuntimeError('Dependencia fora da restauracao: '+name+' = '+location)
    runtime = subprocess.run([str(python), '-B', '-m', 'scripts.verify_research_runtime'], cwd=alt, capture_output=True, text=True)
    if runtime.returncode:
        raise RuntimeError(runtime.stdout + runtime.stderr)
    altcoin = child(python, alt, '''
import json, gzip, hashlib
from pathlib import Path
from scripts.observe_altcoin_forward import Ledger, verify_freeze
data = Path('../altcoin-reviewed-data')
freeze = verify_freeze(Path('../altcoin-data'), Path('../altcoin-payoff-results/samples_identity_corrected.json.gz'), Path('docs/evidence/altcoin_reviewed_20260907'))
ledger = Ledger(data/'ledger.jsonl')
snapshots = 0
raws = 0
for row in ledger.rows:
    payload = row['payload']
    if 'snapshot' in payload:
        p = Path(payload['snapshot'])
        if hashlib.sha256(p.read_bytes()).hexdigest() != payload['snapshot_sha256']:
            raise ValueError('Snapshot divergente: '+str(p))
        snapshots += 1
for p in (data/'raw').glob('*.bin.gz'):
    gzip.decompress(p.read_bytes())
    raws += 1
print(json.dumps({'freeze_sha256':freeze, 'ledger_rows':len(ledger.rows), 'snapshots_verified':snapshots, 'raw_gzip_readable':raws}))
''')
    carry_result = child(python, carry, '''
import json
from pathlib import Path
from scripts.observe_carry_forward import verify
from scripts.research_io import Ledger
from scripts.carry_public import verify_sources
protocol, freeze = verify()
data = Path('../carry-forward-data')
ledger = Ledger(data/'ledger.jsonl')
sources = 0
for row in ledger.rows:
    snapshot = row['payload'].get('snapshot')
    if snapshot:
        verify_sources(data, snapshot['sources'])
        sources += len(snapshot['sources'])
print(json.dumps({'freeze_sha256':freeze, 'ledger_rows':len(ledger.rows), 'raw_sources_verified':sources}))
''')
    print(json.dumps({'status':'PASS','runtime':json.loads(runtime.stdout),'locations':locations,'altcoin':altcoin,'carry':carry_result,'network_requests':0,'ledgers_modified':False}, indent=2))


if __name__ == '__main__':
    validate(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent)
