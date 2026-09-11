import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import random
import socket
import sys
import time
import warnings

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=pathlib.Path('C:/Cripto/pesquisa-20260909')
# Set isolated paths before project imports. No private dotenv, no market I/O.
scratch=ROOT/'work'/'isolated'
scratch.mkdir(exist_ok=True)
(scratch/'synthetic.env').write_text('# synthetic only\n',encoding='utf-8')
for name in list(os.environ):
    if any(x in name.upper() for x in ['KEY','TOKEN','SECRET','PASSWORD']):
        os.environ.pop(name,None)
os.environ['CRIPTO_ENV_FILE']=str(scratch/'synthetic.env')
for n in ['DATA','OUTPUT','CACHE','LOGS']:
    os.environ[n+'_DIR']=os.environ['GARIMPO_'+n+'_DIR']=str(scratch/n.lower())
os.environ['PREDICTOR_OPS_STATE_DIR']=str(scratch/'state')
os.environ['PREDICTOR_EVENTS_PATH']=str(scratch/'events.jsonl')
os.environ['GEMINI_API_KEY']='synthetic-benchmark-gemini-only'
os.environ['SERP_API_KEY']='synthetic-benchmark-serpapi-only'
def denied(*a,**kw): raise RuntimeError('Network forbidden in synthetic benchmark')
socket.socket.connect=denied
socket.create_connection=denied
sys.path.insert(0,str(REPO))
import numpy as np
from scipy.stats import spearmanr,rankdata
from GarimpoInvestimentos.analyzers.backtest import _spearman_rho,_ranks
from GarimpoInvestimentos.analyzers.indicators import sma,bollinger

t=time.perf_counter()
rng=random.Random(20260911)
cases=[]
for n in range(3,103):
    x=[rng.randrange(-5,6) for _ in range(n)]
    y=[rng.randrange(-5,6) for _ in range(n)]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        expected=float(spearmanr(x,y).statistic)
    actual=_spearman_rho(x,y)
    match=(actual is None and math.isnan(expected)) or (actual is not None and abs(actual-expected)<=1e-10)
    rank_error=max(abs(a-b) for a,b in zip(_ranks(x),rankdata(x)))
    cases.append({'n':n,'error':None if actual is None else abs(actual-expected),'match':bool(match and rank_error<=1e-10),'rank_error':float(rank_error)})
constant=_spearman_rho([1.0]*10,list(range(10)))
prices=[100+rng.uniform(-10,10) for _ in range(250)]
errors=[]
prefix_errors=[]
leak_detected=0
stream=np.convolve(np.array(prices),np.ones(20)/20,mode='valid')
for n in range(20,251):
    data=prices[:n]
    mid=float(np.mean(data[-20:]))
    sd=float(np.std(data[-20:],ddof=0))
    ref=(mid+2*sd,mid,mid-2*sd,(data[-1]-(mid-2*sd))/(4*sd))
    errors.append(max(abs(a-b) for a,b in zip(bollinger(data),ref)))
    errors.append(abs(sma(data,20)-mid))
    prefix_errors.append(abs(sma(data,20)-float(stream[n-20])))
    leak_detected+=abs(float(np.mean(prices))-float(np.mean(data)))>1e-10
result={'id':'B01-B02-20260911T0233','observed_at':dt.datetime.now(dt.UTC).isoformat(),'protocol_sha256':hashlib.sha256((ROOT/'BENCHMARK_PROTOCOL.json').read_bytes()).hexdigest(),'seed':20260911,'B01':{'cases':len(cases),'mismatches':sum(not c['match'] for c in cases),'max_error':max(c['error'] or 0 for c in cases),'constant_is_undefined':constant is None,'cases_detail':cases},'B02':{'prefixes':231,'max_reference_error':max(errors),'max_prefix_error':max(prefix_errors),'planted_future_mean_detected_at_prefixes':int(leak_detected)},'elapsed_seconds':time.perf_counter()-t,'scope':'synthetic engineering; no alpha, no statistical market validation; no throughput superiority claim'}
result['passed']=bool(all(c['match'] for c in cases) and constant is None and max(errors)<1e-10 and max(prefix_errors)<1e-10 and leak_detected>0)
(ROOT/'benchmark_result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='B01'}))
print(json.dumps({k:v for k,v in result['B01'].items() if k!='cases_detail'}))
raise SystemExit(0 if result['passed'] else 1)
