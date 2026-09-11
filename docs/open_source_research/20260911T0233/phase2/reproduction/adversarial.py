import sys,pathlib,json,hashlib,datetime
import experiments as e
r=pathlib.Path(__file__).resolve().parents[1]
b=e.Instrument('venueA','spot','BTC','USD','USD','N/A','BTC/USD','N/A','1','spot','BTC','USD/BTC')
inverse=e.replace(b,market='perpetual',payoff='inverse',settlement_asset='BTC',quantity_unit='USD_contract')
o=e.Observation(b,10,11,11,'100','a'*64)
tests=[('wrong price unit',lambda:e.replace(b,price_unit='USDT/BTC')),('inverse settlement',lambda:e.replace(inverse,settlement_asset='USD')),('spot quantity unit',lambda:e.replace(b,quantity_unit='USD')),('nonhex receipt',lambda:e.replace(o,receipt_hash='z'*64)),('ambiguous revision',lambda:e.asof([o,e.replace(o,value='99',receipt_hash='b'*64)],b,12)),('NaN amount',lambda:e.convert('NaN','USD','USD',None,12))]
checks=[{'case':name,'rejected':e.reject(fn)} for name,fn in tests]
out={'registered_protocol_sha256':e.sha(r/'ADVERSARIAL_PROTOCOL.json'),'implementation_sha256':e.sha(pathlib.Path(e.__file__)),'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'checks':checks,'passed':all(x['rejected'] for x in checks),'original_F01':e.f01()}
with (r/sys.argv[1]).open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(json.dumps({'checks':checks,'passed':out['passed'],'original_F01_passed':out['original_F01']['passed']}))
