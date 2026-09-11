import pathlib,json,gzip,hashlib,subprocess,datetime
P=pathlib.Path; ROOT=P(__file__).resolve().parents[1]; REPO=P('C:/Cripto/pesquisa-20260909'); OLD=ROOT.parent/'phase2'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x): (ROOT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
selected=[]; refs=set()
def add(id,p,kind,meta=None):
 selected.append(dict(id=id,path=str(p),kind=kind,metadata=meta));refs.add(p)
 if meta:refs.add(P(meta))
alt=P('C:/Cripto/restaurado-20260908/sessoes/20260907-altcoins/work/altcoin-retro-data/raw')
metas=[(p,read(p)) for p in sorted(alt.glob('*.json'))]
for sym in ['BTCUSDT','ETHUSDT','FTTUSDT','WBETHUSDT','USDPUSDT','TUSDUSDT','FDUSDUSDT']:
 hits=[(p,m) for p,m in metas if 'symbol='+sym+'&' in m.get('url','') and m.get('http_status')==200]
 if hits:
  p,m=hits[0];add('spot_'+sym,p.with_suffix('.bin.gz'),'klines',str(p))
basis=P('C:/Cripto/operacao/dados/basis-recovered-20260909/raw')
bm=[(p,read(p)) for p in sorted(basis.glob('*.json'))]
for name,needle in [('perp_trade','/klines?symbol=BTCUSDT&'),('perp_mark','/markPriceKlines?symbol=BTCUSDT&'),('future_trade','/klines?symbol=BTCUSDT_261225&'),('future_mark','/markPriceKlines?symbol=BTCUSDT_261225&'),('funding','/fundingRate?')]:
 hits=[(p,m) for p,m in bm if needle in m.get('url','') and m.get('status')==200]
 if hits:
  p,m=hits[0];add(name,p.with_suffix('.bin.gz'),'funding' if name=='funding' else 'klines',str(p))
diag=P('C:/Cripto/restaurado-20260908/sessoes/20260907-pesquisa/work/btc-execution-diagnostic-v1')
refs.add(diag/'diagnostic.json')
for name in ['spot_info','future_info','spot_00','future_00']:
 p=diag/'raw'/(name+'.bin.gz')
 if p.exists():add(name,p,'exchangeInfo' if 'info' in name else 'depth',str(diag/'diagnostic.json'))
aave=REPO/'docs/evidence/aave_validation_20260910/history'
ar=[(p,read(p)) for p in sorted((aave/'raw').glob('*.json'))]
for method in ['eth_chainId','web3_sha3','eth_call']:
 hits=[(p,m) for p,m in ar if m['request']['method']==method]
 # Multiple distinct call selectors, no outcome selection.
 seen=set()
 for p,m in hits:
  key=m['request']['params'][0].get('data','')[:10] if method=='eth_call' else method
  if key in seen:continue
  seen.add(key);add('aave_'+p.stem,p,'rpc')
  if len(seen)>=5:break
for n in ['002','004'] :add('aave_block_'+n,aave/'raw'/(n+'.json'),'rpc')
for n in ['protocol.json','executed.source','month-00.json']:refs.add(aave/n)
gap=P('C:/Cripto/operacao/dados/altcoin-gap-probes-20260909')
add('empty_FTT',gap/'FTTUSDT.response.gz','empty',str(gap/'FTTUSDT.metadata.json'))
identity=P('C:/Cripto/restaurado-20260908/sessoes/20260907-altcoins/work/altcoin-retro-package/docs/evidence/altcoin_payoff_20260907/identity_events.json')
add('late_identity_mapping',identity,'mapping')
protected=set(refs)
for p in ROOT.parent.rglob('*'):
 if p.is_file() and ROOT not in p.parents and '__pycache__' not in p.parts:protected.add(p)
for n in ['docs/NEXT_CHAT_PROMPT.md','charters/scientific_state.json','GarimpoInvestimentos/trials.json','uv.lock']:protected.add(REPO/n)
protected.update(REPO.glob('scripts/*.py'))
write('BASELINE.json',dict(registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),adapter_version='F01 v2',adapter_path=str(OLD/'work/experiments.py'),adapter_sha256=sha(OLD/'work/experiments.py'),read_only_hashes={str(p):sha(p) for p in sorted(protected)},sample=selected,allowed_new_paths=[str(ROOT),str(REPO/'docs/open_source_research/20260911T0233/phase3')],unavailable_sample_classes=['coin-margined receipt not found in bounded selected archives','OI and index-price not in selected receipts; no external collection','true economic revision not established; repeated block requests included']))
write('PROTOCOL.json',dict(mission='F01-real identity only',registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),first_battery='Unmodified phase2 Instrument/Observation: assess representability and semantic round-trip; no invented missing fields',sample_rule='First lexicographic successful metadata match by declared instrument/endpoint, first unique RPC selectors; includes empty and retrospective mapping',lossless=['all 23 identity/status fields','original values including lexical decimals','receipt physical and decompressed hashes','source locator','known clocks','observed content version','semantic type'],adversarial=['A symbol','B unit','C settlement','D price type','E future version','F chain/contract','G nonfinite/decimals/hash','H missing metadata'],success='Every supported case lossless; every required adversary rejected; no silent inference; all baseline hashes unchanged',rejection='Any semantic loss or unsupported join admitted',inconclusion='Missing metadata remains UNKNOWN; cannot certify full economic identity',network_calls=0,capital_permission=False))
print(json.dumps({'cases':len(selected),'sample':selected},indent=2))

