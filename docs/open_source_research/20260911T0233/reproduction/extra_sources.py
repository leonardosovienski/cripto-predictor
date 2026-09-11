import concurrent.futures as cf
import json
import pathlib
from discover import ROOT, OUT, fetch
SOURCES='''Crypto carry|paper|https://www.bis.org/publ/work1087.htm|carry e segmentação
Common Risk Factors in Cryptocurrency|paper|https://www.nber.org/papers/w25882|ranking fatores mercado tamanho momentum
Model selection bias|paper|https://jmlr.org/papers/v11/cawley10a.html|validação aninhada
Loss versus rebalancing|paper|https://arxiv.org/abs/2208.06046|LP e seleção adversa
Binance funding history|data_source|https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History|funding liquidado
Deribit API|data_source|https://docs.deribit.com/|opções IV Greeks books
Glassnode API|data_source|https://docs.glassnode.com/|on-chain entidades e revisões
Coin Metrics Community|dataset|https://docs.coinmetrics.io/|métricas de rede e mercado
Dune documentation|tool|https://docs.dune.com/|SQL e indexação on-chain
ALFRED real time|data_source|https://fred.stlouisfed.org/docs/api/fred/realtime_period.html|vintages macro
Lido withdrawals|reference_implementation|https://docs.lido.fi/contracts/withdrawal-queue-erc721/|fila de resgates staking
SciPy Spearman|library|https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html|verificação diferencial de ranking
DefiLlama unlocks|data_source|https://defillama.com/unlocks|eventos e emissão
'''
def entry(arg):
    i,row=arg
    name,typ,url,cap=row.split('|')
    receipt=fetch(url,OUT/f'R{i:02d}.html')
    return {'id':f'R{i:02d}','name':name,'type':typ,'url':url,'capability':cap,'receipt':receipt,'C':'C0','E':[],'result':'NOT_EVALUATED','license':'UNKNOWN','version':'web observed '+receipt['observed_at'],'evidence_limit':'Public documentation only; service access and historical data not acquired.'}
with cf.ThreadPoolExecutor(max_workers=3) as pool:
    rows=list(pool.map(entry,enumerate(SOURCES.strip().splitlines(),41)))
(ROOT/'extra_candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([(x['id'],x['name'],x['receipt']['status']) for x in rows]))
