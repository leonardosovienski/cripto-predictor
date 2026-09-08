**Teste concluído: a atualização não demonstrou melhora na projeção de lucro.** Ela acrescentou modelos e corrigiu o cálculo das quantidades para proteção, mas o carry contínuo de BTC que já existia continua com o maior lucro histórico entre os modelos de carry comparados. A projeção futura validada permanece desconhecida.

Reprodução realizada em 08/09/2026 UTC, ainda 07/09 em Brasília. Cada linha usa separadamente **5.000 USDT hipotéticos**, de **01/01/2024 até a abertura de 07/09/2026 UTC: 980 dias, 140 semanas**. Os valores abaixo são o resultado total desse período, após os custos simulados; não são ganhos mensais ou anuais e não devem ser somados como se viessem da mesma conta.

| Modelo | Situação | Base (USDT) | Custos adversos (USDT) | Estresse (USDT) |
|---|---|---:|---:|---:|
| Carry contínuo BTC — AR1 | Já existia | +424,25 | +341,13 | +104,12 |
| Carry contínuo ETH — AR1 | Já existia | +328,94 | +250,01 | +65,94 |
| Carry com filtro BTC — AR2 | Já existia | +17,79 | −82,26 | −117,42 |
| Carry com filtro ETH — AR2 | Já existia | +30,69 | −80,18 | −130,09 |
| Carry BTC com vencimento — BR1 | Adicionado | +230,17 | +110,07 | +78,42 |
| Convergência de perpétuos BTC — BR2 | Adicionado | 0,00 | 0,00 | 0,00 |

O novo BR1 ficou **194,08 USDT abaixo** do AR1 BTC no cenário base e **231,06 USDT abaixo** nos custos adversos. Nesse último cenário, os retornos sobre os 5.000 USDT iniciais foram, respectivamente, **2,20% e 6,82% no período inteiro**. Como o AR1 foi preservado, adicionar o BR1 não reduziu seu resultado: a nova alternativa apenas não apresentou mais lucro.

O BR1 fechou cinco posições protegidas e ficou 65 semanas inteiras em caixa; o AR1 BTC manteve uma posição protegida por 140 semanas. A exposição e a necessidade de margem são diferentes. Portanto, a comparação mede lucro absoluto com o mesmo capital inicial, não equivalência de risco nem dominância em todos os critérios. O BR2 não operou porque o maior sinal horário observado foi 0,2888%, abaixo do gatilho congelado de 0,75%.

Os custos base assumem, por lado, taxa de 10 pontos-base no spot, 5 nos futuros e deslizamento de 5 por perna de mercado. No cenário adverso, esses valores passam a 20, 10 e 20; acrescenta-se uma despesa hipotética de 25 USDT por ano após a primeira entrada, inclusive enquanto a estratégia fica em caixa. No vencimento, o futuro tem taxa de liquidação de 5 ou 10 pontos-base e não recebe deslizamento de uma venda de mercado fictícia. No estresse, os recebimentos positivos de funding caem pela metade, os pagamentos negativos permanecem e cada entrada perde ainda 0,5% do valor spot por desencontro de execução. BR1 não tem funding. Os modelos aplicam as mesmas premissas relevantes, mas produzem custos totais diferentes conforme suas operações.

**A contribuição recente foi fraca.** Em 2026, de janeiro até o corte de setembro, os resultados adversos foram:

| Modelo | Contribuição de 2026 (USDT) |
|---|---:|
| Carry contínuo BTC | +5,75 |
| Carry contínuo ETH | −11,33 |
| Carry BTC com vencimento | −17,05 |
| Convergência BTC | 0,00 |

São contribuições das posições e do caixa do estudo contínuo, não novos testes que recomeçam com 5.000 USDT em janeiro. O BR1 não abriu posições em 2026; seu −17,05 vem integralmente da despesa anual hipotética mantida enquanto ficou em caixa. No estresse de funding, a contribuição de 2026 do AR1 BTC foi **−21,95 USDT**. A média de todo o histórico, influenciada por 2024 e 2025, não é uma expectativa confiável para os meses seguintes.

O intervalo descritivo do BR1 com custos adversos, por reamostragem de blocos de 13 semanas, vai de **−6,96 a +247,26 USDT** para o lucro do período. Ele inclui perda. Retirando aritmeticamente as cinco melhores contribuições semanais, esse lucro passa a −16,73 USDT. Isso mede concentração; não é uma estratégia alternativa nem uma previsão. Os intervalos antigos do AR1 usavam outro tamanho de bloco e outra unidade, por isso não foram comparados diretamente. Também não se compararam drawdowns diários do AR1 com drawdowns horários do BR1 como se fossem a mesma medida.

**A melhora comprovada foi de execução simulada.** Nos mesmos livros de ofertas públicos preservados, com comissão spot hipotética em BTC, o planejamento corrigido reduziu a sobra desprotegida do primeiro exemplo de **58,26 para 0,40 USDT**. Os 12 planos foram reproduzidos. Isso reduz exposição acidental; não são 57,86 USDT de lucro. As cotações foram coletadas até 08/09/2026 às 02:08:23 UTC e não foram usadas para recalibrar o histórico. Comissão real da conta e execução simultânea continuam desconhecidas.

Validação executada neste pedido:

- **42 testes de software aprovados**; verificação de estilo e tipos do comparador sem erros. A suíte completa antiga de 1.045 testes não foi repetida.
- **18 cenários econômicos refeitos**, com **23 arquivos de resultados idênticos byte a byte**: 14 dos modelos antigos de carry e 9 dos novos.
- Auditoria separada com Decimal: **532 respostas públicas reconstruídas**, 29 séries, 23.994 decisões, 165.258 comparações numéricas e 73.104 verificações de margem, sem divergência acima da tolerância. Os 68 arquivos-fonte do carry anterior também tiveram integridade verificada.
- **12 planos de execução idênticos**, sem novas requisições de rede. As conexões de rede ficaram bloqueadas durante a reprodução.

Os resultados negativos anteriores não foram apagados: o momentum de altcoins AR3 permanece em **−4.945,35 USDT no cenário base**, conforme o teste já entregue; ele não foi reexecutado nesta comparação de carry. O checkpoint mais antigo de +54,84 USDT em BTC usava outro ano e outra alocação e não foi tratado como um antes/depois comparável.

Não foi alterado nenhum parâmetro de estratégia. O histórico continua sendo pesquisa adaptativa já consultada, sem confirmação independente. Taxas efetivas da conta, impostos, conversão, custódia e execução real não estão certificados; os valores são líquidos apenas dos custos explicitamente modelados. O observador semanal, seu livro de registros e o repositório original foram preservados.

**Decisão:** manter o resultado do carry contínuo de BTC como evidência histórica existente. Os modelos acrescentados não sustentam elevar uma estimativa futura de lucro. Nenhuma operação real foi realizada e nenhum lucro real foi comprovado.
