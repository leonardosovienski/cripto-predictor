import argparse
import hashlib
import json
import shutil
import subprocess
import tomllib
import zipfile
from datetime import datetime,timezone
from pathlib import Path

work=Path(__file__).resolve().parent
repo=work/'cripto-v1.2'
data=work/'altcoin-profit-data'
out=work.parent/'outputs'
evidence=repo/'docs/evidence/altcoin_profit_20260907'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
git=lambda *args:subprocess.check_output(['git',*args],cwd=repo,text=True).strip()

def stage():
 for name in ('audit.json','planning.json','status.json'):
  shutil.copyfile(data/name,evidence/name)
 audit=json.loads((data/'audit.json').read_text())
 config=tomllib.loads(Path('C:/Users/Superleo13/.codex/automations/observar-altcoins-semanalmente/automation.toml').read_text(encoding='utf-8'))
 assert config['status']=='ACTIVE'
 assert "--data-dir '..\\altcoin-profit-data'" in config['prompt']
 assert "--evidence-dir 'docs\\evidence\\altcoin_profit_20260907'" in config['prompt']
 automation={'id':config['id'],'name':config['name'],'status':config['status'],'target_thread_id':config['target_thread_id'],'schedule_unchanged':'Domingos às 21h America/Sao_Paulo; primeira janela 13/09/2026.','objective':'Lucro líquido absoluto, sem comparação com outros investimentos.','current_profile':'altcoin_profit_20260907','current_data_directory':'work/altcoin-profit-data','notification_intent':'Somente mudança relevante, conclusão, falha ou informação necessária.'}
 dump(evidence/'automation.json',automation)
 search_log={'registered_protocol_commit':'330619f','code_and_freeze_before_new_preflight':'007432c','user_directed_change':'Absolute net profit and agent-selected research venue; no outside benchmark and no original 240-symbol cap.','new_historical_performance_trials':0,'prospective_decisions':0,'model_scorer_and_training_changes':0,'candidate_universe':'All current Binance spot USDT subject to declared exclusions and unchanged data/liquidity rules.','preflight_selected':audit['selected'],'scope_limit':'Other venues are allowed by user preference, but no other venue adapter is claimed.'}
 dump(evidence/'search_log.json',search_log)
 dump(out/'CRIPTO_LUCRO_ABSOLUTO.json',{'audit':audit,'automation':automation,'planning':json.loads((data/'planning.json').read_text()),'search_log':search_log})
 original_report=out/'ACOMPANHAMENTO_CRIPTO.md'
 shutil.copyfile(original_report,out/'ACOMPANHAMENTO_CRIPTO_V3_20260907.md')
 report='''# Cripto — foco em lucro líquido

**Objetivo confirmado: terminar com mais dinheiro do que começou, depois de todos os custos. Sem exigir superar Selic, Bitcoin ou qualquer outro investimento. Você não precisa escolher a corretora agora.**

A escolha de moedas e corretoras fica aberta para a pesquisa. A infraestrutura já implementada coleta Binance spot em USDT; isso não significa cobertura de todas as corretoras ou criptos do mundo.

## O que foi ajustado

- Retirada a exigência de uma referência de investimento e removidas as carteiras de comparação do acompanhamento futuro.
- Retirado o limite da amostra inicial de 240 moedas. Agora a busca percorre todos os pares Binance spot/USDT atualmente negociáveis, com as exclusões declaradas e os mesmos filtros de dados e liquidez.
- Mantida a regra de considerar ganhos, perdas e custos, sem forçar uma entrada quando o cálculo não oferece margem positiva.
- Atualizado o acompanhamento existente para essa configuração. Evidências anteriores foram preservadas.

## Resultado da busca ampliada em 07/09/2026

| Verificação | Resultado |
|---|---:|
| Pares spot/USDT ativos no catálogo | 487 |
| Pares após as exclusões declaradas | 472 |
| Pares com dados e liquidez suficientes | 44 |
| Pares aprovados pela regra atual | **0** |
| Testes de software aprovados | 46 |

Portanto, o diagnóstico atual continua sem entrada simulada. A retirada da comparação com Selic não transforma uma previsão desfavorável em lucro. Nenhuma ordem foi enviada e nenhum dinheiro foi movimentado.

## Como será acompanhado

Primeira janela em **13/09/2026 às 21h de Brasília**; primeiro resultado semanal possível em 20/09 às 21h. São 12 janelas previstas, com última saída em 06/12 às 21h. O computador precisa estar ligado e o aplicativo aberto. Decisões são registradas antes das cotações de entrada; uma janela perdida não será reconstruída como observada a tempo. O acompanhamento avisará quando houver mudança relevante, falha ou conclusão.

As marcas de preços em USDT usam hipóteses explícitas de custos. Taxas de conta, conversão e impostos desconhecidos não serão tratados como zero, e uma marca positiva em USDT não será apresentada como lucro líquido confirmado em reais. A documentação da Binance descreve comissões específicas por conta/par. [Fonte oficial](https://developers.binance.com/en/docs/products/spot/faqs/commission_faq).

As 12 semanas fornecem observações novas e testam a operação do registrador. **Ainda não há lucro demonstrado nem prazo garantido para obtê-lo.**
'''
 original_report.write_text(report,encoding='utf-8')
 with (repo/'docs/HYPOTHESES.md').open('a',encoding='utf-8') as stream:
  stream.write('''

### 2026-09-07 — User-defined absolute-profit scope v4

User explicitly rejects comparison to any other investment and delegates the choice of research venue/crypto. This instruction replaces prior external-benchmark requirements for the user's objective. Protocol 330619f and code freeze 007432c precede a new full-current-universe diagnostic. The existing weekly automation is updated, not duplicated, with the same schedule and notification intent.

All-current Binance spot USDT scope: 487 current catalog pairs, 472 after declared exclusions, 44 eligible delayed/liquid histories and zero qualifying selections. No original 240-symbol cap; BTC may be a candidate and remains a model input, but no comparison portfolios are recorded in v4. The trained geometry/payoff scorer is unchanged. Other venues are allowed by preference but not implemented by this adapter. New data lives in work/altcoin-profit-data and does not overwrite v3 observations.

Forty-six tests, Ruff, Pyright, all 616 public response hashes and full offline snapshot replay pass. No new historical performance trial, no prospective decision, no matured outcome and no real capital. Absolute net profit requires the same currency after applicable costs; account/FX/tax unknowns remain unknown. Prior Selic-relative planning remains historical; v4 planning uses absolute positive-net-return scenarios without imposing them as user targets. Deployment/Proof/attestation remain unpassed. Protected state, trials, production costs and frozen funding/OI/HMM families are untouched.
''')
 print(json.dumps({'report':str(original_report),'audit':str(out/'CRIPTO_LUCRO_ABSOLUTO.json'),'automation':automation},ensure_ascii=True))

def package():
 head=git('rev-parse','HEAD')
 patch=out/'CRIPTO_LUCRO_ABSOLUTO.patch'
 patch.write_bytes(subprocess.check_output(['git','diff','--binary','0fd58c9',head],cwd=repo))
 subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=repo,check=True)
 files={}
 for p in evidence.iterdir():
  if p.is_file():files['docs/evidence/altcoin_profit_20260907/'+p.name]=p
 for name in ('observe_altcoin_forward.py','plan_absolute_profit.py','prepare_altcoin_payoff.py','research_altcoin_analogs.py','collect_altcoin_analogs.py','__init__.py'):
  files['scripts/'+name]=repo/'scripts'/name
 for name in ('test_altcoin_forward.py','test_altcoin_payoff.py','test_altcoin_analogs.py'):
  files['tests/'+name]=repo/'tests'/name
 for directory in ('altcoin_analogs_20260907','altcoin_payoff_20260907','altcoin_forward_20260907'):
  files[f'docs/evidence/{directory}/protocol.json']=repo/f'docs/evidence/{directory}/protocol.json'
 files['base-data/acquisition.json']=work/'altcoin-data/acquisition.json'
 files['training/samples_identity_corrected.json.gz']=work/'altcoin-payoff-results/samples_identity_corrected.json.gz'
 for p in data.rglob('*'):
  if p.is_file() and p.name!='observer.lock':files['profit-data/'+p.relative_to(data).as_posix()]=p
 files['ACOMPANHAMENTO_CRIPTO.md']=out/'ACOMPANHAMENTO_CRIPTO.md'
 replay=(work/'audit_profit_scope.py').read_text().replace("repo=Path(__file__).resolve().parent/'cripto-v1.2'","repo=Path(__file__).resolve().parent").replace("data=repo.parent/'altcoin-profit-data'","data=repo/'profit-data'").replace("base_data=repo.parent/'altcoin-data'","base_data=repo/'base-data'").replace("training=repo.parent/'altcoin-payoff-results/samples_identity_corrected.json.gz'","training=repo/'training/samples_identity_corrected.json.gz'")
 additions={'REPRODUZIR.py':replay.encode(),'requirements.txt':b'httpx==0.28.1\nnumpy==2.5.1\nscikit-learn==1.9.0\nscipy==1.18.0\njoblib==1.5.3\nthreadpoolctl==3.6.0\npytest==8.4.2\n','README.md':'''# Reprodução v4 — lucro absoluto

Python 3.13 e dependências de requirements.txt. Na pasta extraída, `python REPRODUZIR.py` verifica os hashes e reconstrói todo o diagnóstico a partir das 616 respostas públicas gravadas; nenhuma consulta externa é feita. A nova hora de execução é diferente, mas dados, fontes, critérios, características, pontuação e seleção precisam ser idênticos. `python -m pytest -q tests` executa os 41 testes incluídos; cinco controles adicionais de congelamento passaram no repositório, totalizando 46.

O treino reparado está incluído. A auditoria integral de sua construção continua nos pacotes anteriores. Este pacote é suficiente para reproduzir o diagnóstico v4, não autoriza executar ordens e não contém contas/chaves. Não rode o acompanhamento sobre uma cópia do livro como se ela fosse o monitor ativo. O acompanhamento real desta tarefa usa work/altcoin-profit-data no worktree original, conforme RUNBOOK.

O objetivo é lucro líquido absoluto; não há carteira de referência externa. A permissão para escolher qualquer corretora não significa que o adaptador já cubra outras além da Binance pública. Os resultados anteriores permanecem preservados.
'''.encode()}
 hashes={name:sha(p) for name,p in files.items()}
 hashes.update({name:hashlib.sha256(blob).hexdigest() for name,blob in additions.items()})
 zpath=out/'CRIPTO_LUCRO_ABSOLUTO_REPRODUCAO.zip'
 with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,p in sorted(files.items()):z.write(p,name)
  for name,blob in additions.items():z.writestr(name,blob)
  z.writestr('FILE_HASHES.json',json.dumps(hashes,indent=2))
 with zipfile.ZipFile(zpath) as z:
  assert z.testzip() is None
  for name,digest in hashes.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
 manifest={'created_at':datetime.now(timezone.utc).isoformat(),'repository_head':head,'base_commit':'0fd58c90a7d4ae32fbbce02cba035e0dbdeed469','active_objective':'ABSOLUTE_NET_PROFIT','active_protocol':'discovery-altcoin-absolute-profit-20260907-v4','files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in (out/'ACOMPANHAMENTO_CRIPTO.md',out/'CRIPTO_LUCRO_ABSOLUTO.json',patch,zpath)},'zip_entries':len(hashes)+1,'zip_hashes':'PASS','reverse_patch_check':'PASS','historical_evidence':'Previous reports and packages retain their original meaning; active report now reflects user correction.','real_capital':False}
 dump(out/'CRIPTO_LUCRO_ABSOLUTO_MANIFESTO.json',manifest)
 print(json.dumps(manifest,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('mode',choices=('stage','package'))
 args=p.parse_args()
 stage() if args.mode=='stage' else package()
