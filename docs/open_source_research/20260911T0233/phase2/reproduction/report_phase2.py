import pathlib,json,hashlib,datetime,shutil,subprocess,zipfile,math
R=pathlib.Path(__file__).resolve().parents[1]
P=pathlib.Path('C:/Cripto/pesquisa-20260909')
D=P/'docs/open_source_research/20260911T0233'
OUT=D/'phase2';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v).replace('|','/') for v in row)+' |\n' for row in rows)+'\n'
results=read(R/'RESULTS.json');rs=results['results'];v1=read(R/'F01_ADVERSARIAL_V1.json');v2=read(R/'F01_ADVERSARIAL_V2.json');sem=read(R/'F03_SEMANTIC_GATE.json')
assert not v1['passed'] and v2['passed'] and v2['original_F01']['passed']
assert sha(R/'work/experiments_v1_preserved.py')==results['implementation_sha256']==v1['implementation_sha256']
assert sha(R/'work/experiments.py')==v2['implementation_sha256']
assert rs['F04']['passed'] and rs['F05']['passed'] and rs['F02']['pass_preservation']
fields=['HIPÓTESE','INCERTEZA QUE SERÁ REDUZIDA','BASELINE','DADOS E CONTRATO TEMPORAL','IMPLEMENTAÇÃO','CONTROLE / REFERÊNCIA INDEPENDENTE','MÉTRICA PRINCIPAL','CUSTOS E PREMISSAS ECONÔMICAS','TESTE DE FALSIFICAÇÃO','CRITÉRIO DE SUCESSO','CRITÉRIO DE REJEIÇÃO','CRITÉRIO DE INCONCLUSÃO','RESULTADO','IMPACTO SOBRE AS DECISÕES EXISTENTES','PRÓXIMO GATE']
specs={
'F01':[
'Identidade explícita, unidades coerentes e versões por publicação/recepção impedem mistura de instrumentos e uso de informação ainda não disponível.',
'Se distinguir nomes é suficiente ou se ainda passam erros de unidade, liquidação, revisão e conversão monetária.',
'MarketDataPoint instalado e snapshot da fase1; B03 cobriu clocks/preço, sem identidade econômica completa. Não repetimos B03 nem a suíte inteira.',
'Fixtures sintéticas: quatro pares distintos (quote, payoff/liquidação, chain, venue), dois relógios inválidos, revisão recebida depois da publicação, câmbio explícito USDT/USD0,97. Tempos são inteiros relativos; não observações de mercado. Instrumento fixa venue, mercado, base/quote/settlement, chain/contrato, vencimento, multiplicador, payoff e unidades.',
'Instrument/Observation, asof e convert no adapter isolado work/experiments.py. Após controles adversariais, v2 valida relação de unidades, settlement permitido, hash hexadecimal, montante finito e conflitos de versão. A v1 foi preservada. Nenhuma alteração em Core, providers ou produção.',
'Campos reais do contrato instalado inspecionados por AST; distinções e valores esperados fixados manualmente; conversão Decimal contra Fraction. São referências de método, não outro auditor nem prova externa de identidade. Símbolo/source podem codificar informação: ausência de campo tipado não prova colisão real em produção.',
'Zero colisões nos quatro pares; rejeição explícita dos inputs inválidos; revisão100 antes da recepção e90 depois; 100USDT tornam-se97USD apenas com FX admitido.',
'Sem preços/taxas pessoais ou PnL. O câmbio0,97 é controle sintético de não paridade. Hash com formato correto não prova que o conteúdo do provider seja verdadeiro.',
'Seis controles adicionais pré-registrados: preço em unidade errada; inverso liquidando na quote; quantidade spot em quote; hash não hexadecimal; revisões conflitantes no mesmo relógio; montanteNaN. A v1 aceitou os seis indevidamente.',
'Todos os contrastes originais e os seis adversariais devem satisfazer as expectativas, sem conversão implícita ou escolha silenciosa de versão ambígua.',
'Qualquer aceitação indevida rejeita esta versão do adapter. Foi o caso da v1; sua aprovação inicial era insuficiente.',
'Metadata de provider ausente ou não comprovável bloqueia uso econômico. Opções/quanto e formas não suportadas são recusadas: não se declara identidade universal completa.',
'V1: testes iniciais passaram, mas0/6 rejeições adversariais. V2:6/6 rejeições e controles originais aprovados. Diferenças de instrumentos e receipt tardio preservadas; multiplicador1 e1,0 normalizados. PASS_NARROW_ENGINEERING após correção.',
'K01 permanece prioridade e ganha adapter experimental verificável. Fortalece a exigência de contrato explícito; não muda mercados, snapshots ou hipóteses existentes. F01 não certifica histórico PIT de nenhum provider.',
'G2 técnico: mapear um par spot/perp e duas versões de um dado real com recibos preservados, verificar round-trip de unidades/identidade e falhar quando metadata faltar. G3 só após essa avaliação; sem integração nesta fase.'],
'F02':[
'Uma rota archive acessível, distinta e com proveniência documentada pode corroborar os mesmos38 blocos/índices Aave.',
'Se a renda reproduzida da primeira fonte também corresponde a respostas de uma segunda rota e à implementação histórica correta.',
'1728 fluxos reconciliados na fase1. A tentativa BlockREQ terminou ConnectTimeout na primeira chamada,0 bytes;38 fronteiras e código do protocolo permaneceram fixados.',
'Nesta fase apenas hashes de protocol/started/result e inventário de raw. Não existe resposta bem-sucedida nova no diretório da tentativa. Nenhuma série nova ou período alternativo foi consultado.',
'f02 verifica que os arquivos do bloqueio continuam idênticos à baseline; não reexecuta o coletor consumido. Não foi procurado um novo conjunto de endpoints.',
'A segunda rota independente ainda não forneceu dados. A verificação de hash é controle de preservação, não corroboração econômica ou independência de backend.',
'Para corroboração:38/38 fronteiras com hashes de bloco, índice, identidade e implementação verificáveis. Nesta fase:0 fronteiras novas verificadas.',
'0 chamadas novas e0 quota consumida. Sem custos pessoais, capital ou execução.',
'Uma divergência real de bloco, índice ou identidade falsificaria a claim correspondente. Timeout não executa esse teste.',
'Todas as fronteiras coincidem e a procedência limita corretamente o que significa independência. Não atendido nesta fase.',
'Rejeição somente mediante divergência substantiva confirmada. Não houve tal evidência.',
'Acesso sem mudança comprovada, respostas ausentes ou proxy/bytecode histórico não identificado.',
'BLOCKED_ACCESS_UNCHANGED / INCONCLUSIVE. Recibos anteriores íntegros;0 novos dados e0 chamadas. Não se afirma que o endpoint continua mundialmente indisponível: não foi testado novamente.',
'Mantém K03 BLOCKED_DATA e a avaliação histórica condicional. Não enfraquece nem fortalece o retorno pelo simples erro de infraestrutura.',
'Apenas após mudança comprovada de acesso, novo protocolo complementar para os mesmos38 blocos e mapeamento proxy/implementation. Nada de repetir automaticamente a tentativa antiga.'],
'F03':[
'O painel retrospectivo disponível pode sustentar um novo universo/ranking residual sem reconstruir elegibilidade a partir de conhecimento posterior.',
'Se os dados existentes realmente satisfazem o gate PIT, incluindo moedas retiradas, versões tardias e escopo além do filtro direcional.',
'Painel antigo de727447 linhas e661 pares, já explorado;140 semanas previamente vistas não são holdout. Registro existente de13 eventos de identidade é restrito a observações censuradas.',
'Metadados de aquisição de todos os pares; amostras determinísticas de schema BTCUSDT/ETHUSDT/FTTUSDT; USDCUSDT ausente. Leitura somente de schema, proveniência, datas e lacunas; nenhum preço/retorno/ranking calculado. Foram inspecionados open_ms/close_ms, finalized_at_utc e a finalidade declarada de identity_events.',
'f03 compara controles de universo as-of e inventaria evidência. A revisão semantic_gate.py corrige o diagnóstico inicial por nomes: open_ms representa event_at, finalized_at é aquisição, symbol pode representar parte da identidade. Campo com outro nome não é tratado como informação inexistente.',
'Quatro universos esperados fixados manualmente em decisões9/12/15/21, com listagem conhecida tarde, delisting eUSDC incluída. Controle negativo aplica sobreviventes atuais ao passado. Não há referência independente de publicação histórica para todo o painel.',
'100% dos dados usados pelo novo experimento precisam de evidência temporal/eligibilidade; zero erros nos controles sintéticos. Percentual real admissível permanece UNKNOWN, não0% por ausência de nomes de campos.',
'0 aquisição nova. Hedge/borrow, fees e período não usado continuam sem contrato admissível para a nova hipótese; não estimamos retorno ou custo retroativamente.',
'Aplicar universo atual às decisões antigas deve ser detectado. Exigir que publicação/recepção tardias não retrocedam; verificar que registros parciais de eventos não virem catálogo completo.',
'Gate econômico somente se informação disponível em cada decisão e universo por data forem demonstrados para todas as linhas usadas. Controle sintético sozinho não atende isso.',
'Rejeitar o uso deste pacote como prova PIT/holdout de uma nova hipótese quando faltam os contratos exigidos. Não rejeitar ranking residual, estudos antigos ou existência histórica de informação pública.',
'Publicação original e elegibilidade histórica não comprovadas; datas de aquisição posterior não resolvem o passado; ausência de avaliação reservada e hedge admissível.',
'Controles as-of4/4 corretos; sobreviventes atuais erraram em3/4 decisões. Metadados mantêm542 dias ausentes somados; USDC ausente na amostra. O catálogo de13 eventos declara historical_feature_use=false e escopo incompleto. BLOCKED_DATA para experimento econômico novo.',
'K04 continua bloqueada com causa concreta; K01 demonstra valor como gate. Nenhum sinal/peso/modelo foi recalculado, nenhum resultado congelado reinterpretado.',
'G1 de aquisição/PIT: definir catálogo de elegibilidade e recibos observáveis, tratamento de delisting e um período ainda não exposto. Só depois protocolar duas variantes de ranking e hedge financiado.'],
'F04':[
'Fill parcial da segunda perna e caixa segregado podem eliminar a vantagem bruta de um hedge que parece favorável com preenchimento total.',
'Se o cálculo conserva caixa/quantidade por venue e se o resultado sobrevive a posições residuais e desmonte adverso.',
'B04/B06 da fase1 validaram VWAP publicado e comissão/hedge completo. Não modelavam probabilidade de fill parcial nem a trajetória do caixa por perna.',
'Nove cenários sintéticos: fill futuro0/0,5/1BTC e atraso0/1/10s. Spot compra1BTC a100; futuro vende a101; preços de desmonte residual100/99/95 são impostos pelo protocolo. Parte casada fecha a100 em86400s. Não são livros reais nem distribuição de latência estimada.',
'Ledger Decimal com caixa spot110USD e futuro50USD, inventário, short e margem bloqueada. Registra cada compra/venda/fee/liberação; proíbe venda spot sem estoque e compensação automática de caixa entre venues.',
'Fórmula fechada em Fraction calcula fluxos separadamente do ledger de eventos; zero erro até tolerância1e−10. Método alternativo pelo mesmo agente, não engine externo independente nem auditor financeiro.',
'Conservação de caixa/PnL em9/9; posição final zerada; nenhum caixa livre negativo; duas violações recusadas; resultado por cenário e capital imobilizado reportados.',
'Capital total160USD; comissão0,1% de quote por fill; margem20% do notional de entrada. Funding/juros são zero no cenário-base, sem tarifa pessoal conhecida. Custos adicionais toleráveis são calculados como break-even, não estimados como disponíveis. Não modela chamadas de margem intraperíodo, default, FX, impacto ou tributação.',
'Conta futura com caixa0 deve recusar margem mesmo havendo160 no spot; não permitir vender BTC não adquirido. Resultado parcial/adverso deve ser confrontado com o caso ideal completo.',
'9/9 resultados batem com a fórmula e os controles são recusados. A robustez econômica do exemplo exigiria resultado positivo nos cenários de stress especificados.',
'Erro de reconciliação rejeita o ledger. Resultado líquido<=0 rejeita robustez daquele cenário/alegação, não toda estratégia de carry.',
'Sem L2/trades/fees/latência empíricos, não estimar fill rate, probabilidade de lucro, capacidade ou risco de liquidação real.',
'Contabilidade aprovada9/9; duas violações recusadas. PnL entre−5,195 e+0,599USD;4/9 cenários positivos, contagem sem significado probabilístico. Fill completo: +0,599USD; com metade e1s adverso, lucro desaparece. Robustez do exemplo não demonstrada.',
'K06/K11 ganham diagnóstico incremental de quantidade/caixa por perna. Enfraquece a conclusão baseada apenas no spread bruto/full fill. Não muda o piloto carry congelado.',
'G2 técnico de execução: incluir marks/chamadas de margem, funding e desmonte com recibos admissíveis. Sem dados, permanecer em limites de cenário; sem integração ou capital.'],
'F05':[
'Dependência temporal e seleção do melhor resultado tornam intervalos IID e p-valores isolados excessivamente otimistas.',
'Quanto esses procedimentos falham em controles conhecidos; se bloco fixo e ajuste familiar atendem critérios registrados; se labels publicados tarde sobrevivem à purga.',
'B05 mostrou limitação de gap por linha; PBO/DSR existentes não foram reexecutados. Não há matriz completa de perdas/labels de uma nova família econômica admissível.',
'AR(1) gaussiano estacionário: rho0,6,160 pontos,400 séries, seeds fixas; bootstrap circular de bloco8 com299 resamples, nominal95%. Multiplicidade:8 blocos,4 candidatos fixos,256 sinais conjuntos enumerados. Labels sintéticos com término longo e disponibilidade atrasada.',
'Comparação de intervalo normal IID, intervalo de covariância conhecida e bootstrap de bloco8; seleção por maior média, teste individual versus maxT; gate end/available antes de três cortes. Nenhum ajuste de bloco, seed, n ou família após observar resultados.',
'Variância analítica AR1 contra soma da matriz de covariância; randomização vetorizada contra enumeração escalar. Referência conhecida é oracle sintético, não estimador disponível para mercado. MaxT é avaliado sob nulidade global e simetria conjunta de sinais por bloco; não prova controle forte em qualquer nulidade parcial.',
'Cobertura e largura dos intervalos, erro MonteCarlo, erro familiar exato a5%, zero labels proibidos após gate. Critério registrado: oracle entre90–99%, procedimento de intervalo rejeitado se cobertura<90%, maxT erro<=5%.',
'Retornos sintéticos sem custos/escala de negociação. Observações correlacionadas não são160 unidades independentes: tamanho equivalente do oracle≈40,47. Em dados econômicos, método deve usar PnL líquido e registrar todas as escolhas.',
'Intervalo nominal95% IID deve ser confrontado com verdade conhecida; escolher o melhor de quatro sem desconto deve elevar erro familiar; label com publicação tardia deve ser excluído ainda que tenha terminado.',
'Oracle satisfaz faixa registrada, maxT<=5%, referências numéricas e controles de labels passam. Uma técnica aproximada só atende confiabilidade aqui se cobertura>=90%.',
'Cobertura<90% rejeita suficiência daquele procedimento no DGP testado. Erro familiar>5% rejeita a decisão selecionada sem correção. Não universalizar a outras dependências.',
'Covariância real, estacionariedade, block-size adequado e histórico completo de busca não são conhecidos para a nova família. Não calcular CI econômico, SPA ou promoção científica com estes controles.',
'IID248/400=62%; oracle374/400=93,5%; bloco8:345/400=86,25%. IID e bloco8 reprovam critério90%. Seleção sem correção41/256=16,0156%; maxT12/256=4,6875%. Referências numéricas concordam; gate remove labels proibidos nos três cortes.',
'K05 ganha evidência experimental contra independência presumida, bloco escolhido por conveniência e significância após seleção. O bootstrap8 não foi ajustado para passar. Não altera resultados de trials fechadas nem valida lucro.',
'G2 metodológico condicionado ao DGP/labels reais de uma família nova: plano de incerteza e registro de seleção antes de abrir resultados. Controle sintético favorável do maxT não basta para transferi-lo automaticamente.']}
assert all(len(v)==15 for v in specs.values())
states={'F01':'READY_FOR_EXPERIMENT_G2_TECHNICAL','F02':'BLOCKED_DATA','F03':'BLOCKED_DATA','F04':'INCONCLUSIVE_ECONOMIC_ROBUSTNESS','F05':'INCONCLUSIVE_MARKET_INFERENCE'}
registry={'initiative':'20260911T0233','phase':2,'created_at':datetime.datetime.now(datetime.UTC).isoformat(),'baseline_head':results['seed_and_design']['head'],'mode':'EXPERIMENTAL_VALIDATION','experiments':[{'id':k,'state':states[k],'C':'C4' if k in ['F01','F04','F05'] else 'C3' if k=='F03' else 'C0','C_scope':'only isolated tests/inspection described; no economic validation implied','fields':dict(zip(fields,v))} for k,v in specs.items()],'attempts':[
{'id':'P2-01','protocol':'PROTOCOL.json','result':'RESULTS.json','type':'fixed synthetic/metadata run','economic_trials':0},
{'id':'P2-F01-V1','protocol':'ADVERSARIAL_PROTOCOL.json','result':'F01_ADVERSARIAL_V1.json','outcome':'six initial adapter defects exposed'},
{'id':'P2-F01-V2','protocol':'ADVERSARIAL_PROTOCOL.json','result':'F01_ADVERSARIAL_V2.json','outcome':'isolated adapter repaired; six controls and original F01 pass'},
{'id':'P2-F03-SEMANTIC','protocol':'ADVERSARIAL_PROTOCOL.json','result':'F03_SEMANTIC_GATE.json','outcome':'field aliases recognized; temporal/eligibility evidence still insufficient'}],
'independence':'No subagents, external assessor or new external engine. Methodologically different analytical controls, same author. Empirical economic independent-source claim remains unavailable.',
'economic_promotion':False,'prospective_validation_sufficient_now':False,'new_network_calls':0,'capital_permission':False,'orders':0}
save(OUT/'REGISTRY.json',registry)
detail='# Fase2 — fichas dos cinco experimentos\n\nIniciativa20260911T0233; baseline e artefatos da fase1 preservados. Todos os15 campos solicitados aparecem em cada ficha. C refere-se ao teste isolado, nunca à capacidade inteira.\n\n'
for k,v in specs.items():
 detail+=f'## {k} — {states[k]}\n\n'
 for label,value in zip(fields,v):detail+=f'**{label}**\n\n{value}\n\n'
(OUT/'EXPERIMENTS.md').write_text(detail,encoding='utf-8')
answers=[
['1. Incertezas efetivamente eliminadas','Nos casos testados: distinção de quatro identidades, bloqueio de revisões/FX não disponíveis, seis falhas do adapter experimental, conservação de caixa em nove cenários e efeitos de dependência/seleção sob nulidade conhecida. Não eliminamos incerteza sobre verdade dos providers ou lucro.'],
['2. Hipóteses enfraquecidas/rejeitadas','Rejeitada suficiência da v1 de identidade; rejeitados IID e bootstrap8 para cobertura mínima90% no DGP fixado; rejeitada significância individual do candidato escolhido como controle familiar; enfraquecida robustez de spread positivo com fill ideal. Ranking residual e Aave não foram refutados economicamente.'],
['3. Valor incremental demonstrado','F01 passa a recusar inconsistências antes silenciosas; F03 impede transformar catálogo parcial/acesso tardio em universo PIT; F04 torna visíveis exposição residual e caixa indisponível por venue; F05 quantifica erro inferencial em controles verificáveis.'],
['4. Resultados inconclusivos','Corroboração Aave/implementation histórica; PIT do universo completo e ranking residual; probabilidade/custo real de fills; risco de margem intraperíodo; método de incerteza adequado à nova família em mercado.'],
['5. Hipóteses econômicas prontas para experimento completo','Nenhuma recebeu promoção econômica G2 nesta fase. Aave continua candidata condicional; ranking espera gate PIT/hedge; carry espera dados de execução e protocolo preservado. Há justificativa para G2 técnico de F01 e F04, o que não equivale a um backtest econômico completo.'],
['6. Próximo experimento de maior valor informacional','F01 com dados reais já preservados: mapear spot/perp e versões de um dado, incluindo unidades/settlement e recibos. Sucesso: round-trip sem perda, zero inferência monetária implícita, rejeição dos campos ausentes e das versões futuras. Isso decide se o contrato habilita F03/F04 sem nova coleta ampla.'],
['7. Evidência suficiente para validação prospectiva?','Não para promover qualquer nova hipótese econômica nesta fase. Os controles justificam aprofundamento técnico. Pilotos prospectivos previamente congelados mantêm suas próprias condições/janelas, sem ativação ou alteração aqui. Nenhuma evidência E6-P nova.']]
registry['answers']=answers
save(OUT/'REGISTRY.json',registry)
report='''# Cripto Predictor — fase2: validação experimental

**A fase reduziu incertezas de engenharia e inferência, mas não liberou uma nova hipótese econômica para validação prospectiva.** Os testes encontraram falhas reais no adapter experimental inicial e mostraram por que dependência, seleção e execução parcial precisam entrar na decisão.

Não houve novo discovery, repetição da auditoria/suíte anterior, nova chamada de mercado, ordem, conta, instalação ou alteração de protocolo congelado. O protocolo principal foi registrado antes do primeiro resultado. A revisão adversarial teve protocolo adicional e preservou os resultados que falharam.

## Resultado por experimento

'''+table(['Experimento','Evidência produzida','Decisão'],[
['F01 — identidade','4 pares distintos; revisão tardia/FX verificados; v1 falhou em6/6 controles adversariais, v2 rejeita6/6 e mantém os controles originais','Adapter experimental corrigido e candidato a G2 técnico; não integrado'],
['F02 — Aave','Hashes e bloqueio anterior confirmados; nenhum recibo novo;0 chamadas','BLOCKED_DATA; infraestrutura não virou rejeição científica'],
['F03 — universo PIT','4/4 universos sintéticos corretos; filtro de sobreviventes atuais errado em3/4; revisão semântica do painel antigo','Sem prova PIT completa para novo ranking; não calculamos IC/PnL'],
['F04 — execução/capital','9/9 cenários reconciliados;2 violações recusadas; PnL−5,195 a+0,599USD','Contabilidade demonstrada; robustez econômica não'],
['F05 — incerteza/seleção','400 séries AR1 e256 randomizações exatas; bloqueio de labels tardios','IID e bloco8 insuficientes no controle; maxT passa sob nulidade especificada']])
report+='''## O que mudou na avaliação

**Identidade não é apenas adicionar campos.** A primeira versão separava quote/chain/venue/payoff, mas aceitava unidades incoerentes, liquidação incompatível, hash inválido, valores monetários não finitos e revisões conflitantes. Seis controles novos falsificaram sua suficiência. A correção v2 ocorreu somente no adapter de pesquisa; falhas, código antigo e hashes foram mantidos. Opções e contratos fora do escopo são recusados, em vez de receber uma identidade incompleta por aproximação.

**O gate PIT é semântico.** A primeira leitura por nomes de campos era excessivamente estrita; corrigimos essa interpretação. open_ms e finalized_at têm informação útil, mas fechamento do candle e aquisição posterior não comprovam primeira publicação histórica. O painel contém661 pares e727447 linhas; seus metadados registram542 dias ausentes somados. BTC/ETH/FTT estão nas amostras, USDC não; isso descreve esse painel, não toda a cobertura possível. O registro de13 eventos é explicitamente parcial e pós-hoc. Nenhum resultado antigo foi reclassificado, e a ausência de evidência não foi convertida em0% de dados válidos.

**O caixa da outra venue não está automaticamente disponível.** O ledger mantém110USD no spot e50USD no futuro. Recusa margem na venue futura com caixa0 mesmo havendo dinheiro no spot. Uma perna incompleta deixa exposição residual e pode consumir todo o ganho aparente. Custos, atrasos e preços de desmonte são cenários impostos, não estimativas de mercado.

'''+table(['Fill futuro','Atraso(s)','Desmonte residual','PnL líquidoUSD','Conciliação'],[(c['fill_fraction'],c['delay_seconds'],c['orphan_unwind_price'],c['net_pnl_usd'],'PASS' if c['pass'] else 'FAIL') for c in rs['F04']['cases']])
report+='''Quatro dos nove cenários são positivos; isso não é uma chance estimada de lucro. O melhor resultado,0,599USD sobre160USD de capital total, é também o teto de custos adicionais que esse exemplo suporta antes de perder o ganho. Funding e juros foram zero por hipótese; margem intraperíodo, default e impacto não foram simulados. Não é evidência de carry executável.

## Incerteza e multiplicidade: resultado controlado

O processo sintético AR(1) usa rho0,6 e160 pontos por série. Pela covariância conhecida, isso equivale a aproximadamente40,47 observações independentes para estimar a média. O oracle existe porque geramos o processo; não está disponível por decreto em dados reais.

'''+table(['Intervalo nominal95%','Cobertura em400 séries','Erro MonteCarlo(1SE)','Largura média','Critério>=90%'],[(x['method'],f"{x['covered']}/400 ({100*x['coverage']:.2f}%)",f"{100*x['mc_standard_error']:.2f} pontos percentuais",f"{x['mean_interval_width']:.4f}",'PASS' if x['registered_coverage_threshold_pass'] else 'REJECT neste DGP') for x in rs['F05']['intervals']])
report+='''O intervalo IID cobriu apenas62% e o bootstrap circular com bloco8 cobriu86,25%. Ambos falharam o critério registrado; não ajustamos o bloco depois para tornar o resultado favorável. O intervalo de covariância conhecida cobriu93,5%, dentro da faixa do controle.

Ao selecionar a maior média entre quatro candidatos, o teste individual rejeitou indevidamente41/256 padrões de sinais (16,0156%). A correção maxT rejeitou12/256 (4,6875%), abaixo do limite5% no desenho exato. Isso vale para a nulidade global e a simetria de sinais por bloco definidas; não prova validade sob dependência arbitrária, seleção não registrada ou nulidades parciais.

Também foram eliminados labels cujo término ou recepção ocorre no corte ou depois dele. Remover apenas labels longos não basta quando a informação chega atrasada. Não aplicamos nenhum desses resultados a uma trial encerrada nem calculamos significância econômica com uma matriz incompleta de tentativas.

## Respostas às sete perguntas finais

'''+table(['Pergunta','Resposta'],answers)
report+='''## Próxima decisão concreta

Priorizar **F01 em recibos reais preservados**, com teste de round-trip e falsificação de metadata, antes de novo ranking ou replay econômico. O teste deve falhar quando a evidência não representa instrumento/unidade/versão — não inventar a informação faltante. F02 só volta à execução após mudança comprovada de acesso. Para F05, não reutilizar o mesmo exercício até achar um bloco que passe.

Os estudos históricos favoráveis mantêm seu alcance original. A fase2 não acrescentou lucro observado, corroboração de segunda fonte ou evidência prospectiva. A conclusão é avançar em validação técnica específica, mantendo bloqueados os saltos econômicos que os dados ainda não sustentam.

## Rastreabilidade

- [Fichas completas](EXPERIMENTS.md): os15 campos solicitados para F01–F05.
- [Registro estruturado](REGISTRY.json): resultados, estados e respostas finais.
- [Protocolo principal](PROTOCOL.json) e [protocolo adversarial](ADVERSARIAL_PROTOCOL.json).
- [Resultados iniciais](RESULTS.json), [F01 v1 reprovada](F01_ADVERSARIAL_V1.json), [F01 v2](F01_ADVERSARIAL_V2.json) e [gate semântico F03](F03_SEMANTIC_GATE.json).
- [Preservação](PRESERVATION.json) e [manifesto](MANIFEST.json).

Nenhum revisor externo participou. Controles analíticos usam métodos distintos, mas foram implementados pelo mesmo agente. Nenhuma independência empírica inexistente é atribuída a essa concordância.
'''
# Improve spacing in prose without altering identifiers/URLs or decimal notation.
import re
def polish(s):
 parts=re.split(r'(`[^`]*`|\]\([^)]*\)|https?://\S+)',s)
 for i in range(0,len(parts),2):
  t=parts[i];t=re.sub(r'\b([a-zà-ÿ]{2,}|e)(?=\d)',r'\1 ',t);t=re.sub(r';(?=\S)','; ',t);t=re.sub(r',(?=[A-Za-zà-ÿ])',', ',t);t=re.sub(r'(?<=\d)(USD|USDT|BTC|UTC|SE)\b',r' \1',t);parts[i]=t
 return ''.join(parts)
(OUT/'REPORT.md').write_text(polish(report),encoding='utf-8')
(OUT/'EXPERIMENTS.md').write_text(polish(detail),encoding='utf-8')
for p in R.glob('*.json'):shutil.copy2(p,OUT/p.name)
# Keep phase1 baseline snapshot distinct from this phase's canonical experiment registry.
save(OUT/'REGISTRY.json',registry)
(OUT/'reproduction').mkdir(exist_ok=True)
for p in (R/'work').glob('*.py'):shutil.copy2(p,OUT/'reproduction'/p.name)
old=read(R.parent/'baseline.json')
checks={p:sha(P/p)==h for p,h in old['preservation'].items()}
changes=[x['path'] for x in old['inventory'] if sha(P/x['path'])!=x['sha256']]
inputs={p:sha(pathlib.Path(p))==h for p,h in read(R/'BASELINE.json')['inputs'].items()}
data_checks={p:sha(pathlib.Path(p))==h for p,h in rs['F03']['input_hashes'].items()}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()
assert all(checks.values()) and all(inputs.values()) and all(data_checks.values()) and not changes and head==old['head']
pres={'observed_at':datetime.datetime.now(datetime.UTC).isoformat(),'head':head,'baseline_files_unchanged':inputs,'protected_files_unchanged':checks,'data_samples_unchanged':data_checks,'python_source_files_verified':len(old['inventory']),'python_changes':changes,'network_calls':0,'quota_mutations':0,'orders':0,'prior_phase_results_unchanged':True,'new_research_code_only':True,'passed':True}
save(OUT/'PRESERVATION.json',pres)
# Snapshot the completed phase1 report before adding only a continuation pointer.
shutil.copy2(D/'REPORT.md',OUT/'phase1_report_snapshot.md')
mf=[{'path':p.relative_to(OUT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']
save(OUT/'MANIFEST.json',{'initiative':'20260911T0233','phase':2,'files':mf,'validation':'5 experiments x15 fields; initial and adversarial failure/success preserved; no stochastic rerun; baseline/protected/source/data hashes checked'})
# Link the same initiative to its new phase, preserving phase1 snapshots and outcomes.
main=read(D/'REGISTRY.json');main.setdefault('phases',[]).append({'phase':2,'registry':'phase2/REGISTRY.json','report':'phase2/REPORT.md','manifest_sha256':sha(OUT/'MANIFEST.json'),'completed_at':pres['observed_at'],'economic_promotion':False})
save(D/'REGISTRY.json',main)
current=(D/'REPORT.md').read_text(encoding='utf-8')
(D/'REPORT.md').write_text('> Continuação concluída: [Fase2 — validação experimental](phase2/REPORT.md). O texto abaixo preserva a análise da fase1.\n\n'+current,encoding='utf-8')
main_mf=[{'path':p.relative_to(D).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(D.rglob('*')) if p.is_file() and p!=D/'MANIFEST.json']
save(D/'MANIFEST.json',{'run_id':'20260911T0233','revision':'PHASE2_LINKED','files':main_mf,'prior_manifest_snapshot':'phase2/phase1_manifest_snapshot.json'})
dest=pathlib.Path('C:/Users/leona/Documents/Codex/2026-09-10/le/outputs/cripto-fase2-20260911');dest.mkdir(parents=True,exist_ok=True)
shutil.copytree(OUT,dest/'relatorio',dirs_exist_ok=True)
with zipfile.ZipFile(dest/'cripto-fase2.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (dest/'relatorio').rglob('*'):
  if p.is_file():z.write(p,p.relative_to(dest/'relatorio'))
for row in mf:assert sha(dest/'relatorio'/row['path'])==row['sha256']
save(dest/'ENTREGA.json',{'report':str(dest/'relatorio/REPORT.md'),'package_sha256':sha(dest/'cripto-fase2.zip'),'source_preserved':True,'phase':2})
print(json.dumps({'report':str(dest/'relatorio/REPORT.md'),'files':len(mf)+1,'source_preserved':True,'economic_promotion':False}))
