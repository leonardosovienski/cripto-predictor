import pathlib,json,datetime,hashlib,os,sys,socket,runpy,copy
from fractions import Fraction
from decimal import Decimal
root=pathlib.Path(__file__).resolve().parents[1]
repo=pathlib.Path('C:/Cripto/pesquisa-20260909')
sys.path.insert(0,str(repo))
runpy.run_path(str(repo/'tests/conftest.py'))
def deny(*a,**kw):raise RuntimeError('No network in engineering benchmark')
socket.socket.connect=deny
socket.create_connection=deny
from GarimpoInvestimentos.dpl.snapshots import serving_context
from scripts.diagnose_btc_execution import walk
from scripts.plan_btc_hedge_v2 import validate_book,net_hedge_plan
from sklearn.model_selection import TimeSeriesSplit
import numpy as np
protocol=json.loads((root/'EXTENDED_PROTOCOL.json').read_text())
assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in protocol['code_sha256'].items())
now=datetime.datetime(2026,9,11,12,tzinfo=datetime.UTC)
base={'symbol':'BTC','interval':'1d','source':'synthetic','candle_open':'2026-09-10T00:00:00+00:00','available_at':'2026-09-11T00:00:00+00:00','collected_at':'2026-09-11T01:00:00+00:00','features':{'price_usd':100}}
class Store:
    def __init__(self,s):self.s=s
    def latest_market_snapshot(self,*a):return self.s
mutations=[('valid',{}),('future availability',{'available_at':'2026-09-12T00:00:00+00:00'}),('future receipt',{'collected_at':'2026-09-12T01:00:00+00:00'}),('receipt before publication',{'collected_at':'2026-09-10T23:00:00+00:00'}),('not daily closed',{'candle_open':'2026-09-10T12:00:00+00:00'}),('stale >26h',{'candle_open':'2026-09-08T00:00:00+00:00','available_at':'2026-09-09T00:00:00+00:00'}),('different symbol',{'symbol':'ETH'}),('naive time',{'available_at':'2026-09-11T00:00:00'}),('nonpositive price',{'features':{'price_usd':0}})]
b03=[]
for name,changes in mutations:
    try:serving_context(Store(base|changes),'BTC',now=now);accepted=True
    except ValueError:accepted=False
    b03.append({'name':name,'accepted':accepted,'pass':accepted==(name=='valid')})
b04=[]
for name,levels,q,asc,expected in [('one level buy',[['100','2']],1,True,Fraction(100)),('two level buy',[['100','1'],['102','2']],2,True,Fraction(101)),('two level sell',[['100','1'],['98','2']],2,False,Fraction(99))]:
    value=walk(levels,q,asc);b04.append({'name':name,'actual':value,'exact':str(expected),'pass':abs(value-float(expected))<1e-10})
for name,fn in [('insufficient depth',lambda:walk([['100','1']],2,True)),('zero quantity',lambda:walk([['100','1']],0,True)),('unsorted',lambda:walk([['102','1'],['100','2']],2,True)),('crossed full book',lambda:validate_book({'bids':[['101','1']],'asks':[['100','1']]}))]:
    try:fn();rejected=False
    except ValueError:rejected=True
    b04.append({'name':name,'rejected':rejected,'pass':rejected})
ends=np.arange(30)+1;ends[5]=25
b05=[]
for train,test in TimeSeriesSplit(n_splits=3,test_size=5,gap=2).split(np.arange(30)):
    overlap=[int(i) for i in train if ends[i]>=test[0]]
    purged=[int(i) for i in train if ends[i]<test[0]]
    b05.append({'test_start':int(test[0]),'train':train.tolist(),'overlap_rows':overlap,'interval_purged_train':purged,'remaining_overlap':sum(int(ends[i]>=test[0]) for i in purged)})
f={'step':'.001','min_qty':'.001','max_qty':'100','min_notional':'1','status':'TRADING'}
spot={'bids':[['99','100']],'asks':[['100','100']]};future={'bids':[['101','100']],'asks':[['102','100']]}
plan=net_hedge_plan(spot,future,f,f,8)
d=lambda k:Decimal(plan[k])
ok=(d('net_received_btc')>=d('future_short_btc') and 0<=d('unhedged_dust_btc')<Decimal('.00100001') and d('spot_outlay_usdt')<=1250 and abs(d('spot_outlay_usdt')+d('future_entry_fee_usdt_assumed')+d('cash_reserve_usdt')-5000)<Decimal('1e-10'))
try:net_hedge_plan(spot,{'bids':[['101','.0001']],'asks':[['102','100']]},f,f,8);reject=False
except ValueError:reject=True
result={'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'protocol_sha256':hashlib.sha256((root/'EXTENDED_PROTOCOL.json').read_bytes()).hexdigest(),'B03':b03,'B04':b04,'B05':b05,'B06':{'plan':plan,'capital_and_net_checks':bool(ok),'insufficient_future_depth_rejected':reject},'scope':'C4 controlled synthetic correctness; no market profit or empirical partial-fill model','passed':all(r['pass'] for r in b03+b04) and any(r['overlap_rows'] for r in b05) and all(r['remaining_overlap']==0 for r in b05) and bool(ok) and reject}
(root/'extended_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
