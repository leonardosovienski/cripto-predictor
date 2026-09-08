import json
from pathlib import Path
root = Path(__file__).parent
r = json.loads((root / 'absolute-results-v2/results.json').read_text())
for name, row in r['carry'].items():
    print(name, 'candidate', row['future_observation_candidate'], 'step', row['current_quantity_step'])
    for c, s in row['scenarios'].items():
        print(c, {k:s[k] for k in ['profit_usdt_mechanical','funding_usdt','basis_pnl_usdt','fees_slippage_usdt','round_trip_hedges','active_weeks','cash_weeks','maximum_drawdown_daily_close_and_final_unwind','minimum_hourly_collateral_surplus_usdt','minimum_30pct_mark_jump_surplus_usdt','first_conservative_margin_breach','first_jump_breach']})
        print('bootstrap', s['bootstrap']['interval_95_usdt'], 'years', s['by_year'], 'concentration', s['concentration'])
s=r['spot']
print('SPOT', {k:s['overall'][k] for k in ['active_weeks','cash_weeks','selected_holdings','censored_selected_holdings','average_exposure','trade_stats_primary','cost_scenarios']})
print('years', {k:v['cost_scenarios']['10'] for k,v in s['by_entry_year'].items()})
print('concentration',s['concentration']['10'])
print('unresolved',s['unresolved'])
print('bootstrap',s['registered_bootstrap']['40'])
print('symbols',s['symbol_contributions_usdt_primary'])
