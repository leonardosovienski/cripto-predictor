"""Reproduce a frozen, descriptive economic screen; never executes orders."""
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

WORK = Path(__file__).parent
DATA = WORK / 'carry-data'
PROTOCOL = json.loads((WORK/'carry_protocol.json').read_text())
END = datetime.fromisoformat(PROTOCOL['end_exclusive_utc'].replace('Z', '+00:00'))
END_MS = int(END.timestamp()*1000)
SLOT = 8*3600*1000
CAPITAL = 5000.0
FX = 5.1253
START_MS = END_MS-365*86400000

def read(name):
    return json.loads((DATA/name).read_text(encoding='utf8'))

def benchmark(capital_usd):
    c = capital_usd*FX
    gross = c*.139
    fees_lo = .002*max(0,c-10000)
    fees_hi = .002*max(0,c+gross-10000)
    return {'capital_brl':c, 'gross_gain_brl':gross, 'tax_rate':.175,
            'custody_brl_range':[fees_lo,fees_hi],
            'net_gain_brl_range':[gross*.825-fees_hi,gross*.825-fees_lo],
            'net_return_range':[(gross*.825-fees_hi)/c,(gross*.825-fees_lo)/c]}

def quality(rows):
    times = [r['fundingTime'] for r in rows]
    assert len(set(times)) == len(times)
    assert all(START_MS<=t<END_MS for t in times)
    # Venue timestamps have millisecond settlement offsets; no rates are altered.
    offsets = [t%SLOT for t in times]
    assert max(offsets)<1000, ('non_8h_schedule', max(offsets))
    buckets = [t//SLOT for t in times]
    expected = set(range(START_MS//SLOT, END_MS//SLOT))
    assert len(set(buckets)) == len(buckets)
    missing = sorted(expected-set(buckets))
    assert not missing, ('missing_settlements',missing)
    return {'observations':len(rows),'expected':len(expected),'missing':0,'duplicates':0,
            'max_timestamp_offset_ms':max(offsets),'schedule_hours':8,
            'event_window_start':datetime.fromtimestamp(min(times)/1000,UTC).isoformat(),
            'event_window_end':datetime.fromtimestamp(max(times)/1000,UTC).isoformat()}

def fixed_quantity(symbol,rows,notional=2500):
    spot,mark = read(symbol+'_spot_daily.json'),read(symbol+'_mark_daily.json')
    # The last candle contains later intraday fields. Only its opening quote at
    # END is eligible; its high/low/close/volume are never read for outcomes.
    spot_by_open={x[0]:x for x in spot}
    mark_by_open={x[0]:x for x in mark}
    assert START_MS in spot_by_open and END_MS in spot_by_open
    assert START_MS in mark_by_open and END_MS in mark_by_open
    assert len([x for x in spot if START_MS<=x[0]<END_MS])==365
    assert len([x for x in mark if START_MS<=x[0]<END_MS])==365
    s0,s1=float(spot_by_open[START_MS][1]),float(spot_by_open[END_MS][1])
    f0,f1=float(mark_by_open[START_MS][1]),float(mark_by_open[END_MS][1])
    q=notional/s0
    eligible=[r for r in rows if r['fundingTime']//SLOT>START_MS//SLOT]
    assert all(r.get('markPrice') and float(r['markPrice'])>0 for r in eligible)
    receipts=math.fsum(q*float(r['markPrice'])*float(r['fundingRate']) for r in eligible)
    basis=q*((f0-s0)-(f1-s1))
    legs=q*(s0+s1+f0+f1)
    fees=q*(.001*(s0+s1)+.0005*(f0+f1))
    slip=legs*.0005
    maximum_mark=max(float(x[2]) for x in mark if START_MS<=x[0]<END_MS)
    max_short_price_loss=max(0,q*(maximum_mark-f0))
    return {'quantity':q,'spot_start':s0,'spot_end':s1,'mark_start':f0,'mark_end':f1,
            'eligible_settlements':len(eligible),'first_settlement_excluded':True,
            'funding_usdt':receipts,'basis_change_usdt':basis,
            'spot_pnl_usdt':q*(s1-s0),'perp_price_pnl_usdt':q*(f0-f1),
            'gross_mark_pnl_usdt':receipts+basis,'fee_illustration_usdt':fees,
            'slippage_5bps_each_side_usdt':slip,'net_scenario_usdt':receipts+basis-fees-slip,
            'net_scenario_brl_fx_unchanged':(receipts+basis-fees-slip)*FX,
            'maximum_daily_mark_high':maximum_mark,
            'max_price_only_short_loss_usdt':max_short_price_loss,
            'margin_cash_usdt':2500, 'margin_test':'NOT_A_LIQUIDATION_SIMULATION',
            'executable':False,'missing_execution':['fills','liquidation/maintenance rules','unwind slippage','venue eligibility','USDT/USD conversion','tax classification']}

results={'protocol_id':PROTOCOL['id'],'protocol_sha256':hashlib.sha256((WORK/'carry_protocol.json').read_bytes()).hexdigest(),
         'mode':'DISCOVERY_DESCRIPTIVE_NOT_PROOF','benchmark':benchmark(CAPITAL),'assets':{}}
bmin=results['benchmark']['net_gain_brl_range'][0]
for symbol in PROTOCOL['symbols']:
    rows=read(symbol+'_funding.json')
    checks=quality(rows)
    windows=[]
    for days in PROTOCOL['windows_days']:
        cutoff=END_MS-days*86400000
        subset=[r for r in rows if r['fundingTime']>=cutoff]
        rates=[float(r['fundingRate']) for r in subset]
        rate_sum=math.fsum(rates)
        monthly={}
        for row in subset:
            month=datetime.fromtimestamp(row['fundingTime']/1000,UTC).strftime('%Y-%m')
            monthly[month]=monthly.get(month,0)+float(row['fundingRate'])
        windows.append({'days':days,'n':len(rates),'rate_sum':rate_sum,
                        'simple_annualized_rate':rate_sum*365/days,
                        'negative_fraction':sum(x<0 for x in rates)/len(rates),
                        'funding_rate_min':min(rates),'funding_rate_max':max(rates),
                        'monthly_signed_sums':monthly})
    annual=next(w['rate_sum'] for w in windows if w['days']==365)
    receipts=2500*annual
    base_fees=2500*2*(.001+.0005)
    base_slip=2500*4*.0005
    net=receipts-base_fees-base_slip
    actual=fixed_quantity(symbol,rows)
    sensitivities=[]
    for slip in [0,5,10]:
        pnl_usd=receipts-base_fees-2500*4*slip/10000
        for fx_cost in [0,.005,.01]:
            for attention in [0,1200]:
                # FX cost expressed once as percentage of original committed capital.
                sensitivities.append({'slippage_bps_each_side':slip,'fx_cost_fraction':fx_cost,
                                      'attention_brl':attention,
                                      'economic_value_brl_fx_flat':pnl_usd*FX-CAPITAL*FX*fx_cost-attention})
    fx_sensitivity=[]
    for dx in [-.2,-.1,0,.1,.2]:
        gain_brl=((CAPITAL+actual['net_scenario_usdt'])*(1+dx)-CAPITAL)*FX
        fx_sensitivity.append({'usdbrl_change':dx,'gross_of_tax_value_brl':gain_brl,
                               'illustrative_after_15pct_tax_brl':gain_brl-.15*max(0,gain_brl),
                               'after_tax_excess_over_benchmark_brl':gain_brl-.15*max(0,gain_brl)-bmin})
    results['assets'][symbol]={'quality':checks,'windows':windows,
        'normalized_notional':{'funding_usdt_2500':receipts,'funding_brl_2500':receipts*FX,
            'funding_usdt_5000_zero_cost':5000*annual,'funding_brl_5000_zero_cost':5000*annual*FX,
            'roundtrip_fee_scenario_usdt':base_fees,'roundtrip_slippage_scenario_usdt':base_slip,
            'net_scenario_usdt':net,'net_scenario_brl':net*FX,
            'annual_funding_required_base':(bmin/FX+base_fees+base_slip)/2500,
            'annual_funding_required_with_attention':((bmin+1200)/FX+base_fees+base_slip)/2500,
            'zero_cost_notional_needed_for_benchmark_usdt':bmin/FX/annual,
            'zero_cost_required_n_over_capital':bmin/FX/annual/CAPITAL},
        'fixed_quantity':actual,'cost_sensitivity':sensitivities,'fx_sensitivity':fx_sensitivity,
        'fx_appreciation_needed_to_match_benchmark_pre_tax':(CAPITAL+bmin/FX)/(CAPITAL+actual['net_scenario_usdt'])-1,
        'decision': 'REJECT_FOR_THIS_ECONOMIC_SCREEN' if 5000*annual*FX<bmin else 'INCONCLUSIVE_REQUIRES_MORE_EVIDENCE'}

# Independent arithmetic and accounting checks, not another trial search.
for asset in results['assets'].values():
    f=asset['fixed_quantity']
    assert math.isclose(f['spot_pnl_usdt']+f['perp_price_pnl_usdt'],f['basis_change_usdt'],abs_tol=1e-8)
    assert math.isclose(asset['normalized_notional']['funding_usdt_2500']*2,
                        asset['normalized_notional']['funding_usdt_5000_zero_cost'])
    assert all(s['economic_value_brl_fx_flat']<=asset['normalized_notional']['funding_brl_2500'] for s in asset['cost_sensitivity'])
results['decision']='DO_NOT_DEEPEN_PASSIVE_BTC_ETH_CARRY_UNDER_THIS_CAPITAL_AND_BENCHMARK'
results['limitations']=['Historical rates are not forecasts','Zero-cost N=C scenario is a favorable normalized comparison, not a deployable structure or universal upper bound','Operator benchmark, taxes, realized friction and collateral efficiency remain unknown','No alternative assets or timing rules searched after results']
(DATA/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
for symbol,a in results['assets'].items():
    print(symbol,json.dumps({'normalized':a['normalized_notional'],'fixed_quantity':a['fixed_quantity'],
                             'fx_breakeven':a['fx_appreciation_needed_to_match_benchmark_pre_tax']},ensure_ascii=False))
print('ALL_DATA_AND_ACCOUNTING_CHECKS_PASS')
