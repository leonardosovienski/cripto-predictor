import argparse
import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime, timezone
from pathlib import Path

work=Path(__file__).resolve().parent
repo=work/'cripto-v1.2'
out=work.parent/'outputs'
data=work/'altcoin-forward-data'
evidence=repo/'docs/evidence/altcoin_forward_20260907'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo,text=True).strip()

def stage():
 audit=json.loads((data/'audit.json').read_text())
 config=tomllib.loads(Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml').read_text())
 assert config['status']=='ACTIVE' and config['target_thread_id']=='01a07d06-406f-7781-adad-0d0ea3ae9424'
 automation={'id':config['id'],'name':config['name'],'status':config['status'],'kind':config['kind'],'local_timezone':'America/Sao_Paulo','schedule':'Domingos às 21h; primeiro registro em 13/09/2026; última saída prevista em 06/12/2026.','local_runtime_required':True,'notification_intent':'Somente mudança relevante, conclusão, falha ou informação necessária.','policy_after_last_outcome':'Pausar após o balanço final.'}
 validation={'tests_passed':44,'tests_command':'pytest -q tests/test_altcoin_forward.py tests/test_altcoin_payoff.py tests/test_altcoin_analogs.py tests/test_freeze_h6_definition.py','ruff':'PASS','pyright':'PASS with local .venv Python','offline_replay':json.loads((data/'replay_validation.json').read_text()),'raw_response_hashes_verified':audit['raw_responses_verified'],'ledger_chain':'PASS','original_feature_score_parity':'13 of 13 identical features and scores; differences exactly zero','before_first_slot_tick':'PASS, zero prospective decisions, no quotes acquired and no added ledger rows','frozen_state_costs_trials_unchanged':'git diff --exit-code 9e492f0 HEAD for five frozen files passed','formal_attestation':False}
 for file in ('audit.json','design.json','replay_validation.json','status.json'):
  shutil.copyfile(data/file,evidence/file)
 dump(evidence/'automation.json',automation)
 dump(evidence/'validation.json',validation)
 sources={'checked_on':'2026-09-07','market_data_only_documentation':'https://developers.binance.com/en/docs/products/spot/faqs/market_data_only','commission_documentation':'https://developers.binance.com/en/docs/products/spot/faqs/commission_faq','codex_local_automation_documentation':'https://learn.chatgpt.com/docs/automations?surface=app','market_data_base':'https://data-api.binance.vision/api/v3/','announcement_catalogs':[{'catalog_id':i,'url':f'https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=50&catalogId={i}'} for i in (161,49)],'provenance':'All 275 raw responses and actual requested_at/known_at/source hashes are in forward-data/raw in the reproduction package; additional initial connectivity probes are preserved separately.'}
 dump(evidence/'sources.json',sources)
 search_log={'prior_history_reference':'docs/evidence/altcoin_payoff_20260907/search_log.json','new_id':'discovery-altcoin-forward-20260907-v3','changes':'Read-only observer and declared current investability/stablecoin exclusion; no new historical model-performance trial. Model v2 unchanged.','new_historical_performance_trials':0,'new_real_market_prospective_decisions':0,'synthetic_controls':'Stipulated 100 null replicates, two candidate queries each; zero qualifications; known-pattern positive/negative and censored-case controls pass. No general null calibration claim.','preflight_protocol_commit':'c80f309','initial_code_freeze_commit':'cbe5229','catalog_diff_commit':'9ca6648','status':'OBSERVER_SCHEDULED; NO_EXECUTABLE_PROMOTION'}
 dump(evidence/'search_log.json',search_log)
 result={'created_at':datetime.now(timezone.utc).isoformat(),'audit':audit,'validation':validation,'automation':automation,'design':json.loads((data/'design.json').read_text()),'status':json.loads((data/'status.json').read_text())}
 dump(out/'CRIPTO_PROXIMOS_PASSOS.json',result)
 report='''# Acompanhamento de cripto — ponto atual

**A preparação técnica foi executada e o acompanhamento semanal está agendado. Ainda não há lucro demonstrado nem operação com dinheiro real.**

| Etapa | Situação |
|---|---|
| Corrigir trocas de nome/unidade das moedas | 10 dos 13 casos anteriores reconstruídos. BTT, CVP e VIDT continuam sem saída verificável no prazo original. |
| Conferir dados atuais | 240 moedas na amostra; 160 pares ativos após exclusões; 13 passaram pelos filtros de dados e liquidez. |
| Registrar avisos oficiais | 428 avisos do catálogo de deslistagem e 4.404 do catálogo de notícias: paginação conferida. A interpretação completa dos eventos ainda não foi certificada. |
| Medir custos de tela | Ofertas de compra/venda e profundidade coletadas. Taxas da conta, conversão para reais e tributação continuam desconhecidas. |
| Testar o registrador | 44 testes passaram; reprodução com respostas gravadas reproduziu o cálculo sem acessar a internet. |
| Observar decisões antes dos resultados | Agendado. Primeira janela: **13/09/2026, domingo, às 21h de Brasília**. |
| Demonstrar lucro e liberar execução | Pendente. Depende de evidência futura, custos reais, eventos e critérios formais. |

**Resultado de hoje:** nenhuma das 13 moedas passou pela regra. Na simulação de referência, a alocação fica inteiramente em caixa USDT. Isso não significa converter seu dinheiro para USDT; nenhuma transação foi feita.

O acompanhamento observará 12 janelas semanais. A primeira saída será observada em 20/09 às 21h, se a primeira entrada tiver sido registrada. A última saída está prevista para 06/12 às 21h. A regra não será modificada só porque ficou sem candidatas ou perdeu. As decisões serão gravadas antes das cotações de entrada; falhas e preços ausentes permanecerão registrados.

**O computador precisa estar ligado e o aplicativo aberto nas janelas**, pois a execução usa arquivos locais. Se uma janela for perdida, ela não será reconstruída como se tivesse sido observada a tempo. O acompanhamento avisará quando houver mudança relevante, falha, conclusão ou necessidade de informação. [Documentação oficial](https://learn.chatgpt.com/docs/automations?surface=app).

Na fotografia das ofertas, uma compra e venda hipotéticas imediatas de US$ 1.000 custariam entre aproximadamente **US$ 2,14 e US$ 5,57**, incluindo uma taxa **suposta** de 0,10% em cada operação. Não são negócios executados nem custos futuros garantidos. A taxa real depende da conta e do par. [Documentação de comissões da Binance](https://developers.binance.com/en/docs/products/spot/faqs/commission_faq).

Para fechar a comparação econômica pessoal, ainda faltam corretora/conta pretendida e investimento de referência. Por enquanto, Binance e o cenário Selic já documentado são apenas referências de pesquisa. USDT não é caixa sem risco em reais; variação cambial não será tratada como vantagem da seleção.

As 12 semanas servem para testar o funcionamento e acumular observações novas. **Não prometem que haverá lucro nem que esse prazo será suficiente para comprová-lo.** A análise de tamanho de amostra depende de vantagem mínima, oscilação dos resultados e dependência entre semanas, ainda não medidos para este modelo.
'''
 (out/'ACOMPANHAMENTO_CRIPTO.md').write_text(report,encoding='utf-8')
 hypothesis='''

### 2026-09-07 — Altcoin forward observation pilot v3

User authorized the remaining preparation and forward observation steps. Protocol c80f309 and recorder freeze cbe5229 precede the live preflight; 9ca6648 adds catalog status diffs before any prospective decisions. Fixed v2 net-payoff scorer and training geometry remain unchanged. Current investability excludes verified RLUSD category contamination prospectively only; no resampling, historical performance search or prior-evidence rewrite.

Live preflight: 275 preserved public responses; 160 of the 240 sampled symbols currently trading after exclusions, 13 eligible, zero qualifying. Features and scores for all 13 exactly match the consumed September 7 snapshot. All 428 delisting and 4404 news catalog headlines retrieved with matching pagination counts; interpreted event completeness remains UNKNOWN. Visible-book hypothetical immediate roundtrip at 1000 USDT ranges 21.4276–55.7413 bps including ASSUMED 10bps fees each side. These are quote marks, not fills or verified account economics.

Forty-four targeted tests, Ruff and Pyright pass; offline snapshot replay matches apart from its new execution timestamp. Full-geometry synthetic known-pattern controls and censoring guard pass; zero qualifications in 200 stipulated-null queries do not certify general false-positive rates. Normal-design power sensitivity is conditional, not a Core model-specific attestation.

Weekly local Codex heartbeat scheduled from September 13, 21:00 America/Sao_Paulo, for a bounded 12-entry-slot observer and final due observation December 6, 21:00. No prospective decisions or matured outcomes exist at registration. Decisions are durable before entry quotes; missed slots/outcomes remain censored; no retuning. This explicitly separate observation pilot does not pass executable readiness or G1-G7. Exact account fees, attainable operator benchmark, full events, execution parity and formal attestation remain unresolved. Frozen state/trials/costs, production, funding/OI/HMM and capital unchanged.
'''
 with (repo/'docs/HYPOTHESES.md').open('a',encoding='utf-8') as stream:stream.write(hypothesis)
 print(json.dumps({'staged_evidence':str(evidence),'report':str(out/'ACOMPANHAMENTO_CRIPTO.md'),'automation':automation},ensure_ascii=False))

def package():
 head=git('rev-parse','HEAD')
 patch=subprocess.check_output(['git','diff','--binary','9e492f0',head],cwd=repo)
 (out/'CRIPTO_ACOMPANHAMENTO.patch').write_bytes(patch)
 subprocess.run(['git','apply','--reverse','--check',str(out/'CRIPTO_ACOMPANHAMENTO.patch')],cwd=repo,check=True)
 package=out/'CRIPTO_ACOMPANHAMENTO_REPRODUCAO.zip'
 files={}
 for name in ('observe_altcoin_forward.py','check_altcoin_forward_design.py','prepare_altcoin_payoff.py','research_altcoin_analogs.py','collect_altcoin_analogs.py','__init__.py'):
  files['scripts/'+name]=repo/'scripts'/name
 for name in ('test_altcoin_forward.py','test_altcoin_payoff.py','test_altcoin_analogs.py'):
  files['tests/'+name]=repo/'tests'/name
 for p in evidence.iterdir():
  if p.is_file():files['docs/evidence/altcoin_forward_20260907/'+p.name]=p
 for parent in ('altcoin_analogs_20260907','altcoin_payoff_20260907'):
  files[f'docs/evidence/{parent}/protocol.json']=repo/f'docs/evidence/{parent}/protocol.json'
 files['base-data/acquisition.json']=work/'altcoin-data/acquisition.json'
 files['training/samples_identity_corrected.json.gz']=work/'altcoin-payoff-results/samples_identity_corrected.json.gz'
 for p in data.rglob('*'):
  if p.is_file() and p.name!='observer.lock':files['forward-data/'+p.relative_to(data).as_posix()]=p
 for p in (work/'altcoin-forward-probes').glob('*'):
  files['initial-probes/'+p.name]=p
 files['ACOMPANHAMENTO_CRIPTO.md']=out/'ACOMPANHAMENTO_CRIPTO.md'
 replay=(work/'replay_forward.py').read_text().replace("repo=Path(__file__).resolve().parent/'cripto-v1.2'","repo=Path(__file__).resolve().parent").replace("data=repo.parent/'altcoin-forward-data'","data=repo/'forward-data'").replace("repo.parent/'altcoin-data'","repo/'base-data'").replace("repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz'","repo/'training/samples_identity_corrected.json.gz'")
 readme='''# Reprodução do piloto de observação

Este pacote reproduz o diagnóstico coletado em 07/09 e seus controles sem baixar preços novos. O artefato de treino reparado está incluído, com hash; a auditoria completa de sua formação continua nos pacotes ALTCOINS_REPRODUCAO e CRIPTO_CONTINUACAO_REPRODUCAO anteriores.

Python 3.13. Dependências em requirements.txt. Na pasta extraída:

```
python REPRODUZIR.py
python -m scripts.check_altcoin_forward_design --output design-reproduzido.json
python -m pytest -q tests
```

REPRODUZIR.py permite apenas respostas existentes no cache, verifica hashes e exige igualdade de todo o snapshot, exceto recorded_after_acquisition, que registra a nova execução. Os 39 testes deste pacote cobrem analogia, payoff e observador. No repositório também passaram cinco testes do congelamento, total 44.

Os registros da coleta original e seus caminhos de origem são preservados. Não executar tick sobre uma cópia do livro como se ela fosse o monitor ativo. O monitor ativo usa a pasta de trabalho original descrita no RUNBOOK, e somente ele deve escrever no livro. Não há execução de ordens neste código.

Todos os arquivos fornecidos constam de FILE_HASHES.json. O programa antigo que gravou o preflight é rastreado pelo commit cbe5229 e freeze_preflight.json; freeze.json corresponde ao observador com registro de alterações do catálogo, anterior à primeira decisão futura. O modelo e os preços do diagnóstico não foram modificados.
'''
 requirements='httpx==0.28.1\nnumpy==2.5.1\nscikit-learn==1.9.0\nscipy==1.18.0\njoblib==1.5.3\nthreadpoolctl==3.6.0\npytest==8.4.2\n'
 additions={'REPRODUZIR.py':replay.encode(),'README.md':readme.encode(),'requirements.txt':requirements.encode()}
 hashes={name:sha(path) for name,path in files.items()}
 hashes.update({name:hashlib.sha256(blob).hexdigest() for name,blob in additions.items()})
 with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,path in sorted(files.items()):z.write(path,name)
  for name,blob in additions.items():z.writestr(name,blob)
  z.writestr('FILE_HASHES.json',json.dumps(hashes,indent=2))
 with zipfile.ZipFile(package) as z:
  assert z.testzip() is None
  for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
 manifest={'created_at':datetime.now(timezone.utc).isoformat(),'repository_head':head,'base_commit':'9e492f07f05b161beaed3cb7d343ff97011d5c14','branch':git('branch','--show-current'),'artifacts':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in (out/'ACOMPANHAMENTO_CRIPTO.md',out/'CRIPTO_PROXIMOS_PASSOS.json',out/'CRIPTO_ACOMPANHAMENTO.patch',package)},'zip_files':len(hashes)+1,'zip_internal_hash_check':'PASS','reverse_patch_check':'PASS','automation_id':'observar-altcoins-semanalmente','formal_profitability_proof':False,'real_capital':False}
 dump(out/'CRIPTO_ACOMPANHAMENTO_MANIFESTO.json',manifest)
 print(json.dumps(manifest,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('mode',choices=('stage','package'))
 args=p.parse_args()
 stage() if args.mode=='stage' else package()
