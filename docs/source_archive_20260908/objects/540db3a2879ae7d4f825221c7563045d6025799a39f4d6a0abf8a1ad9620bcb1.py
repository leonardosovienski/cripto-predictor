import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx

work = Path(__file__).parent
root = work / 'cripto-v1.2'
dest = root / 'docs/evidence'
dest.mkdir(exist_ok=True)
files = subprocess.check_output(['git', 'ls-files', '*.md'], cwd=root, text=True).splitlines()
inventory = []
for name in files:
    content = (root / name).read_text(encoding='utf8')
    for no, line in enumerate(content.splitlines(), 1):
        if re.search(r'\bDSR\b|\bSR0\b|\bdsr\b', line) and re.search(r'\d', line):
            inventory.append({'path': name, 'line_at_audit': no, 'text': line.strip(),
                              'status': 'HISTORICAL_OR_THRESHOLD_NOT_REVALIDATED'})
(dest / 'cripto_v12_dsr_inventory.json').write_text(json.dumps({
    'as_of': '2026-09-07', 'base_commit': '3c104ce',
    'scope': 'All versioned Markdown numeric mentions of DSR/SR0; thresholds and historical claims distinguished in HYPOTHESES.md P0-A.',
    'decision': 'Do not use historical DSR as current evidence until original returns, ledger snapshot and comparable Sharpe bases are recovered.',
    'current_ledger_sha256': hashlib.sha256((root / 'GarimpoInvestimentos/trials.json').read_bytes()).hexdigest(),
    'n_trials': 26, 'n_finite_sharpes': 23,
    'diagnostic_sr0_filtered': 0.9524130493332158,
    'diagnostic_sr0_all': 0.9777608299827842,
    'diagnostic_valid_for_inference': False,
    'mentions': inventory,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

sources = json.loads((work / 'public-sources/manifest.json').read_text(encoding='utf8'))
for row in sources:
    row['interpretation'] = 'AVAILABILITY_ONLY_NOT_ALPHA'
    if row['name'] == 'selic': row['interpretation'] = 'REJECTED_FUTURE_EVENT_DATE'
    if row['name'] == 'selic_effective': row['interpretation'] = 'OBSERVED_AS_OF_2026_09_04_NOT_FORWARD_GUARANTEE'
    if row.get('status') != 200: row['interpretation'] = 'UNAVAILABLE_NO_INFERRED_VALUE'
url = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados'
r = httpx.get(url, params={'formato': 'json', 'dataInicial': '04/09/2026', 'dataFinal': '07/09/2026'}, timeout=20)
sources.append({'name': 'selic_bounded', 'url': str(r.url), 'accessed_at': datetime.now(UTC).isoformat(),
                'status': r.status_code, 'sha256': hashlib.sha256(r.content).hexdigest(), 'data': r.json(),
                'interpretation': 'OBSERVED_POLICY_RATE_WITH_EVENT_DATE_CUTOFF'})
(dest / 'cripto_v12_sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

dossier = {
    'status': 'DRAFT_NOT_REGISTERED_NOT_AUTHORIZED',
    'as_of': '2026-09-07',
    'proposed_family': 'funding_carry_structural_v1',
    'related_frozen_family': 'funding_oi_hmm_v3',
    'previous_result': 'H1-H3 CLOSED_NO_GO: funding/OI as directional predictor; family remains frozen.',
    'closure_reason': 'Directional edge did not survive registered PSR/IC/MaxDD and assumed execution costs; no family reopening.',
    'new_information': 'Economically different target: funding payments to a delta-hedged spot-long/perp-short structure, not directional forecasts. No new alpha result claimed.',
    'causal_reason': 'Payment from perpetual longs to shorts when funding is positive; compensates financing, basis, liquidation and counterparty constraints. Sign can reverse.',
    'why_old_test_no_longer_answers_question': 'Predictive score-return correlation does not identify net funding cashflows on a hedged collateral structure; this distinction alone does not establish deployability or approve research.',
    'new_protocol': {
        'mode': 'DISCOVERY', 'activate': False, 'capital_authorized': False,
        'first_gate': 'G1_KILL_UNDER_CURRENT_ENVELOPE',
        'stopping_rule': 'No outcome test until venue/collateral G1 and a same-currency benchmark/cost G2 are decidable; then G3-G7 in order.',
        'universe_proposed': ['BTCUSDT', 'ETHUSDT'],
        'target': 'Net funding receipts plus basis P&L minus spot/perp fees, fills, unwind, FX, taxes and capital opportunity cost.',
        'temporal_rule': 'Record event_time and actual observation known_at; historical settlement data are discovery-only.',
        'sample_power': 'UNKNOWN until concrete structure and minimum economically relevant effect are fixed; pre-register before outcomes.',
        'no_reuse': 'No re-run/reparameterization of H1-H3; no modification of production collection.',
        'required_before_activation': ['operator benchmark accessibility', 'venue and collateral structure', 'observed friction', 'FX route and costs', 'risk premium and attention costs'],
    },
}
p = root / 'docs/reopen_dossiers/funding_carry_structural_v1.json'
p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

p = root / 'docs/HYPOTHESES.md'
p.write_text(p.read_text(encoding='utf8') + (work / 'audit_delta.md').read_text(encoding='utf8'), encoding='utf8')
print('DSR mentions inventoried:', len(inventory))
