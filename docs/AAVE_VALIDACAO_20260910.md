# Aave USDC: resultado histórico positivo e limites da validação

A busca de lucro produziu uma candidata com resultado histórico positivo após custos modelados: **fornecer USDC nativo ao Aave V3 Arbitrum, sem tomar empréstimo nem alavancar**. A evidência desta rodada aprova o critério histórico registrado; **não comprova lucro pessoal, lucro futuro ou uma operação realizada pelo dono**.

## Resultado com todo o capital contabilizado

Cada cenário anual começa com **5.000 USDC no total**: 4.945 aplicados e 55 reservados para despesas. Esses 55 correspondem a 30 de execução completa e 25 de infraestrutura no ano. A reserva não rende juros e é consumida até a saída. Impostos, conversão/bridge e despesas pessoais adicionais continuam sujeitos a cenários separados. USDC não é tratado como USDT, dólar ou real.

| Período fixo, UTC | Juros calculados sobre 4.945 USDC | Custos reservados | Resultado após esses custos | Patrimônio final |
|---|---:|---:|---:|---:|
| 01/06/2024–01/06/2025 | 287,413985 | 55 | **+232,413985 USDC** | 5.232,413985 |
| 01/06/2025–01/06/2026 | 165,170571 | 55 | **+110,170571 USDC** | 5.110,170571 |

São duas alternativas anuais independentes de capital, não duas parcelas a somar. Um cenário distinto de permanência por 24 meses, com 4.920 aplicados e 80 reservados, terminou em **+379,847998 USDC** após os custos registrados. Isso é acumulado de dois anos, não renda mensal.

Com **100 USDC adicionais de despesas reservadas dentro dos mesmos 5.000**, os resultados anuais ficam em **+126,601770 e +6,830418 USDC**. Esses 100 são uma sensibilidade condicional, não uma estimativa de impostos ou uma certificação de custos particulares. Com apenas **1.000 USDC de capital total**, o mesmo cenário de 55 de custos resulta em **−0,074578 e −23,435554 USDC**. A escala de capital altera a decisão; não foi escolhida uma variante perdedora como lucrativa.

A primeira conta da rodada aplicava 5.000 e descontava custos ao final, sem financiar seu momento de pagamento. Ela foi preservada. A [correção contábil](evidence/aave_validation_20260910/funded_costs/accounting-amendment.json) reservou os custos dentro do capital inicial e reduziu os resultados. Os valores acima são os corrigidos. As 1.728 reconciliações combinam os mesmos capitais, janelas e cenários registrados; não são 1.728 estratégias independentes testadas.

## O que foi medido e conferido

- O [protocolo](evidence/aave_validation_20260910/history/protocol.json) fixou, antes da aquisição, uma única reserva, 25 fronteiras mensais entre junho de 2024 e junho de 2026, dois anos principais e diagnósticos de meses, trimestres e anos sobrepostos. Não houve busca pelo melhor começo, threshold ou pool depois do resultado.
- A coleta completou os 25 pontos em **364 chamadas RPC e 412.019 bytes**, sem retries. Em cada ponto: chain ID, último bloco antes/no horário, bloco sucessor, hashes, pool, USDC nativo, aToken, seis decimais, índice, reconstrução do índice, liquidez não emprestada, pausa, congelamento e limite de oferta.
- Todas as entradas e saídas principais cabiam na configuração e no caixa observados. O menor caixa mensal observado foi **15.603.479,219877 USDC**. Isso não prova disponibilidade entre pontos, nem garante execução futura.
- Os saldos foram reconciliados por inteiros e por frações racionais, incluindo arredondamentos conservadores. O teste publicado liga cada índice usado ao respectivo `eth_call` bruto, e recalcula aplicação, reserva, despesa, juros e patrimônio final.
- Treze testes sintéticos passaram antes da aquisição. A primeira execução detectou uma comparação de precisões decimais diferentes no teste; a referência foi corrigida para frações exatas e ambas as execuções ficaram preservadas. Não houve alteração de resultado de mercado para aprovar teste.

Os dados novos são uma **extensão retrospectiva com janelas fixas**. A escolha da candidata já foi influenciada pelo histórico recente de 84 dias e pelos resultados anteriores do projeto. Portanto, esta rodada não é um teste prospectivo nem uma validação temporal fora da amostra. Há somente dois períodos anuais sem sobreposição; os 13 anos móveis não são 13 amostras independentes. Não foi calculada uma probabilidade de lucro futuro.

## Evidência pública de execução e custos atuais

O teste de execução examinou **112 eventos** da mesma reserva em um intervalo fixo de 10.000 blocos. Selecionou o primeiro evento de cada tipo com pelo menos 5.000 USDC, ou o primeiro menor quando esse tamanho não existia. Recibos bem-sucedidos foram confrontados com eventos e transferências do USDC nativo:

| Operação pública observada | Quantidade | Taxa da transação inteira, ETH | Alcance |
|---|---:|---:|---|
| [Saque](https://arbiscan.io/tx/0x318d7dd1badf24e3bf9be11ed61e67b3e4801110ed806be730033499d10b7bb3) | 24.424,307448 USDC | 0,0000441388756 | Saque maior que a referência de 5.000 efetivamente transferiu USDC |
| [Fornecimento](https://arbiscan.io/tx/0x8fdcb1c6a776bb992eb236d7f5862da424f5118292ba87471f16d1a676ef7820) | 8,353952 USDC | 0,000036329112648 | Não apareceu fornecimento de pelo menos 5.000 nesse intervalo |

Esses eventos não pertencem necessariamente à mesma posição. **Não se demonstrou um ciclo completo de aplicação, permanência e resgate lucrativo por uma única carteira**, nem execução pelo dono. A taxa inclui todas as ações da transação e não inclui necessariamente a aprovação ERC20 anterior.

A primeira consulta foi recusada pelo limite de 100 blocos por chamada. A tentativa original, com seis chamadas, foi preservada; uma [emenda de aquisição](evidence/aave_validation_20260910/execution_receipts/scope.json) manteve os mesmos 10.000 blocos e os dividiu em 100 consultas. A segunda tentativa usou 109 chamadas. O total de 115 ficou abaixo das 128 registradas para ambas. Nenhuma conta, chave financeira ou cobrança foi usada.

Um [livro público adicional](evidence/aave_validation_20260910/conversion_quote/result.json), em quatro GETs, mostrou USDC/USDT com compra a 1,00022 e venda a 1,00021. Para 5.000 USDT, a aritmética de conversão e reconversão imediata, com 0,1% por lado, perde **10,044889 USDT**; a 0,2%, **20,029789 USDT**. São cenários de tarifa sobre profundidade visível, sem certificar lote mínimo, prioridade, fills, taxas da conta, saques ou bridge. Não foram aplicadas cotações de hoje a fluxos históricos. A valorização das taxas ETH dos dois recibos no ask atual de ETH/USDC resulta em cerca de 0,09 e 0,11 USDC, sem constituir cotação completa de ida e volta.

Fontes primárias: [RPC pública Alchemy](https://www.alchemy.com/rpc/arbitrum), [saques Aave](https://aave.com/help/supplying/withdraw-tokens), [eventos oficiais do Pool](https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol), [gas Arbitrum](https://docs.arbitrum.io/how-arbitrum-works/deep-dives/gas-and-fees), [dados públicos Binance](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md). Os registros RPC preservados são a evidência consultada; não houve confirmação por um segundo nó independente.

## Decisão e condições que podem inverter o resultado

**Candidata aprovada para aprofundamento; lucro histórico condicional sustentado.** O empréstimo de USDC ganhou prioridade porque o histórico adicional continuou positivo após custos financiados pelo próprio capital e porque foi confirmado um saque público superior ao tamanho de referência. Carry AR1 permanece estacionado, dado o pouco resultado recente; a economia de renovação AR2 continua insuficiente no escopo anteriormente rejeitado. As famílias negativas e os pilotos congelados não foram retunados.

A renda vem de juros variáveis pagos por tomadores; nenhuma recompensa promocional foi valorizada. Não há empréstimo tomado nesta hipótese, mas continuam possíveis perdas do contrato, stablecoin, custódia e indisponibilidade de retirada. Uma perda de 5% no valor de saída elimina o ganho dos dois cenários anuais, mesmo sem tributos adicionais. A taxa de fornecimento no ponto atual foi aproximadamente 2,7422% ao ano em convenção nominal, variável; não se extrapola esse snapshot como receita prometida.

Para declarar **lucro líquido pessoal executável**, faltam as despesas aplicáveis e a validação do caminho completo de entrada/saída na estrutura efetiva. Para declarar desempenho **prospectivo**, faltam observações posteriores à escolha e ao congelamento. Esses critérios permanecem distintos da aprovação histórica. Não foi ativado capital nem agendamento, e não há promessa de coleta em segundo plano. A próxima informação de maior valor é um ciclo prospectivo do mesmo mecanismo, com custos definidos e prova de saída; procurar outra configuração vencedora no histórico não resolve essa dependência.

## Reprodução offline

Os [manifestos e brutos](evidence/aave_validation_20260910/MANIFEST.json) preservam dados, parâmetros, tentativas, código exato executado e hashes. O teste abaixo verifica bytes, confronta índices com RPC e refaz as 1.728 contas por frações, sem rede:

```powershell
C:\Cripto\CRIPTO.cmd python -m pytest -q tests/test_aave_economic_evidence.py
```

Os executores originais e fontes ficam nas respectivas pastas de evidências; seus caminhos absolutos representam este ambiente autorizado. Não se alteram seus bytes ou os protocolos para adaptar a reprodução. A versão corrigida de custos está em [funded_costs/results.json](evidence/aave_validation_20260910/funded_costs/results.json). Validação técnica e estado de integração são registrados no PR e no relatório canônico `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`.
