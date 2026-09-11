import sys
sys.dont_write_bytecode=True
import pathlib,json,hashlib,datetime,importlib.util
import adapter_v3b
R=pathlib.Path(__file__).resolve().parents[1]
def read(n):return json.loads((R/n).read_bytes())
def write(n,x):(R/n).write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf-8')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
b=read('BASELINE.json');contracts=read('INSTRUMENT_CONTRACTS.json');clocks=read('CLOCK_MATRIX.json');ci=read('CLOCK_INVESTIGATION.json');reqs=read('EVIDENCE_REQUIREMENT_MAP.json');decisions=read('DECISIONS.json');tests=read('tests_first/RESULTS.json');fund=read('FUNDING_CONTRACT.json')
changed=[p for p,h in b['protected_hashes'].items() if not pathlib.Path(p).is_file() or sha(p)!=h];assert not changed
assert (R/'tests_first/RESULTS.json').read_bytes()==(R/'tests_reproduction/RESULTS.json').read_bytes()
write('PRESERVATION.json',{'checked_files':len(b['protected_hashes']),'changed':changed,'passed':True,'phase2_phase3_bytes_preserved':True,'new_network_calls':0,'capital_operations':0,'scope':'All baseline-enumerated files; no claim of whole-disk audit'})
write('REPRODUCIBILITY.json',{'identical_results_bytes':True,'runs':['tests_first/RESULTS.json','tests_reproduction/RESULTS.json'],'result_hash':sha(R/'tests_first/RESULTS.json')})
oldpath=R.parent/'phase3/work/adapter_v3.py';spec=importlib.util.spec_from_file_location('preserved_v3',oldpath);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
oldrecords=json.loads((R.parent/'phase3/NORMALIZED_CASES.json').read_bytes());record=next(x['record'] for x in oldrecords if x['case']=='future_00');clock=next(x for x in clocks if x['id']=='future_00');cutoff=max(record['fields']['EVENT_TIME']['value'],record['fields']['INGESTION_TIME']['value'])
comparison={'case':'future_00','cutoff_ns':cutoff,'v3_available_predicate':old.available(record,cutoff),'v3B_states':adapter_v3b.states(clock,cutoff,contracts['BTC_PERPETUAL']),'meaning':'v3 numeric predicate was a technical filter, not proof of economic admissibility. Same-domain observation and cross-domain event meaning are now distinct; no earlier artifacts changed.'};write('CUTOFF_SEMANTICS_COMPARISON.json',comparison)
assert comparison['v3_available_predicate'] and not comparison['v3B_states']['ECONOMICALLY_ELIGIBLE']
answers=[
'BTC spot: o recibo spot exchangeInfo comprova o namespace api.binance.com, a flag isSpotTradingAllowed=true, baseAsset=BTC e quoteAsset=USDT no momento de recebimento. Não há contrato econômico completo de quantidade, preço, multiplier, payoff ou settlement certificado neste bundle.',
'BTC perpetual: o recibo fapi comprova symbol=BTCUSDT, contractType=PERPETUAL, baseAsset=BTC, quoteAsset=USDT e marginAsset=USDT. Isso não prova linearidade, payout em USDT ou multiplier=1.',
'BTCUSDT_261225: o recibo declara NEXT_QUARTER, BTC/USDT, marginAsset=USDT e deliveryDate=1798185600000; o decoder preservado em milissegundos o representa como 2026-12-25 08:00 UTC. Esses termos são declarados na coleta; não validam períodos anteriores nem a regra de settlement.',
'Não estão todos comprovados. Quantity unit, price unit como contrato completo, multiplier, payoff e settlement permanecem NOT_PROVEN. Metadados de base/quote não substituem a definição da unidade de ordem, e filtros LOT_SIZE não definem multiplier.',
'São historicamente comprovados os bytes recebidos e os registros locais de aquisição, com a limitação de precisão do relógio não calibrado. As declarações de exchangeInfo são CURRENT_ONLY, isto é, apenas como coletadas em 08/09/2026, não documentação atual consultada hoje. Vigência passada ou continuidade entre duas coletas iguais permanece desconhecida. Uso em candles anteriores exigiria RETROACTIVE_ASSUMPTION.',
'Funding permanece observação de taxa: FUNDING_REPLAY_NOT_PROVEN. Há 33 registros, deltas entre 28799974 e 28800013 no campo de tempo (sob interpretação ms), mas isso não certifica intervalo fixo, posição elegível, direção, moeda de pagamento ou cash flow realizado.',
'Não. A aritmética de +410,3008 ms está confirmada condicionalmente à leitura de T em ms. O fenômeno aparece nos 12 livros futures, entre +408,6478 e +446,958 ms. CAUSE_UNKNOWN.',
'Faltam significado/unidade historicamente documentados de T/E para esse endpoint e uma ligação calibrada entre relógio remoto e local naquele intervalo. Não há logs contemporâneos de sincronização, offset, monotonicidade de relógio do sistema ou headers de resposta suficientes para distinguir offset, semântica e erro de geração.',
'Nenhum replay econômico parcial BTC spot/perp/future foi habilitado. São possíveis reconstrução literal de metadata, cronologia local de recebimento, separação trade/mark/book e testes dimensionais com unidades explicitamente declaradas. Esses controles não calculam notional/PnL de instrumentos reais nem fills.',
'F03 = BLOCKED_CURRENT_EVIDENCE. Faltam membership/listing/delisting/eligibility históricos, disponibilidade e versões apropriadas aos cutoffs. O pequeno bundle BTC não contém um universo histórico.',
'F04 = BLOCKED_CURRENT_EVIDENCE. Nenhum subconjunto satisfaz simultaneamente unidade, settlement, payoff, multiplier, collateral e admissibilidade temporal. Não se usa PARTIALLY_READY para chamar preparação técnica de autorização econômica.',
'Não se recuperam dos campos capturados: relógio monotônico e offset passado, instante de persistência/normalização não registrado, primeiras publicações e versões ausentes. Logs ou arquivos contemporâneos independentes poderiam mudar alguns estados; dados atuais não recompõem essa história. Essa impossibilidade é relativa ao acervo delimitado, não uma alegação sobre todos os arquivos possíveis.',
'A evidência impede abrir Fase 4 econômica, ranking F03 e replay de funding. Permite decidir a próxima busca estrita: especificação histórica exata de unidade, multiplier, payoff e settlement para BTCUSDT/BTCUSDT_261225 válida na janela escolhida. Se não houver prova, encerrar aquele replay histórico; resolver fórmulas por convenção não é alternativa admissível.'
]
text='''# CRIPTO-PREDICTOR — Fase 3B

Iniciativa `20260911T0233`. Continuação estrita da fase 3.

**F03 = BLOCKED_CURRENT_EVIDENCE. F04 = BLOCKED_CURRENT_EVIDENCE. Nenhum escopo econômico da Fase 4 foi aberto.**

A fase termina por bloqueadores precisos e saturação do bundle delimitado, não por tentativa de fazer UNKNOWN desaparecer. Há progresso técnico local, mas nenhum contrato econômico completo certificado. A causa dos clocks permanece **CAUSE_UNKNOWN**.

## Escopo, baseline e preservação

'''
text+=f"Commit `{b['commit']}`. Foram preservados e verificados {len(b['protected_hashes'])} arquivos, incluindo v2, v3, harness v3.1 e resultados anteriores. Nova extensão isolada: `{adapter_v3b.VERSION}`; nenhuma integração de produção. Baseline e protocolo foram registrados antes das baterias em `BASELINE.json` e `PROTOCOL.json`.\n\n"
text+='''Foram examinadas 34 aquisições preservadas na matriz temporal: 26 recibos do diagnóstico (12 pares de livros e dois exchangeInfo), seis recibos BTC de candles/funding já usados na fase 3, um exchangeInfo do capability probe e o README oficial arquivado. Não são 34 novas coletas nem 34 fontes independentes. Artefatos auxiliares incluem o código do coletor, seu freeze, data_semantics e protocolo histórico. Nenhum resultado de estratégia foi recalculado.

O acervo adicional foi limitado a btc-execution-diagnostic-v1, basis-capability-probe e aos arquivos de código/freeze correspondentes. “Não localizado” abaixo significa não localizado nesse bundle e nos inputs enumerados; não significa uma busca exaustiva no disco ou na internet. Zero chamadas externas, backtests, rankings, F02 ou operações de capital.

## Matrizes dos contratos

PROVEN certifica o valor literal ou transformação explicitamente descrita da evidência, não uma hipótese econômica adicional. CURRENT_ONLY significa declaração recebida na coleta preservada, não consulta à documentação de hoje. Conteúdo idêntico em dois momentos não prova vigência ininterrupta entre eles. N/A exige motivo estrutural; nenhuma lacuna foi transformada em N/A para abrir replay.

'''
for id,c in contracts.items():
 text+=f"### {id} — {c['symbol']}\n\n"
 text+='| Campo | Valor | Status | Evidência | Clock da evidência | Pode valer retroativamente? |\n|---|---|---|---|---|---|\n'
 for k,f in c['fields'].items():
  value=json.dumps(f['value'],ensure_ascii=False) if f['value'] is not None else '—'
  evidence='; '.join(pathlib.Path(e['path']).name+' `'+('/'.join(map(str,e['pointer'])))+'`' for e in f['evidence']) or f['why']
  text+=f"| {k} | {value} | {f['status']} | {evidence} | {f['evidence_clock'] or 'UNKNOWN'} | Não; {f['epistemic_label']} |\n"
 text+='\n'
text+='''Os clocks numéricos dessas tabelas são ns do relógio local, com hashes e ponteiros completos em `INSTRUMENT_CONTRACTS.json`. Para perpetual, deliveryDate=4133404800000 permanece um campo bruto não interpretado como vencimento real. Para o contrato datado, a data foi lida do campo, não do sufixo do ticker. `onboardDate` não comprova o instante em que um participante conheceu o listing nem a vigência de todos os termos desde então.

## Fórmulas e dimensões

Nenhuma fórmula de notional, PnL, margin ou settlement foi atribuída aos três instrumentos reais: faltam termos suficientes para derivá-la da especificação admissível. Não se aplicou fórmula genérica de perpetual nem multiplier=1 por convenção.

O controle dimensional positivo verifica apenas a identidade algébrica com unidades **declaradas no teste**:

```
[BTC] × [USDT/BTC] = [USDT]
```

Os controles `[BTC] × [USD/BTC] → [USDT]` e `[contract] × [USDT/BTC] → [USDT]` falham. Isso comprova o verificador de dimensões, não atribui unidades aos preços reais. O README oficial arquivado descreve colunas distintas de quote/base volume para USD-M/COIN-M e avisa sobre atualizações dos arquivos; não fornece sozinho uma especificação completa de payoff, settlement ou vigência histórica para estes instrumentos.

## Semântica das observações e funding

Trade candle close, mark candle close e displayed ask são mantidos separados por recibo. Nenhum é fill garantido. Não existe index-price neste subset. A distinção literal dos endpoints/colunas permite recusar trade como mark e mark como executable quote, sem provar liquidez, fila, slippage ou hedge simultâneo.

Funding: `FUNDING_REPLAY_NOT_PROVEN`. O primeiro registro contém fundingRate=0.00004595, fundingTime=1787788800000 e rateType=Regular. A observação está comprovadamente no corpo recebido; predicted versus uma taxa economicamente liquidada não é certificado apenas por esse rótulo. O conjunto contém 33 registros e diferenças de tempo entre 28799974 e 28800013 unidades brutas; sob leitura em ms são aproximadamente oito horas, com variação. Esse fato não estabelece uma regra contratual fixa.

RATE é observável; POSITION BASIS, PAYMENT DIRECTION, PAYMENT CURRENCY e ELIGIBILITY TIME permanecem NOT_PROVEN. Original publication, posição efetivamente elegível e ledger de pagamentos não foram capturados nesses recibos. `markPrice` não vira base de pagamento sem fórmula comprovada. Nenhum cash flow foi calculado.

## Investigação temporal

O código preservado do coletor coincide exatamente com o hash congelado `5f316589e5bbbbebea18e4b4b67023f09d6593601b3d9d956176705b10889cd4`. Ele captura `time.time_ns()` antes de `client.send` e logo depois de seu retorno; lê e persiste o corpo em seguida. Isso identifica a origem e a unidade dos clocks locais. Não mede tempo de persistência, normalização, clock monotônico ou offset remoto.

No future_00:

```
LOCAL_REQUEST_TIME = 1788833244617086500 ns
LOCAL_RECEIPT_TIME = 1788833244947699200 ns
T bruto            = 1788833245358
E bruto            = 1788833245362

Se T estiver em milissegundos de epoch:
T × 10^6 − LOCAL_RECEIPT_TIME = 410300800 ns = 410,3008 ms
```

A aritmética é exata, sem float. A unidade local é comprovada pelo coletor. A leitura de T em ms é compatível com o epoch e com o decoder preservado, mas o bundle não contém a especificação histórica do endpoint depth que prove a unidade e o significado de T/E. Portanto, a diferença não é uma prova isolada de clock skew ou erro da fonte.

'''
text+=f"Nos 12 livros futures, todas as diferenças condicionais são positivas: mínimo {ci['delta_ms_min']} ms, máximo {ci['delta_ms_max']} ms, mediana {ci['delta_ms_median']} ms. T, E, request, receipt e lastUpdateId são estritamente crescentes na amostra. Todos os recebimentos são posteriores às requisições locais. Os inteiros locais têm granularidade observada de {ci['local_encoded_resolution_gcd_ns']} ns; granularidade de representação não é precisão, exatidão ou sincronização. E−T varia de 2 a 5 ticks brutos.\n\n"
text+='''As duas aquisições de future exchangeInfo têm o mesmo corpo, inclusive serverTime, apesar de horários de recebimento diferentes. Isso impede tomar o serverTime do corpo como horário fresco de resposta. Não prova qual mecanismo de cache/snapshot, se algum, ocorreu. Os 26 corpos do diagnóstico e os dois corpos docs/info do probe tiveram seus hashes conferidos contra os metadados preservados.

| Hipótese | Evidência favorável | Evidência contrária / limite | Teste possível | Conclusão |
|---|---|---|---|---|
'''
for h in read('CLOCK_HYPOTHESES.json')['hypotheses']:text+=f"| {h['id']} — {h['hypothesis']} | {'; '.join(h['for'])} | {'; '.join(h['against'])} | {h['possible_test']} | {h['conclusion']} |\n"
text+='''
Nenhuma hipótese causal foi selecionada. Não há base para subtrair 410,3008 ms, ajustar timestamps pela mediana ou culpar o coletor/exchange.

## Os três estados

**OBSERVED:** o corpo foi recebido até o cutoff no mesmo domínio de relógio local. Não exige fingir que o clock remoto está sincronizado.

**EVENT_OCCURRED:** um timestamp associado foi preservado; ocorrência efetiva até um cutoff local continua NOT_PROVEN enquanto unidade, significado ou ligação entre relógios estiverem sem prova.

**ECONOMICALLY_ELIGIBLE:** requer o contrato econômico e sua validade para o escopo, além da admissibilidade temporal. Recebimento é condição necessária, não suficiente.

`CUTOFF_SEMANTICS_COMPARISON.json` executa os dois predicados no mesmo future_00. Em `max(T convertido, receipt)`, o filtro técnico v3 retorna true; a nova extensão mantém OBSERVED=true e ECONOMICALLY_ELIGIBLE=false. Não se reinterpretam os resultados anteriores como validação econômica. O máximo numérico de relógios não reconciliados deixa de servir como justificativa de elegibilidade.

## Matriz de clocks dos recibos

Os valores de evento são brutos; os locais são ns. U=UNKNOWN. PUB, RESP, ING e NORM permanecem U: E/serverTime não foram promovidos a publicação/resposta, e receipt não foi renomeado para ingestão. O header HTTP Date disponível em um recibo é preservado como candidato com resolução textual de um segundo, não primeira publicação ou resposta calibrada.

| Recibo | SOURCE_EVENT_TIME | SOURCE_PUBLICATION_TIME | SOURCE_RESPONSE_TIME | LOCAL_REQUEST_TIME | LOCAL_RECEIPT_TIME | INGESTION_TIME | NORMALIZATION_TIME |
|---|---|---|---|---|---|---|---|
'''
for c in clocks:
 vals=['U' if v['value'] is None else str(v['value']) for v in c['clocks'].values()]
 text+='| '+c['id']+' | '+' | '.join(vals)+' |\n'
text+='''
As unidades, domínios e ressalvas por célula estão em `CLOCK_MATRIX.json`; não se impõe uma ordem total entre esses clocks.

## Evidence requirement map

“Irrecuperável do capture” significa que os bytes e campos registrados não identificam aquela propriedade; não declara que todo arquivo histórico possível inexiste. Uma fonte nova precisa ser contemporânea ao evento ou explicitamente versionada para provar o passado. Documentação de hoje e novos timestamps não recuperam clocks antigos.

| Campo ausente | Por que importa | Evidência necessária | Existe localmente? | Recuperável legitimamente? | Bloqueia | Próxima ação |
|---|---|---|---|---|---|---|
'''
for e in reqs:text+='| '+' | '.join(e[k] for k in ['missing_field','why_it_matters','necessary_evidence','exists_locally_in_bounded_scope','legitimate_recovery','blocks','next_action'])+' |\n'
text+='''
## Testes, decisões e parada

'''+json.dumps(tests['summary'],indent=2,ensure_ascii=False)+'\n\n'
text+='''Foram 27 controles positivos, 28 negativos e 3 de UNKNOWN, sem falhas, além de 114 verificações de estados temporais. Positivos verificam campos explicitamente evidenciados, round-trip, distinção de métricas e álgebra declarada; não existe controle positivo de payoff real completo. As tentativas de moeda errada, contratos como quantidade base, multiplier suposto, settlement incompatível, margem como moeda de PnL, linear/inverse trocados e trade/mark/fill confundidos foram REJECTED ou UNSUPPORTED. UNKNOWN não foi preenchido para satisfazer o teste. A segunda execução produziu RESULTs idênticos byte a byte.

F03: identidade parcial CURRENT_ONLY; listing/delisting/eligibility históricos não demonstrados; disponibilidade apenas por recebimento local; publicação original ausente; revisões limitadas aos hashes adquiridos. **BLOCKED_CURRENT_EVIDENCE**, sem subset de ranking habilitado.

F04: campos literais parciais e tipos de preço distinguíveis; quantidade, unidade de preço como contrato, settlement, payoff, multiplier e collateral incompletos; domínio temporal não reconciliado. **BLOCKED_CURRENT_EVIDENCE**, sem subset econômico habilitado. Não exigir o universo completo não elimina essas faltas no próprio BTC.

Os dois gates ficam em BLOCKED_CURRENT_EVIDENCE porque fontes históricas específicas poderiam trazer termos ou informações ausentes. Algumas propriedades são não identificáveis a partir deste capture: offset/calibração não registrados, ingestão/normalização não registradas e vintages ausentes. Isso não é suficiente para declarar o projeto inteiro STRUCTURALLY_UNRECOVERABLE_FOR_SCOPE. Encerra-se esta rodada pela regra B (bloqueio preciso), com C para propriedades não identificáveis nos campos capturados e D para o bundle de especificações delimitado.

## Respostas finais

'''
for i,x in enumerate(answers,1):text+=f'{i}. {x}\n\n'
text+='''## Reproduzir

```
C:\\Cripto\\CRIPTO.cmd python -X utf8 C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233\\phase3b\\work\\test_contracts.py C:\\Cripto\\operacao\\temporarios\\fase3b-repro-novo
```

Use uma pasta de saída nova. Não reexecute prepare.py sobre a baseline. O teste usa contratos/matrizes desta entrega e os recibos locais preservados. `PRESERVATION.json`, `REPRODUCIBILITY.json` e `MANIFEST.json` registram as verificações. O pacote inclui os inputs específicos adicionais para rastreabilidade; os caminhos originais são mantidos como proveniência.

Para BTC, base/quote e alguns campos de mercado estão comprovados como recebidos; settlement, multiplier, payoff e temporalidade econômica continuam precisamente desconhecidos. Isso permite reconstrução documental e controles técnicos, mas impede replay econômico. Não haverá promoção global para Fase 4.
'''
(R/'REPORT.md').write_text(text,encoding='utf-8')
write('REGISTRY.json',{'initiative':'20260911T0233','phase':'3B','parent_phase':str(R.parent/'phase3'),'decisions':decisions,'answers':{str(i):x for i,x in enumerate(answers,1)},'tests':tests['summary'],'clock_cause':'CAUSE_UNKNOWN','stop':'PRECISE_BLOCKERS_AND_BOUNDED_SATURATION','capital_permission':False})
print('Report and 13 answers complete; protected files',len(b['protected_hashes']))
