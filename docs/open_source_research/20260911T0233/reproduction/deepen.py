import concurrent.futures as cf
import json
import pathlib
import subprocess
from discover import ROOT, OUT, fetch

PATHS={
'freqtrade/freqtrade':['freqtrade/optimize/analysis/lookahead.py','tests/optimize/test_lookahead_analysis.py','docs/lookahead-analysis.md'],
'hummingbot/hummingbot':['hummingbot/strategy_v2/executors/arbitrage_executor/arbitrage_executor.py','test/hummingbot/strategy_v2/executors/arbitrage_executor/test_arbitrage_executor.py'],
'nautechsystems/nautilus_trader':['nautilus_trader/backtest/models/fill.pyx','tests/unit_tests/backtest/test_models.py'],
'ccxt/ccxt':['python/ccxt/base/exchange.py','wiki/Manual.md'],
'nkaz001/hftbacktest':['hftbacktest/src/backtest/models/queue.rs','hftbacktest/src/backtest/models/latency.rs'],
'bmoscon/cryptofeed':['cryptofeed/exchanges/binance.py','tests/unit/test_binance.py'],
'DefiLlama/yield-server':['src/adaptors/aave-v3/index.js','README.md'],
'aave/aave-v3-core':['contracts/protocol/libraries/logic/ReserveLogic.sol','contracts/protocol/libraries/math/MathUtils.sol','test-suites/math-utils.spec.ts'],
'Uniswap/v3-core':['contracts/libraries/SwapMath.sol','test/SwapMath.spec.ts'],
'bashtage/arch':['arch/bootstrap/multiple_comparison.py','arch/tests/bootstrap/test_multiple_comparison.py'],
'statsmodels/statsmodels':['statsmodels/tsa/stattools/_stattools.py','statsmodels/tsa/tests/test_stattools.py'],
'scikit-learn/scikit-learn':['sklearn/model_selection/_split.py','sklearn/model_selection/tests/test_split.py'],
'skfolio/skfolio':['src/skfolio/model_selection/_combinatorial.py','tests/test_model_selection/test_combinatorial.py'],
'lballabio/QuantLib':['ql/pricingengines/blackformula.cpp','test-suite/blackformula.cpp'],
'stefan-jansen/alphalens-reloaded':['src/alphalens/performance.py','tests/test_performance.py'],
}
def deep(row):
    repo=row['repository']
    if repo not in PATHS: return None
    branch=row['default_branch']
    try:
        raw=subprocess.check_output(['git','ls-remote',row['url']+'.git','refs/heads/'+branch],text=True,timeout=30)
        ref=raw.split()[0]
    except Exception: ref=branch
    records=[fetch('https://raw.githubusercontent.com/'+repo+'/'+ref+'/'+p,OUT/repo.replace('/','__')/p) for p in PATHS[repo]]
    return {'id':row['id'],'repository':repo,'ref':ref,'files':records,'review_status':'DOWNLOADED_NOT_YET_INSPECTED'}
if __name__=='__main__':
    rows=json.loads((ROOT/'candidates.json').read_text(encoding='utf-8'))
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        results=[x for x in pool.map(deep,rows) if x]
    (ROOT/'deep_sources.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'id':r['id'],'repo':r['repository'],'files':[(f['url'].split('/')[-1],f['status']) for f in r['files']]} for r in results]))
