# Fase2 — fichas dos cinco experimentos

Iniciativa20260911T0233; baseline e artefatos da fase 1 preservados. Todos os 15 campos solicitados aparecem em cada ficha. C refere-se ao teste isolado, nunca à capacidade inteira.

## F01 — READY_FOR_EXPERIMENT_G2_TECHNICAL

**HIPÓTESE**

Identidade explícita, unidades coerentes e versões por publicação/recepção impedem mistura de instrumentos e uso de informação ainda não disponível.

**INCERTEZA QUE SERÁ REDUZIDA**

Se distinguir nomes é suficiente ou se ainda passam erros de unidade, liquidação, revisão e conversão monetária.

**BASELINE**

MarketDataPoint instalado e snapshot da fase 1; B03 cobriu clocks/preço, sem identidade econômica completa. Não repetimos B03 nem a suíte inteira.

**DADOS E CONTRATO TEMPORAL**

Fixtures sintéticas: quatro pares distintos (quote, payoff/liquidação, chain, venue), dois relógios inválidos, revisão recebida depois da publicação, câmbio explícito USDT/USD0,97. Tempos são inteiros relativos; não observações de mercado. Instrumento fixa venue, mercado, base/quote/settlement, chain/contrato, vencimento, multiplicador, payoff e unidades.

**IMPLEMENTAÇÃO**

Instrument/Observation, asof e convert no adapter isolado work/experiments.py. Após controles adversariais, v2 valida relação de unidades, settlement permitido, hash hexadecimal, montante finito e conflitos de versão. A v1 foi preservada. Nenhuma alteração em Core, providers ou produção.

**CONTROLE / REFERÊNCIA INDEPENDENTE**

Campos reais do contrato instalado inspecionados por AST; distinções e valores esperados fixados manualmente; conversão Decimal contra Fraction. São referências de método, não outro auditor nem prova externa de identidade. Símbolo/source podem codificar informação: ausência de campo tipado não prova colisão real em produção.

**MÉTRICA PRINCIPAL**

Zero colisões nos quatro pares; rejeição explícita dos inputs inválidos; revisão 100 antes da recepção e 90 depois; 100 USDT tornam-se 97 USD apenas com FX admitido.

**CUSTOS E PREMISSAS ECONÔMICAS**

Sem preços/taxas pessoais ou PnL. O câmbio 0,97 é controle sintético de não paridade. Hash com formato correto não prova que o conteúdo do provider seja verdadeiro.

**TESTE DE FALSIFICAÇÃO**

Seis controles adicionais pré-registrados: preço em unidade errada; inverso liquidando na quote; quantidade spot em quote; hash não hexadecimal; revisões conflitantes no mesmo relógio; montanteNaN. A v1 aceitou os seis indevidamente.

**CRITÉRIO DE SUCESSO**

Todos os contrastes originais e os seis adversariais devem satisfazer as expectativas, sem conversão implícita ou escolha silenciosa de versão ambígua.

**CRITÉRIO DE REJEIÇÃO**

Qualquer aceitação indevida rejeita esta versão do adapter. Foi o caso da v1; sua aprovação inicial era insuficiente.

**CRITÉRIO DE INCONCLUSÃO**

Metadata de provider ausente ou não comprovável bloqueia uso econômico. Opções/quanto e formas não suportadas são recusadas: não se declara identidade universal completa.

**RESULTADO**

V1: testes iniciais passaram, mas 0/6 rejeições adversariais. V2:6/6 rejeições e controles originais aprovados. Diferenças de instrumentos e receipt tardio preservadas; multiplicador 1 e 1,0 normalizados. PASS_NARROW_ENGINEERING após correção.

**IMPACTO SOBRE AS DECISÕES EXISTENTES**

K01 permanece prioridade e ganha adapter experimental verificável. Fortalece a exigência de contrato explícito; não muda mercados, snapshots ou hipóteses existentes. F01 não certifica histórico PIT de nenhum provider.

**PRÓXIMO GATE**

G2 técnico: mapear um par spot/perp e duas versões de um dado real com recibos preservados, verificar round-trip de unidades/identidade e falhar quando metadata faltar. G3 só após essa avaliação; sem integração nesta fase.

## F02 — BLOCKED_DATA

**HIPÓTESE**

Uma rota archive acessível, distinta e com proveniência documentada pode corroborar os mesmos 38 blocos/índices Aave.

**INCERTEZA QUE SERÁ REDUZIDA**

Se a renda reproduzida da primeira fonte também corresponde a respostas de uma segunda rota e à implementação histórica correta.

**BASELINE**

1728 fluxos reconciliados na fase 1. A tentativa BlockREQ terminou ConnectTimeout na primeira chamada,0 bytes; 38 fronteiras e código do protocolo permaneceram fixados.

**DADOS E CONTRATO TEMPORAL**

Nesta fase apenas hashes de protocol/started/result e inventário de raw. Não existe resposta bem-sucedida nova no diretório da tentativa. Nenhuma série nova ou período alternativo foi consultado.

**IMPLEMENTAÇÃO**

f02 verifica que os arquivos do bloqueio continuam idênticos à baseline; não reexecuta o coletor consumido. Não foi procurado um novo conjunto de endpoints.

**CONTROLE / REFERÊNCIA INDEPENDENTE**

A segunda rota independente ainda não forneceu dados. A verificação de hash é controle de preservação, não corroboração econômica ou independência de backend.

**MÉTRICA PRINCIPAL**

Para corroboração:38/38 fronteiras com hashes de bloco, índice, identidade e implementação verificáveis. Nesta fase:0 fronteiras novas verificadas.

**CUSTOS E PREMISSAS ECONÔMICAS**

0 chamadas novas e 0 quota consumida. Sem custos pessoais, capital ou execução.

**TESTE DE FALSIFICAÇÃO**

Uma divergência real de bloco, índice ou identidade falsificaria a claim correspondente. Timeout não executa esse teste.

**CRITÉRIO DE SUCESSO**

Todas as fronteiras coincidem e a procedência limita corretamente o que significa independência. Não atendido nesta fase.

**CRITÉRIO DE REJEIÇÃO**

Rejeição somente mediante divergência substantiva confirmada. Não houve tal evidência.

**CRITÉRIO DE INCONCLUSÃO**

Acesso sem mudança comprovada, respostas ausentes ou proxy/bytecode histórico não identificado.

**RESULTADO**

BLOCKED_ACCESS_UNCHANGED / INCONCLUSIVE. Recibos anteriores íntegros; 0 novos dados e 0 chamadas. Não se afirma que o endpoint continua mundialmente indisponível: não foi testado novamente.

**IMPACTO SOBRE AS DECISÕES EXISTENTES**

Mantém K03 BLOCKED_DATA e a avaliação histórica condicional. Não enfraquece nem fortalece o retorno pelo simples erro de infraestrutura.

**PRÓXIMO GATE**

Apenas após mudança comprovada de acesso, novo protocolo complementar para os mesmos 38 blocos e mapeamento proxy/implementation. Nada de repetir automaticamente a tentativa antiga.

## F03 — BLOCKED_DATA

**HIPÓTESE**

O painel retrospectivo disponível pode sustentar um novo universo/ranking residual sem reconstruir elegibilidade a partir de conhecimento posterior.

**INCERTEZA QUE SERÁ REDUZIDA**

Se os dados existentes realmente satisfazem o gate PIT, incluindo moedas retiradas, versões tardias e escopo além do filtro direcional.

**BASELINE**

Painel antigo de 727447 linhas e 661 pares, já explorado; 140 semanas previamente vistas não são holdout. Registro existente de 13 eventos de identidade é restrito a observações censuradas.

**DADOS E CONTRATO TEMPORAL**

Metadados de aquisição de todos os pares; amostras determinísticas de schema BTCUSDT/ETHUSDT/FTTUSDT; USDCUSDT ausente. Leitura somente de schema, proveniência, datas e lacunas; nenhum preço/retorno/ranking calculado. Foram inspecionados open_ms/close_ms, finalized_at_utc e a finalidade declarada de identity_events.

**IMPLEMENTAÇÃO**

f03 compara controles de universo as-of e inventaria evidência. A revisão semantic_gate.py corrige o diagnóstico inicial por nomes: open_ms representa event_at, finalized_at é aquisição, symbol pode representar parte da identidade. Campo com outro nome não é tratado como informação inexistente.

**CONTROLE / REFERÊNCIA INDEPENDENTE**

Quatro universos esperados fixados manualmente em decisões 9/12/15/21, com listagem conhecida tarde, delisting eUSDC incluída. Controle negativo aplica sobreviventes atuais ao passado. Não há referência independente de publicação histórica para todo o painel.

**MÉTRICA PRINCIPAL**

100% dos dados usados pelo novo experimento precisam de evidência temporal/eligibilidade; zero erros nos controles sintéticos. Percentual real admissível permanece UNKNOWN, não 0% por ausência de nomes de campos.

**CUSTOS E PREMISSAS ECONÔMICAS**

0 aquisição nova. Hedge/borrow, fees e período não usado continuam sem contrato admissível para a nova hipótese; não estimamos retorno ou custo retroativamente.

**TESTE DE FALSIFICAÇÃO**

Aplicar universo atual às decisões antigas deve ser detectado. Exigir que publicação/recepção tardias não retrocedam; verificar que registros parciais de eventos não virem catálogo completo.

**CRITÉRIO DE SUCESSO**

Gate econômico somente se informação disponível em cada decisão e universo por data forem demonstrados para todas as linhas usadas. Controle sintético sozinho não atende isso.

**CRITÉRIO DE REJEIÇÃO**

Rejeitar o uso deste pacote como prova PIT/holdout de uma nova hipótese quando faltam os contratos exigidos. Não rejeitar ranking residual, estudos antigos ou existência histórica de informação pública.

**CRITÉRIO DE INCONCLUSÃO**

Publicação original e elegibilidade histórica não comprovadas; datas de aquisição posterior não resolvem o passado; ausência de avaliação reservada e hedge admissível.

**RESULTADO**

Controles as-of 4/4 corretos; sobreviventes atuais erraram em 3/4 decisões. Metadados mantêm 542 dias ausentes somados; USDC ausente na amostra. O catálogo de 13 eventos declara historical_feature_use=false e escopo incompleto. BLOCKED_DATA para experimento econômico novo.

**IMPACTO SOBRE AS DECISÕES EXISTENTES**

K04 continua bloqueada com causa concreta; K01 demonstra valor como gate. Nenhum sinal/peso/modelo foi recalculado, nenhum resultado congelado reinterpretado.

**PRÓXIMO GATE**

G1 de aquisição/PIT: definir catálogo de elegibilidade e recibos observáveis, tratamento de delisting e um período ainda não exposto. Só depois protocolar duas variantes de ranking e hedge financiado.

## F04 — INCONCLUSIVE_ECONOMIC_ROBUSTNESS

**HIPÓTESE**

Fill parcial da segunda perna e caixa segregado podem eliminar a vantagem bruta de um hedge que parece favorável com preenchimento total.

**INCERTEZA QUE SERÁ REDUZIDA**

Se o cálculo conserva caixa/quantidade por venue e se o resultado sobrevive a posições residuais e desmonte adverso.

**BASELINE**

B04/B06 da fase 1 validaram VWAP publicado e comissão/hedge completo. Não modelavam probabilidade de fill parcial nem a trajetória do caixa por perna.

**DADOS E CONTRATO TEMPORAL**

Nove cenários sintéticos: fill futuro 0/0,5/1 BTC e atraso 0/1/10s. Spot compra 1 BTC a100; futuro vende a101; preços de desmonte residual 100/99/95 são impostos pelo protocolo. Parte casada fecha a100 em 86400s. Não são livros reais nem distribuição de latência estimada.

**IMPLEMENTAÇÃO**

Ledger Decimal com caixa spot 110 USD e futuro 50 USD, inventário, short e margem bloqueada. Registra cada compra/venda/fee/liberação; proíbe venda spot sem estoque e compensação automática de caixa entre venues.

**CONTROLE / REFERÊNCIA INDEPENDENTE**

Fórmula fechada em Fraction calcula fluxos separadamente do ledger de eventos; zero erro até tolerância 1e−10. Método alternativo pelo mesmo agente, não engine externo independente nem auditor financeiro.

**MÉTRICA PRINCIPAL**

Conservação de caixa/PnL em 9/9; posição final zerada; nenhum caixa livre negativo; duas violações recusadas; resultado por cenário e capital imobilizado reportados.

**CUSTOS E PREMISSAS ECONÔMICAS**

Capital total 160 USD; comissão 0,1% de quote por fill; margem 20% do notional de entrada. Funding/juros são zero no cenário-base, sem tarifa pessoal conhecida. Custos adicionais toleráveis são calculados como break-even, não estimados como disponíveis. Não modela chamadas de margem intraperíodo, default, FX, impacto ou tributação.

**TESTE DE FALSIFICAÇÃO**

Conta futura com caixa 0 deve recusar margem mesmo havendo 160 no spot; não permitir vender BTC não adquirido. Resultado parcial/adverso deve ser confrontado com o caso ideal completo.

**CRITÉRIO DE SUCESSO**

9/9 resultados batem com a fórmula e os controles são recusados. A robustez econômica do exemplo exigiria resultado positivo nos cenários de stress especificados.

**CRITÉRIO DE REJEIÇÃO**

Erro de reconciliação rejeita o ledger. Resultado líquido<=0 rejeita robustez daquele cenário/alegação, não toda estratégia de carry.

**CRITÉRIO DE INCONCLUSÃO**

Sem L2/trades/fees/latência empíricos, não estimar fill rate, probabilidade de lucro, capacidade ou risco de liquidação real.

**RESULTADO**

Contabilidade aprovada 9/9; duas violações recusadas. PnL entre−5,195 e+0,599 USD; 4/9 cenários positivos, contagem sem significado probabilístico. Fill completo: +0,599 USD; com metade e 1s adverso, lucro desaparece. Robustez do exemplo não demonstrada.

**IMPACTO SOBRE AS DECISÕES EXISTENTES**

K06/K11 ganham diagnóstico incremental de quantidade/caixa por perna. Enfraquece a conclusão baseada apenas no spread bruto/full fill. Não muda o piloto carry congelado.

**PRÓXIMO GATE**

G2 técnico de execução: incluir marks/chamadas de margem, funding e desmonte com recibos admissíveis. Sem dados, permanecer em limites de cenário; sem integração ou capital.

## F05 — INCONCLUSIVE_MARKET_INFERENCE

**HIPÓTESE**

Dependência temporal e seleção do melhor resultado tornam intervalos IID e p-valores isolados excessivamente otimistas.

**INCERTEZA QUE SERÁ REDUZIDA**

Quanto esses procedimentos falham em controles conhecidos; se bloco fixo e ajuste familiar atendem critérios registrados; se labels publicados tarde sobrevivem à purga.

**BASELINE**

B05 mostrou limitação de gap por linha; PBO/DSR existentes não foram reexecutados. Não há matriz completa de perdas/labels de uma nova família econômica admissível.

**DADOS E CONTRATO TEMPORAL**

AR(1) gaussiano estacionário: rho 0,6,160 pontos,400 séries, seeds fixas; bootstrap circular de bloco 8 com 299 resamples, nominal 95%. Multiplicidade:8 blocos,4 candidatos fixos,256 sinais conjuntos enumerados. Labels sintéticos com término longo e disponibilidade atrasada.

**IMPLEMENTAÇÃO**

Comparação de intervalo normal IID, intervalo de covariância conhecida e bootstrap de bloco 8; seleção por maior média, teste individual versus maxT; gate end/available antes de três cortes. Nenhum ajuste de bloco, seed, n ou família após observar resultados.

**CONTROLE / REFERÊNCIA INDEPENDENTE**

Variância analítica AR1 contra soma da matriz de covariância; randomização vetorizada contra enumeração escalar. Referência conhecida é oracle sintético, não estimador disponível para mercado. MaxT é avaliado sob nulidade global e simetria conjunta de sinais por bloco; não prova controle forte em qualquer nulidade parcial.

**MÉTRICA PRINCIPAL**

Cobertura e largura dos intervalos, erro MonteCarlo, erro familiar exato a5%, zero labels proibidos após gate. Critério registrado: oracle entre 90–99%, procedimento de intervalo rejeitado se cobertura<90%, maxT erro<=5%.

**CUSTOS E PREMISSAS ECONÔMICAS**

Retornos sintéticos sem custos/escala de negociação. Observações correlacionadas não são 160 unidades independentes: tamanho equivalente do oracle≈40,47. Em dados econômicos, método deve usar PnL líquido e registrar todas as escolhas.

**TESTE DE FALSIFICAÇÃO**

Intervalo nominal 95% IID deve ser confrontado com verdade conhecida; escolher o melhor de quatro sem desconto deve elevar erro familiar; label com publicação tardia deve ser excluído ainda que tenha terminado.

**CRITÉRIO DE SUCESSO**

Oracle satisfaz faixa registrada, maxT<=5%, referências numéricas e controles de labels passam. Uma técnica aproximada só atende confiabilidade aqui se cobertura>=90%.

**CRITÉRIO DE REJEIÇÃO**

Cobertura<90% rejeita suficiência daquele procedimento no DGP testado. Erro familiar>5% rejeita a decisão selecionada sem correção. Não universalizar a outras dependências.

**CRITÉRIO DE INCONCLUSÃO**

Covariância real, estacionariedade, block-size adequado e histórico completo de busca não são conhecidos para a nova família. Não calcular CI econômico, SPA ou promoção científica com estes controles.

**RESULTADO**

IID248/400=62%; oracle 374/400=93,5%; bloco 8:345/400=86,25%. IID e bloco 8 reprovam critério 90%. Seleção sem correção 41/256=16,0156%; maxT12/256=4,6875%. Referências numéricas concordam; gate remove labels proibidos nos três cortes.

**IMPACTO SOBRE AS DECISÕES EXISTENTES**

K05 ganha evidência experimental contra independência presumida, bloco escolhido por conveniência e significância após seleção. O bootstrap 8 não foi ajustado para passar. Não altera resultados de trials fechadas nem valida lucro.

**PRÓXIMO GATE**

G2 metodológico condicionado ao DGP/labels reais de uma família nova: plano de incerteza e registro de seleção antes de abrir resultados. Controle sintético favorável do maxT não basta para transferi-lo automaticamente.

