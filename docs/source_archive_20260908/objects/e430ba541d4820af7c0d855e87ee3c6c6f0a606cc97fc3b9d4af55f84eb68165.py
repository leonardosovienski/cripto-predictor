import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

repo=Path(__file__).resolve().parent/'cripto-v1.2'
old=repo/'docs/evidence/altcoin_forward_20260907'
new=repo/'docs/evidence/altcoin_profit_20260907'
new.mkdir(exist_ok=True)
p=json.loads((old/'protocol.json').read_text())
p.update({
 'id':'discovery-altcoin-absolute-profit-20260907-v4',
 'base_commit':'0fd58c90a7d4ae32fbbce02cba035e0dbdeed469',
 'authorization':'2026-09-07 user: Qualquer corretora pq pode ser qualquer cripto e não compara com nada é só pra dar lucro só isso.',
 'registered_at':datetime.now(timezone.utc).isoformat(),
 'amendment':'User-directed objective and research scope correction before any prospective entries. Replace the comparison-oriented v3 observer with this separate cohort. No prior evidence, training, outcomes or old ledger are overwritten. No outcome-driven parameter search.',
 'economic_objective':{'kind':'ABSOLUTE_NET_PROFIT','acceptance':'Ending value exceeds starting value after all applicable costs, in the same currency. Do not require beating Selic, BTC, a basket or any external investment.','reporting_currency':'BRL','observed_mark_currency':'USDT','unknown_costs':'Public book marks use stated fee/slippage scenarios. Account commission, conversion and taxes are not certified. Missing costs are unknown, not zero; a partial USDT mark is not certified net BRL investor profit.','minimum_user_profit_amount':None,'minimum_user_annual_return':None,'external_benchmark_required':False,'venue_preselection_required_from_user':False},
 'venue_policy':'No user-imposed venue preference. Agent may choose public research venues by suitable data, liquidity and all-in costs. Current tested adapter is Binance public spot only; permission to research other venues is not a claim of implemented worldwide coverage or account accessibility.',
 'universe_mode':'all_current_spot_usdt',
 'universe':'All currently TRADING, spot-enabled Binance USDT symbols, with no original 240-symbol cap and no ranking by past outcome for inclusion. Keep declared non-crypto/stable exclusions plus RLUSD and explicit leveraged-token identification. BTC may itself be a candidate. Every candidate must still have the same 90 complete delayed daily bars and median quote volume >=5 million USDT. Asset classification and coverage are not globally certified. Other exchanges/quotes remain outside the current adapter, not prohibited by user preference.',
 'comparisons':False,
 'entry_mark':p['entry_mark'].split(' Also record BTC')[0]+' Record only the hypothetical selected portfolio; no BTC or basket reference portfolio.',
 'economic_reference':'No external investment benchmark. Compare only the same portfolio starting and ending value after costs. USDT marks and eventual BRL economic profit must be labeled separately until conversion and tax route are verified. User delegates venue selection for research; do not keep asking them to choose a benchmark or a preferred exchange.',
 'synthetic_control_plan':p['synthetic_control_plan'].split(' Conditional power grid:')[0]+' Conditional planning grid uses absolute annual net-return scenarios 1/5/10/20%, weekly log standard deviations 1/3/5% and dependence multipliers 1/4, against zero net profit. These are planning assumptions, not user targets, forecasts or an external comparison. An arbitrarily small positive edge has no fixed finite detection horizon.',
 'scheduler':'Update the existing thread heartbeat, preserving weekly timing and notification preferences. Use this v4 protocol and a separate v4 data directory; first future anchor and last due anchor unchanged.',
 'registration_amendments':[]
})
(new/'protocol.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(hashlib.sha256((new/'protocol.json').read_bytes()).hexdigest())
