import pathlib,json,hashlib,datetime,subprocess
P=pathlib.Path;R=P(__file__).resolve().parents[1];OLD=R.parent/'phase3';REPO=P('C:/Cripto/pesquisa-20260909')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
diag=P('C:/Cripto/restaurado-20260908/sessoes/20260907-pesquisa/work/btc-execution-diagnostic-v1')
probe=diag.parent/'basis-capability-probe';stage=diag.parent/'basis-delivery-stage';evidence=REPO/'docs/evidence/basis_research_20260908'
paths=set(P(p) for p in read(OLD/'BASELINE.json')['read_only_hashes'])
paths.update(p for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
selected=set([diag/'diagnostic.json',stage/'scripts/diagnose_btc_execution.py',REPO/'scripts/diagnose_btc_execution.py',REPO/'scripts/basis_data.py'])
selected.update(diag.glob('raw/*.bin.gz'))
selected.update(probe.glob('*'))
selected.update(evidence/n for n in ['data_semantics.json','implementation_freeze_v1.json','data_archives.json','protocol.json'])
paths.update(p for p in selected if p.is_file())
baseline={'initiative':'20260911T0233','phase':'3B','registered_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'parent':str(OLD),'protected_hashes':{str(p):sha(p) for p in sorted(paths)},'additional_inputs':[str(p) for p in sorted(selected) if p.is_file()],'scope':'BTCUSDT spot/perpetual; BTCUSDT_261225; 12 saved book pairs; saved capability README and exchangeInfo; no outcome calculation','new_paths':[str(R),str(REPO/'docs/open_source_research/20260911T0233/phase3b')],'stop_rule':'Precise blockers or exhaustion of these saved specification/clock artifacts; no search for new strategies or external collection'}
protocol={'registered_at':baseline['registered_at'],'version':'F01-contract-temporal v3B.1','hypothesis':'Saved bundle suffices for some economic/temporal gates; unknown fields must not be inferred','contract_fields':'venue market_type base_asset quote_asset settlement_asset margin_asset quantity_unit price_unit multiplier linear_inverse payoff expiry price_type funding_semantics contract_version valid_from valid_until'.split(),'clock_fields':'SOURCE_EVENT_TIME SOURCE_PUBLICATION_TIME SOURCE_RESPONSE_TIME LOCAL_REQUEST_TIME LOCAL_RECEIPT_TIME INGESTION_TIME NORMALIZATION_TIME'.split(),'state_separation':['OBSERVED in local clock','EVENT_OCCURRED with source-clock uncertainty','ECONOMICALLY_ELIGIBLE only with complete scoped economic, historical, availability evidence'],'economic_negative_controls':['wrong currency','base versus contract quantity','wrong multiplier','settlement mismatch','margin versus PnL currency','linear/inverse','trade/mark','mark/executable'],'positive_controls':'Explicit symbol/base/quote/contractType/deliveryDate extraction and preserved-source provenance; algebra on declared synthetic units only','unknown_controls':'Missing terms stay unknown; max(event,receipt) is never sufficient for economic eligibility','gates':['READY','PARTIALLY_READY','BLOCKED_CURRENT_EVIDENCE','STRUCTURALLY_UNRECOVERABLE_FOR_SCOPE'],'no_network':True,'capital_permission':False,'no_economic_replay':True}
for n,x in [('BASELINE.json',baseline),('PROTOCOL.json',protocol)]:
 with (R/n).open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,ensure_ascii=False)
print('Protected files',len(paths),'additional scoped inputs',len(selected))
