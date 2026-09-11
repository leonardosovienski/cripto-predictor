import pathlib,json,hashlib,datetime,shutil,subprocess
R=pathlib.Path(__file__).resolve().parents[1]
def read(n):return json.loads((R/n).read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=read('BASELINE.json');res=read('RESULTS.json');s=res['summary'];rows=read('NORMALIZED_CASES.json');en=read('EXPLICIT_ENRICHMENT.json')
changed=[p for p,h in b['read_only_hashes'].items() if not pathlib.Path(p).exists() or sha(pathlib.Path(p))!=h]
pres={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protected_files_checked':len(b['read_only_hashes']),'changed':changed,'passed':not changed,'network_calls':0,'capital_operations':0,'phase2_adapter_unchanged':sha(pathlib.Path(b['adapter_path']))==b['adapter_sha256'],'scope':'Every file listed in baseline; not a claim to have rehashed every unrelated file on disk.'}
(R/'PRESERVATION.json').write_text(json.dumps(pres,indent=2),encoding='utf-8');assert not changed
repro=R/'reproduction_check'
if repro.exists():
 rr=json.loads((repro/'RESULTS.json').read_bytes());assert rr['summary']==s
 for n in ['NORMALIZED_CASES.json','ADVERSARIAL_RESULTS.json']:assert (R/n).read_bytes()==(repro/n).read_bytes()
 reproduction={'passed':True,'identical_normalized_and_adversarial_bytes':True,'identical_summary':True,'run_metadata_timestamp_excluded':True}
else:raise RuntimeError('Independent rerun required')
(R/'REPRODUCIBILITY.json').write_text(json.dumps(reproduction,indent=2),encoding='utf-8')
answers=[
'Foram avaliados 23 recibos HTTP/RPC reais distintos e 1 artefato retrospectivo de identidade. Para recibos com séries, normalizou-se a primeira observação; não se certificaram todas as linhas. Há ainda 9 casos derivados de enriquecimento, sem novos recibos. Dois recibos exchangeInfo contêm vários símbolos: os derivados incluem stablecoins.',
'Zero receberam certificação de identidade econômica completa para replay. Os 24 envelopes preservam fielmente evidência parcial e ausências. Nos derivados, 8 descrições de instrumentos têm base/quote explícitas; o nono reconstrói o índice Aave. Não são 9 instrumentos economicamente certificados.',
'BTCUSDT aparece em namespaces spot e futures; candles trade e mark têm semânticas diferentes; fundingRate não prova pagamento nem intervalo; marginAsset não prova settlement; precision não prova decimals on-chain. No livro future_00, evento está 410,3008 ms depois do recebimento local. Headers repetidos do mesmo bloco têm recibos distintos, sem evidência de revisão econômica.',
'Não foi demonstrado novo bug de produção no F01 v2. Foram documentadas duas lacunas de representação. Um bug apareceu no oráculo do novo teste: presumir elegibilidade no instante de recebimento apesar de evento posterior. A implementação já bloqueava esse caso; corrigiu-se o teste, preservando sua falha.',
'Sim, foi criada a extensão experimental F01-real v3: statuses explícitos, semântica da observação, proveniência e gate conservador. O arquivo F01 v2 permanece idêntico. A correção posterior foi no harness v3.1, sem alterar os bytes do adapter v3. Nenhuma integração em produção.',
'Faltam, conforme a fonte, settlement explícito, payoff/multiplier, identidade histórica de tokens, unidades econômicas, publicação original, revisão/provedor/implementação históricos, elegibilidade datada do universo e clocks reconciliados. SOURCE_VERSION=2.0 nos RPC descreve apenas o envelope JSON-RPC, nunca versão da implementação Aave.',
'Os recibos exchangeInfo preservados permitem recuperar base, quote, marginAsset e contractType no instante da coleta, com seus próprios clocks. O bundle Aave permite ligar chain observada no endpoint, selector, pool, endereço do argumento e inteiro de normalized income ao registro derivado do bloco. O decoder local documenta RAY=10^27. São evidências separadas; não foram retropropagadas aos candles.',
'A amostra não permite recuperar a primeira publicação ou revisões não arquivadas, nem afirmar elegibilidade de universo em datas antigas. Metadados de setembro/2026 não certificam especificações de 2020–2024. Isso é impossibilidade nesta evidência, não prova de que nenhum arquivo histórico externo exista.',
'Sim: BTCUSDT spot e PERPETUAL são instrumentos distintos mesmo com o mesmo símbolo; pool Aave e token USDC são contratos diferentes. Trade versus mark são métricas distintas, que podem referir o mesmo instrumento. Não foi demonstrado que a produção tenha efetivamente unido esses registros antes; mostrou-se o risco e a recusa no experimento.',
'F03: BLOCKED. O envelope preserva incertezas e impede o uso antecipado dos recibos, mas não fornece publicação histórica nem membership/listing/delisting completos. Metadados recentes não abrem ranking point-in-time histórico.',
'F04: BLOCKED para replay econômico. Já distingue namespaces, metric types, endereços e moedas explicitamente observadas, mas ainda faltam contratos de settlement/payoff/unidade e reconciliação dos clocks; não há comprovação de fills. Isso não impede estudos técnicos isolados de identidade.',
'A próxima incerteza de maior valor é se o bundle preservado de BTC spot/futures contém especificação explícita, temporalmente compatível, de unidade de quantidade, multiplier, payoff e settlement. Deve-se verificar esse gate necessário antes de replay e explicar a divergência de 410,3008 ms por evidência do coletor. Se faltar, manter UNKNOWN e registrar precisamente o contrato de evidência requerido.'
]
text='''# CRIPTO-PREDICTOR — Fase 3: identidade em recibos reais

Iniciativa `20260911T0233`. Resultado: **normalização parcial rastreável; identidade econômica completa ainda não certificada. F03 BLOCKED. F04 BLOCKED.**

Esta fase não calcula alpha, não reexecuta F02/F05, não altera hipóteses ou protocolos congelados e não autoriza validação prospectiva ou capital.

## Escopo e denominadores

23 recibos HTTP/RPC e um artefato retrospectivo formam 24 casos primários. Cada série fornece apenas sua primeira linha para o experimento de identidade; bytes completos e número de linhas são preservados. Amostragem deliberada por símbolo/endpoint, sem seleção por retorno. Nove enriquecimentos são apresentados separadamente, reutilizando os mesmos recibos: não aumentam a contagem de fontes independentes.

`VALID` significa identidade econômica completa, não simplesmente JSON válido. `AMBIGUOUS` inclui campos econômicos não comprovados; não significa que todos os campos sejam desconhecidos. Metadados/RPC são evidência auxiliar, não preços negociáveis. O round-trip mede fidelidade da representação parcial, não comprovação do que falta. Assim, zero VALID e 24 envelopes fiéis são resultados compatíveis.

## Protocolo e baseline

'''
text+=f"Commit `{b['commit']}`. F01 v2 SHA-256 `{b['adapter_sha256']}`. `BASELINE.json` identifica os arquivos somente leitura, a seleção exata e os caminhos experimentais; `PROTOCOL.json` precede a bateria. Foram verificados {len(b['read_only_hashes'])} arquivos protegidos, sem mudanças. Os documentos e manifestos anteriores não foram reescritos.\n\n"
text+='''Hipótese: um contrato explícito consegue conservar o que os recibos comprovam e recusar usos que dependam de metadata ausente. Incerteza: instrumento, unidade e disponibilidade podem ser reconstruídos sem pressupostos? Controle: leitura direta de ponteiros e hashes; mesmas observações após serialização; pares reais com semântica diferente; mutações derivadas claramente identificadas. Métrica: perdas de round-trip, uso antes do cutoff, inferências e adversários aceitos. Custos: processamento local; zero coleta, conversão cambial, taxas ou premissas de rentabilidade.

Sucesso exige todos os casos suportados fiéis, nenhuma informação futura admitida, proveniência verificável e preservação da baseline. Rejeição: inconsistência aceita ou perda semântica. Inconclusão econômica: ausência de campos históricos ou contrato explícito. Passar o envelope não abre automaticamente o replay.

## Resultado original e extensão

`V2_FIRST_BATTERY.json` conserva a execução do v2 intacto: 24 casos não elegíveis para construção direta. O teste não preencheu Instrument e publication com valores supostos. É uma avaliação de representabilidade e recusa, não prova de uma colisão real na produção. O schema não tem tipo/unidade de observação, status UNKNOWN, revisão ou proveniência por campo. Isso limita seu escopo; não invalida os testes sintéticos da fase 2.

`EXTENSION_PROTOCOL.json` registra, depois desse resultado, a extensão v3 em arquivo separado. Os 23 campos pedidos estão em cada envelope, com PROVEN/UNKNOWN/N/A e justificativa; SOURCE_VERSION distingue protocolo de implementação no texto da transformação. Nada é classificado N/A apenas por faltar. Valores originais, ponteiros, transformação, hashes do arquivo físico e do corpo descomprimido ficam preservados. O gate econômico exige todos os campos necessários comprovados ou estruturalmente N/A.

O primeiro teste v3 também foi preservado, com adapter, harness e resultados em `preserved_first_v3/`. Houve uma expectativa incorreta no teste: assumir que todo recibo já estaria elegível quando recebido. `future_00` traz T=1788833245358 ms e recebimento=1788833244947699200 ns: diferença de **410,3008 ms**. A causa física (clock skew, relógio do coletor ou semântica da fonte) não foi estabelecida. O adapter recusou o registro nesse cutoff. O harness v3.1 passou a exigir o maior clock comprovado, preservando o valor real e registrando a inconsistência. O antigo campo TEMPORAL_VIOLATIONS=1 era uma divergência contra esse oráculo incorreto, não vazamento observado; a errata é esta seção e `CORRECTION_PROTOCOL.json`.

## Síntese da bateria final

```json
'''+json.dumps(s,indent=2,ensure_ascii=False)+'\n```\n\n'
text+='''Os 19 testes incluem 15 mutações/recusas derivadas e quatro pares reais. As famílias A–H estão cobertas; ausência de recibo coin-margined real limita a abrangência do teste de settlement. A recusa de mutação comprova integridade de evidência, não a verdade econômica do servidor. A recusa dos pares reais verifica diferenças explícitas; recusas por UNKNOWN conservam a lacuna. Noventa e dois checks incluem antes/no limite de recebimento, maior clock e revisão futura derivada. Não foi encontrada revisão econômica real autenticada para testar reconstrução histórica entre versões; dois headers repetidos são duas aquisições, não duas versões econômicas.

SILENT_INFERENCES=0 significa que os campos normalizados desta bateria têm evidência/transformação explícita ou UNKNOWN, não que qualquer decoder arbitrário futuro esteja certificado. Nenhuma paridade USD/USDT foi aplicada. UNIT de um call RPC permanece raw ABI; não se promove um inteiro a valor monetário.

## Matriz primária

| Caso | Fonte | Instrumento | Unidade | Settlement | Versão | Temporalidade | Round-trip | Adversarial | Resultado |
|---|---|---|---|---|---|---|---|---|---|
'''
for r in rows:
 e=r['record'];f=e['fields']
 def val(k):return str(f[k]['value']) if f[k]['status']=='PROVEN' else f[k]['status']
 timing='receipt; evento UNKNOWN' if f['EVENT_TIME']['status']!='PROVEN' else 'evento + receipt; publicação UNKNOWN'
 if e['case']=='future_00':timing='evento > receipt: bloqueado no recebimento'
 if e['case']=='late_identity_mapping':timing='acesso posterior; PIT proibido'
 text+=f"| {e['case']} | {val('VENUE')} | {val('ASSET_IDENTITY')} | {val('UNIT')} | {val('SETTLEMENT')} | body {e['body_hash'][:10]} | {timing} | fiel, parcial | conjunto A–H / pares | {r['classification']} |\n"
text+='''
Todos os campos e hashes completos estão em `NORMALIZED_CASES.json`; a matriz não substitui esse registro. MARKET_TYPE desconhecido em candles não é preenchido por sufixo de ticker. VENUE é namespace do host evidenciado, não certificação da contraparte legal. O preço de livro é displayed ask, nunca fill garantido. O candle é close trade/mark, nunca executable quote. Uma resposta vazia é corretamente rejeitada como observação; não é preço zero ou prova suficiente de delisting.

## Evidências recuperáveis, sem backfill

`EXPLICIT_ENRICHMENT.json` contém oito descrições de instrumentos derivadas de exchangeInfo, incluindo BTC, ETH, WBETH e stablecoins quando presentes. Base/quote e marginAsset/contractType são copiados de campos explícitos e só conhecidos a partir do recebimento daquele recibo. Não se aplicou metadata de setembro/2026 a candles antigos. Precision não virou decimals; marginAsset não virou settlement. A categorização econômica de WBETH como wrapped/staked não foi inferida apenas do ticker.

No bundle Aave, a resposta de chainId é 42161 no endpoint consultado. O recibo web3_sha3 liga `getReserveNormalizedIncome(address)` ao selector usado pelo call. Pool, argumento de token, bloco e inteiro concordam com month-00 preservado. O inteiro 1069973262775083814190632012, dividido exatamente por 10^27 conforme decoder local preservado, produz **1.069973262775083814190632012**. Essa transformação é reproduzível e não produz USDC monetário. A concordância com month-00 usa a mesma linhagem; não é fonte independente nem reexecução F02.

O registro derivado preservado tem decimals=6 e o call aave_027 retorna inteiro 6. O recibo específico de selector decimals() não pertence a esta amostra exata; a extensão não declara uma nova certificação histórica do ABI. Código de implementação histórica e primeira disponibilidade ao trader continuam NOT_PROVEN. Não foram encontrados nesta seleção recibos de OI, index-price, coin-margined, logs de eventos ou revisão econômica autenticada; não houve busca externa para suprir essas classes.

## Respostas finais

'''
for i,x in enumerate(answers,1):text+=f'{i}. {x}\n\n'
text+='''## Reprodução e limites

Com o ambiente e recibos locais preservados, execute:

```powershell
C:\\Cripto\\CRIPTO.cmd python -X utf8 C:\\Cripto\\operacao\\relatorios\\OPEN_SOURCE_20260911T0233\\phase3\\work\\run.py C:\\Cripto\\operacao\\temporarios\\f01-real-repro-novo
```

Escolha um diretório de saída novo. Não reexecute prepare.py sobre a baseline. `REPRODUCIBILITY.json` registra uma segunda execução com mesmos bytes dos envelopes/adversários e mesma síntese; horários de execução não fazem parte da igualdade. `PRESERVATION.json` compara todos os arquivos enumerados na baseline. `MANIFEST.json` sela esta entrega. O código experimental usa a biblioteca padrão e imports já existentes do ambiente, sem novas bibliotecas.

O resultado autoriza continuar investigando contratos de dados. Não autoriza ranking, replay econômico completo, promoção de hipótese, validação prospectiva, ordens ou capital.
'''
(R/'REPORT.md').write_text(text,encoding='utf-8')
(R/'REGISTRY.json').write_text(json.dumps({'initiative':'20260911T0233','phase':3,'parent_phase':str(R.parent/'phase2'),'baseline_commit':b['commit'],'result':s,'F03':{'status':'BLOCKED','reason':answers[9]},'F04':{'status':'BLOCKED','reason':answers[10]},'answers':{str(i):x for i,x in enumerate(answers,1)},'protected_unchanged':True,'capital_permission':False},indent=2,ensure_ascii=False),encoding='utf-8')
print('Report complete; protected files',len(b['read_only_hashes']))
