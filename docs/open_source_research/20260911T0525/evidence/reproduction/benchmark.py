import pathlib,json,time,random,statistics,hashlib,sys
sys.dont_write_bytecode=True
from GarimpoInvestimentos.research.factors import analyze_panel
from GarimpoInvestimentos.research.universe import select_universe,Rule
from GarimpoInvestimentos.research.validation import LabelInterval,walk_forward
from GarimpoInvestimentos.research.__main__ import evaluate,demo_config,code_version
from GarimpoInvestimentos.research.registry import RunStore,encoded
R=pathlib.Path(__file__).resolve().parents[1];rng=random.Random(20260911)
panel=[{'date':d,'asset':str(i),'factor':rng.randrange(100),'label':rng.uniform(-.1,.1)} for d in range(20) for i in range(1000)]
universe=[{'instrument_id':str(i),'known_at':1,'active':i%4!=0,'volume':i,'volume_unit':'USD'} for i in range(10000)]
labels=[LabelInterval(i,i+(i%9),i+(i%9)+2) for i in range(10000)]
jobs=[('panel_20000_rows',lambda:analyze_panel(panel)),('universe_10000_rows',lambda:select_universe(universe,[Rule('active','eq',True)],cutoff=1,sort_field='volume',limit=100)),('interval_split_10000_rows_10_windows',lambda:walk_forward(labels,[(i,i+100) for i in range(1000,10000,900)])),('composed_demo',lambda:evaluate(demo_config()))]
out=[]
for name,fn in jobs:
 first=fn();samples=[]
 for _ in range(5):
  t=time.perf_counter();value=fn();samples.append(time.perf_counter()-t);assert value==first
 out.append({'name':name,'median_seconds':statistics.median(samples),'seconds':samples,'deterministic':True})
store=RunStore(R/'demo_runs');config=demo_config();result=evaluate(config)
for ident in ['integrated_demo','reproduced_demo']:
 store.create(config,{'outputs':len(result),'economic_validation':False},artifacts={'results':result},inputs={'config':hashlib.sha256(encoded(config)).hexdigest()},code_version=code_version(),run_id=ident)
assert (store.root/'integrated_demo/results.json').read_bytes()==(store.root/'reproduced_demo/results.json').read_bytes()
(R/'BENCHMARK.json').write_text(json.dumps({'seed':20260911,'timings':out,'comparison':store.compare('integrated_demo','reproduced_demo'),'limits':'Local warm timings, not speedup vs competitor or alpha. First implementation previously absent; no human-productivity multiplier estimated.'},indent=2))
print(json.dumps(out,indent=2))
