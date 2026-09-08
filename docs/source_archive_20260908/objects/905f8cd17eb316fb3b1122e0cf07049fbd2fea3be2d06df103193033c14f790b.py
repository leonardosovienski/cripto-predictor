"""Package the completed continuation without altering the earlier delivery."""
import gzip
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

W = Path(__file__).resolve().parent
R = W / 'cripto-v1.2'
D = W / 'altcoin-payoff-data'
X = W / 'altcoin-payoff-results'
E = R / 'docs/evidence/altcoin_payoff_20260907'
O = W.parent / 'outputs'
result = json.loads((X / 'results.json').read_text())
shutil.copy2(X / 'results.json', E / 'results.json')
validation = {
    'targeted_tests': {'total':30,'prior_analog':11,'new_payoff_identity':11,'freeze_gate':8},
    'ruff':'PASS','pyright':'PASS',
    'offline_byte_identical':['results.json','samples_identity_corrected.json.gz'],
    'new_price_requests':len(result['raw_requests']),
    'new_historical_performance_trials':0,
    'scheduler_created':False,'capital_authorized':False,
}
ledger = {
    'id':result['id'],'protocol_commit':'bbe7a8b','implementation_before_new_prices_commit':'34b599a',
    'adaptive_changes':['quantity/identity correction for known missing outcomes','objective switches from rally frequency to net log payoff','week grouping and uncertainty penalty','abstention/cash allowed'],
    'preserved':['240-symbol sample','8 feature definitions','1-day information delay','7-day horizon','2021-2023 training geometry','all original observations and output files'],
    'new_model_specifications':1,'new_historical_performance_trials':0,
    'snapshot_date':'2026-09-07','snapshot_is_prospective':False,
    'decision':'PREPARED_NOT_PROMOTED; no candidate passed the dry-run margin',
    'data_censoring':'BTT, CVP, VIDT retained with null return; no fabricated full-loss label',
    'notes':'Daily marks and same-base cross-quote identity are accounting assumptions, not evidence of actual fills. Historical v1 scenarios are sensitivity only. No formal Core trial/power attestation or capital activation.'
}
for name,obj in [('validation.json',validation),('search_log.json',ledger)]:
    (E/name).write_text(json.dumps(obj,indent=2),encoding='utf-8')

def pct(value):return 'desconhecido' if value is None else f'{value*100:.2f}%'.replace('.',',')

rows=['| Caso antigo | Tratamento | Retorno bruto de referência em 7 dias |','|---|---|---:|']
for x in result['identity_resolutions']:
    treatment=x.get('exit_pair','saída não verificada')
    if x.get('quote_conversion_pair'):treatment+=' × '+x['quote_conversion_pair']
    if x.get('new_units_per_old') and x['kind']=='TOKEN_MIGRATION':treatment+=f"; {x['new_units_per_old']} unidade(s) por antiga"
    rows.append(f"| {x['symbol']} | {treatment} | {pct(x['gross_return'])} |")
report=f'''# Continuação do seletor de moedas — 07/09/2026

**A base existente foi aproveitada. A próxima versão já calcula ganhos, perdas e custos e pode decidir não selecionar nenhuma moeda. Ainda não demonstrou lucro.**

O trabalho desta rodada teve dois resultados concretos. Primeiro, corrigi o tratamento de moedas que mudaram de nome ou de par. Segundo, implementei um protótipo que considera quanto cada cenário histórico ganhou ou perdeu, com margem para incerteza, em vez de apenas contar grandes altas.

Dos 13 casos problemáticos da rodada anterior, dez tiveram preço de referência reconstruído. BTT, CVP e VIDT continuam sem retorno verificável no horizonte original e agora aparecem como **desconhecidos** no dataset derivado. Não se atribui perda total por conveniência. A versão original permanece preservada como histórico da pesquisa.

{chr(10).join(rows)}

Esses são preços de referência de fechamento e direitos de conversão; não são vendas realizadas. HNT e FTT usam o preço em BUSD convertido pelo BUSD/USDT observado, com uma perna adicional de custo na conta líquida. Não foi suposta paridade perfeita. O BTT novo começou a negociar depois do prazo da operação antiga; usar esse preço posterior seria alterar o teste.

As proporções foram conferidas em fontes oficiais, incluindo [NPXS/PUNDIX](https://www.binance.com/en/support/announcement/detail/3776ecbf694a4dfda138c0d7262ea4b2), [BZRX/OOKI](https://www.binance.com/en/support/announcement/detail/dff27dc6bcbb432c902bcbea5e24ddfa), [OCEAN/FET](https://www.binance.com/en/support/announcement/detail/3dc0eae584cd4accb34cb914dacf670d), [MATIC/POL](https://www.binance.com/en/support/announcement/detail/619c4929fc3f4a0d9df7f9ae1d4519a5) e [BNX/FORM](https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2). Todos os 13 registros têm suas fontes no JSON; consulta em 07/09/2026. As 13 novas respostas de preços foram registradas às 19:25 UTC, com URL e hash. Data do evento e hora da consulta são campos diferentes.

**A correção não recuperou a estratégia anterior.** Mantendo exatamente suas escolhas de 2025–2026, a carteira continua negativa: aproximadamente -97,83% com perda total apenas no caso VIDT ainda desconhecido, ou -97,33% se essa posição tiver retorno zero. São cenários de diagnóstico, não uma faixa garantida de perda real; o P&L executável exato permanece desconhecido.

## Como a nova regra decide

1. Compara a moeda com os mesmos 200 exemplos históricos usados como vizinhos, preservando preços, volume, volatilidade e atraso de informação.
2. Calcula o ganho ou a perda líquidos de cada exemplo, com custos assumidos. Duas altas grandes deixam de esconder muitas perdas pequenas.
3. Agrupa os exemplos pela semana de origem para reduzir o peso artificial de várias moedas subindo juntas.
4. Desconta uma margem heurística para incerteza. Essa margem não é probabilidade calibrada nem limite estatístico garantido.
5. Só admite até cinco candidatos com margem positiva, a 20% cada. As vagas não preenchidas ficam em caixa simulado. Se houver um desfecho desconhecido entre os vizinhos, a moeda não é aprovada; esse exemplo não é apagado do treinamento.

Na fotografia de 07/09 já utilizada anteriormente, **nenhuma das 14 moedas passou**. A resposta do protótipo foi **100% em caixa simulado**. Isso mostra que ele consegue se abster; não prova que saberá escolher as próximas altas ou que sua margem está calibrada. A lista mantém o universo anterior para isolar a mudança de critério; não é uma seleção completa do mercado e contém RLUSD, que exige classificação no universo futuro. O helper de classificação por nome já evita excluir JUP/SYRUP como se fossem produtos alavancados, sem rescrever a amostra antiga.

## O que fazer a seguir

O próximo teste deve registrar as escolhas **antes** dos movimentos seguintes e comparar o retorno líquido com alternativas simples, incluindo ficar sem exposição. Antes de ativá-lo, faltam três itens concretos:

- Completar o universo e o calendário de migrações/suspensões com a hora em que cada informação ficou disponível. Os 13 casos corrigidos não são um cadastro completo de todos os eventos.
- Verificar preços de entrada/saída, atraso e custos numa simulação acompanhada ao vivo. Os custos atuais continuam assumidos; retornos em USDT também precisam de tratamento explícito de câmbio para comparação em BRL.
- Fixar uma amostra e um critério econômico suficientes. Algumas semanas favoráveis não demonstram lucro repetível. Atestado de poder/harness e gates de execução continuam necessários antes de promoção formal.

A primeira semana futura possível deste protocolo é 14/09/2026. Os resultados ainda não existem. Esta rodada preparou código, regras e uma execução diagnóstica; **não iniciou agendamento ou acompanhamento automático**. Os períodos 2024–2026 já vistos continuam exploratórios e não serão apresentados como novo teste independente. Foram feitos zero novos testes de performance histórica da V2, conforme o orçamento registrado antes de consultar os preços corrigidos.

Validação: 30 testes direcionados passaram, incluindo conservação de quantidade nas migrações, censura sem apagar perdas, custos, dependência entre moedas e capacidade de recusar uma carteira desfavorável. Ruff/Pyright passaram. A reprodução em modo offline gerou resultado e dataset derivados idênticos byte a byte. Protocolo: `bbe7a8b`; implementação inicial: `34b599a`. Produção, coleta, custos congelados e evidência anterior preservados.
'''
(O/'CRIPTO_CONTINUACAO.md').write_text(report,encoding='utf-8')
(O/'CRIPTO_CONTINUACAO.json').write_text(json.dumps({'results':result,'validation':validation,'search_log':ledger},indent=2),encoding='utf-8')

members={}
for p in E.glob('*.json'):members['docs/evidence/altcoin_payoff_20260907/'+p.name]=p.read_bytes()
members['scripts/prepare_altcoin_payoff.py']=(R/'scripts/prepare_altcoin_payoff.py').read_bytes()
members['tests/test_altcoin_payoff.py']=(R/'tests/test_altcoin_payoff.py').read_bytes()
for p in D.rglob('*'):
    if p.is_file():members['payoff-data/'+p.relative_to(D).as_posix()]=p.read_bytes()
for p in X.iterdir():
    if p.is_file():members['payoff-expected/'+p.name]=p.read_bytes()
basezip=O/'ALTCOINS_REPRODUCAO.zip'
readme=f'''# Reprodução da continuação

Este ZIP é um complemento do pacote ALTCOINS_REPRODUCAO.zip já entregue,
SHA256 {hashlib.sha256(basezip.read_bytes()).hexdigest()}.
Extraia primeiro aquele pacote e depois este, na mesma pasta. O complemento
adiciona payoff-data e payoff-expected, preservando data/ e expected/ originais.
Use o Python 3.13 com as dependências daquele pacote.

    python -m pytest tests/test_altcoin_payoff.py -q
    python -m scripts.prepare_altcoin_payoff --base-data-dir data --base-results-dir expected --data-dir payoff-data --output-dir payoff-reproduced --offline

O modo --offline não consulta rede e falha se faltar uma resposta registrada.
Compare payoff-reproduced/results.json e samples_identity_corrected.json.gz
com payoff-expected/. O caso não tem ordens, scheduler ou promoção de modelo.

MANIFEST.json lista hashes dos membros, exceto o próprio manifesto.
'''
members['README_CONTINUACAO.md']=readme.encode()
manifest={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in members.items()}
members['MANIFEST_CONTINUACAO.json']=json.dumps(manifest,indent=2).encode()
target=O/'CRIPTO_CONTINUACAO_REPRODUCAO.zip'
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name,data in members.items():z.writestr(name,data)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for name,meta in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==meta['sha256']
print(json.dumps({'files':[p.name for p in O.glob('CRIPTO_CONTINUACAO*')],'zip_bytes':target.stat().st_size,'members':len(members)},indent=2))
