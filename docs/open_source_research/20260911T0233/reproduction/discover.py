import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'external'
OUT.mkdir(exist_ok=True)
REPOS = '''freqtrade/freqtrade|framework|leakage e seleção
hummingbot/hummingbot|framework|market making e execução
nautechsystems/nautilus_trader|framework|engine orientado a eventos
jesse-ai/jesse|framework|backtest e estratégias
ccxt/ccxt|library|contratos e conectores
polakowo/vectorbt|library|simulação vetorizada
nkaz001/hftbacktest|framework|fila e latência
bmoscon/cryptofeed|library|feeds de microestrutura
DefiLlama/yield-server|data_source|decomposição de rendimentos
aave/aave-v3-core|reference_implementation|índices lending
Uniswap/v3-core|reference_implementation|liquidez concentrada
Uniswap/v4-core|reference_implementation|pools hooks e taxas
compound-finance/comet|reference_implementation|lending e colateral
lidofinance/core|reference_implementation|staking e saídas
morpho-org/morpho-blue|reference_implementation|lending isolado
coinmetrics/api-client-python|library|dados de rede e mercado
blockchain-etl/ethereum-etl|tool|extração on-chain
graphprotocol/graph-node|tool|indexação on-chain
DefiLlama/DefiLlama-Adapters|data_source|TVL e protocolos
binance/binance-public-data|dataset|arquivos históricos
quantopian/alphalens|library|fatores e ranking
stefan-jansen/alphalens-reloaded|library|fatores e ranking
stefan-jansen/zipline-reloaded|framework|calendários e backtest
hudson-and-thames/mlfinlab|library|validação financeira
bashtage/arch|library|bootstrap temporal SPA e volatilidade
statsmodels/statsmodels|library|cointegração e modelos de estado
scikit-learn/scikit-learn|library|pipelines e baselines
skfolio/skfolio|library|portfólio e validação
robertmartin8/PyPortfolioOpt|library|otimização e risco
dcajasn/Riskfolio-Lib|library|risco e carteiras
optuna/optuna|framework|registro de otimização
SeldonIO/alibi-detect|library|drift e anomalias
deepcharles/ruptures|library|quebras estruturais
scikit-learn-contrib/MAPIE|library|incerteza conformal
Nixtla/statsforecast|library|baselines temporais
Nixtla/neuralforecast|library|redes temporais
sktime/sktime|framework|avaliação temporal
AI4Finance-Foundation/FinRL|framework|reinforcement learning
lballabio/QuantLib|library|opções e curvas
gerrymanoim/exchange_calendars|library|calendários
'''

def fetch(url, dest):
    started = dt.datetime.now(dt.UTC).isoformat()
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'CriptoResearchAudit/1.0','Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read(3_000_001)
            if len(data)>3_000_000: raise ValueError('response size limit')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return {'url':url,'path':str(dest),'status':response.status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'observed_at':started}
    except Exception as e:
        return {'url':url,'status':'UNAVAILABLE','error':type(e).__name__+': '+str(e),'observed_at':started}

def survey(item):
    i, row = item
    repo, typ, capability = row.split('|')
    receipt=fetch('https://api.github.com/repos/'+repo,OUT/(repo.replace('/','__')+'.json'))
    result={'id':f'R{i:02d}','repository':repo,'url':'https://github.com/'+repo,'type':typ,'capability':capability,'receipt':receipt,'C':'C0','E':[],'result':'NOT_EVALUATED'}
    if receipt['status']==200:
        meta=json.loads(pathlib.Path(receipt['path']).read_text(encoding='utf-8'))
        result.update({k:meta.get(k) for k in ('default_branch','pushed_at','archived','disabled','open_issues_count','description')})
        result['license']=(meta.get('license') or {}).get('spdx_id','UNKNOWN')
    return result

if __name__=='__main__':
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(survey,enumerate(REPOS.strip().splitlines(),1)))
    (ROOT/'candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'candidates':len(rows),'verified_metadata':sum(x['receipt']['status']==200 for x in rows),'errors':[(r['repository'],r['receipt'].get('error')) for r in rows if r['receipt']['status']!=200]},ensure_ascii=False))
