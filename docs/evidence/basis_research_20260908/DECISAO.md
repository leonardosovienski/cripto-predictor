# Implementação de carry com vencimento, convergência e diagnóstico de execução

**O carry com vencimento apresentou lucro histórico nos três cenários registrados, mas ainda não passou no critério de incerteza. A convergência do perpétuo não encontrou entradas que cobrissem o limite definido.** O projeto também ganhou um planejador de quantidades que considera a comissão recebida em BTC e evita deixar uma parcela grande da compra sem hedge.

Cada estratégia usa separadamente **5.000 USDT hipotéticos**, entre **01/01/2024 e 07/09/2026**, totalizando 980 dias. Os resultados abaixo são do período inteiro; não são anuais, não devem ser somados como uma única carteira e não demonstram lucro real.

| Regra | Cenário base | Custos adversos | Estresse adicional |
|---|---:|---:|---:|
| BR1 — Carry BTC com vencimento | **+230,17 USDT (+4,60%)** | **+110,07 USDT (+2,20%)** | **+78,42 USDT (+1,57%)** |
| BR2 — Convergência BTC spot/perpétuo | 0,00 USDT | 0,00 USDT | 0,00 USDT |

## O que foi implementado

As duas hipóteses foram registradas em Git antes da implementação e da avaliação econômica, no commit **86d79d1**. Elas têm regras fixas, dois fluxos de estratégia e três cenários de custos por fluxo. Não houve busca de parâmetros. O código inclui coleta pública, verificação dos arquivos de origem, decisões com atraso explícito, liquidação contratual, caixa e margem separados, resultados completos e reprodução offline.

**BR1 — Carry com vencimento.** Enquanto está em caixa, verifica diariamente às 00h UTC contratos trimestrais de BTC/USDT com 30 a 120 dias até o vencimento. Escolhe o vencimento mais próximo entre os que passam no filtro de liquidez. Só entra se o prêmio observado anteriormente for maior que 2,1%. Compra aproximadamente 25% do capital em BTC e vende a mesma quantidade no futuro, reservando o restante em USDT para margem. A quantidade fica fixa até o vencimento. A saída usa o preço de liquidação publicado pela corretora e o preço spot daquele horário, cobrando custos distintos nas duas pernas.

**BR2 — Convergência do perpétuo.** Verifica a diferença de preços a cada hora. Exige prêmio maior que 0,75%, equivalente ao custo base aproximado de 0,50% mais uma folga de 0,25%. Encerra quando a diferença observada anteriormente chega a 0,05% ou menos, após sete dias, ou no corte final. Funding de ambos os sinais entra na conta enquanto a posição está aberta, respeitando os limites de tempo.

Nas duas regras, a decisão usa o fechamento de uma vela cuja informação ficou disponível **uma hora completa antes da execução simulada**. A liquidez exige 30 dias completos, com um dia adicional de atraso, e mediana diária de volume de pelo menos 5 milhões de USDT nas duas pernas. Os preços de execução são aberturas de velas horárias: são aproximações por primeiros negócios, sem certificação de execução simultânea.

A biblioteca de dados preserva os bytes públicos e verifica os checksums disponibilizados no [arquivo oficial da Binance](https://github.com/binance/binance-public-data). A hipótese de convergência foi motivada pela pesquisa anterior sobre [fundamentos de futuros perpétuos](https://arxiv.org/html/2212.06888v3), mas esta implementação tem regras, custos e amostra próprios; não é uma reprodução dos retornos daquele artigo.

## De onde veio o ganho do carry com vencimento

Foram **cinco hedges completos**, todos encerrados no vencimento. Não houve posição truncada pelo corte final. A exposição somou 12.184 horas, aproximadamente 507,7 dias; houve posição em 75 semanas e 65 semanas inteiramente em caixa.

| Contrato | Entrada UTC | Saída UTC | Quantidade no cenário adverso | Ganho antes da despesa residual, cenário adverso |
|---|---|---|---:|---:|
| BTCUSDT_240329 | 01/01/2024 00h | 29/03/2024 08h | 0,029 BTC | +31,57 USDT |
| BTCUSDT_240628 | 30/03/2024 00h | 28/06/2024 08h | 0,017 BTC | +59,12 USDT |
| BTCUSDT_240927 | 29/06/2024 00h | 27/09/2024 08h | 0,021 BTC | +20,84 USDT |
| BTCUSDT_250328 | 29/11/2024 00h | 28/03/2025 08h | 0,013 BTC | +46,31 USDT |
| BTCUSDT_250926 | 30/05/2025 00h | 26/09/2025 08h | 0,012 BTC | +19,35 USDT |

Esses ganhos já descontam as taxas e o deslizamento de cada operação, mas ainda não a despesa residual de 25 USDT por ano, que é lançada no caixa da carteira. Os vencimentos intermediários que não atenderam à regra não foram forçados.

| Componente | Base | Adverso | Estresse |
|---|---:|---:|---:|
| Diferença de preços capturada | +259,95 | +255,66 | +253,91 |
| Funding | 0,00 | 0,00 | 0,00 |
| Taxas e deslizamento | −29,78 | −78,46 | −77,71 |
| Despesa residual assumida | 0,00 | −67,12 | −67,12 |
| Perda adicional por execução | 0,00 | 0,00 | −30,66 |
| **Lucro final em USDT** | **+230,17** | **+110,07** | **+78,42** |

O lucro veio do prêmio dos futuros e da diferença efetiva entre preços na saída. Não veio de funding. A quantidade de entradas posteriores depende do capital que restou; por isso, a diferença capturada e as taxas em USDT variam um pouco entre cenários, mesmo com decisões idênticas.

O cenário base assume taxas de 10 bps por lado no spot e 5 bps nos futuros, com 5 bps de deslizamento por perna negociada. O adverso usa 20 e 10 bps, respectivamente, mais 20 bps de deslizamento e a despesa residual anual. No vencimento, a perna futura paga uma taxa de liquidação assumida de 5 bps no base ou 10 bps no adverso; ela não recebe um deslizamento fictício de ordem de mercado. A venda spot continua sujeita aos custos de negociação. Um bp equivale a 0,01%.

O estresse acrescenta perda de 0,5% do nocional spot em cada entrada. A compressão de recebimentos positivos de funding também está prevista para o perpétuo, mas não altera BR1 porque futuros com vencimento não geram esse fluxo. As tarifas são hipóteses de pesquisa, não tarifas verificadas da conta.

## Por que o resultado ainda é incerto

No cenário adverso, o intervalo descritivo obtido por reamostragem em blocos de 13 semanas foi de **−6,96 a +247,26 USDT**. Sob estresse, foi de **−34,54 a +208,04 USDT**. Ambos incluem perda. Esse cálculo não corrige toda a pesquisa adaptativa anterior e não é uma probabilidade de lucro futuro.

As cinco semanas de maior contribuição positiva representaram 41,62% das contribuições positivas no adverso. Subtraindo aritmeticamente essas cinco contribuições, o resultado seria −16,73 USDT. Essa é uma medida de concentração, não outra estratégia simulada.

| Contribuição ao resultado adverso | USDT |
|---|---:|
| 2024 | +99,46 |
| 2025 | +27,66 |
| 2026 até o corte | −17,05 |

Não houve novas posições em 2026. O valor negativo desse ano vem exclusivamente da despesa residual assumida, que continua após a primeira entrada mesmo durante períodos em caixa. Não representa perda de uma operação aberta em 2026.

BR1 recebeu a classificação **positivo, mas com incerteza descritiva**. O critério registrado exigia que o limite inferior do intervalo adverso fosse positivo para qualificá-lo como candidato a uma observação futura separada. Ele não atingiu essa condição.

## Convergência: por que não houve operações

Foram verificadas **23.520 decisões horárias**, todas com uma observação de diferença de preços disponível. A maior diferença positiva foi aproximadamente **0,2888%**, abaixo dos **0,75%** registrados. Portanto, nenhuma entrada passou pelo filtro e as 140 semanas ficaram em caixa.

Isso não demonstra que nenhuma oportunidade intradiária exista. Demonstra que esta regra horária, com atraso e custos declarados, não encontrou oportunidade no período. Não reduzi o limite após observar o resultado, não substituí os custos pelos de outro estudo e não converti a ausência de operações em rentabilidade demonstrada.

## Margem e perdas

No carry com vencimento adverso, a maior queda entre marcações horárias foi **1,12%**. Sob estresse, foi **1,23%**. Essas medidas não incluem falência de corretora, congelamento de saldo ou uma liquidação real.

O cálculo manteve o caixa separado do BTC comprado, sem crédito automático para transferir ganhos do spot à margem do futuro. Usou máximas horárias de marcação, uma reserva assumida de manutenção de 1% e 0,5% adicional para encerramento. Recebimentos positivos de funding na hora atual não podem financiar uma máxima anterior dessa mesma hora.

Nenhum cenário de BR1 rompeu essa barreira. O menor excedente no adverso foi **2.838,88 USDT**; aplicando uma alta instantânea adicional de 30% a cada máxima horária, foi **2.176,41 USDT**. Esses valores validam o teste de suficiência sob as hipóteses registradas, sem certificar as regras reais ou históricas de liquidação da conta.

## Diagnóstico público de execução e quantidades

Foram coletadas **12 amostras pareadas** de livros spot e perpétuo, com 100 níveis, sem autenticação. A coleta terminou em **08/09/2026 às 02:08 UTC**, equivalente a **07/09/2026 às 23:08 em Brasília**. Todas passaram pelos limites registrados de duração das requisições e diferença entre seus horários. Isso mede a janela de coleta; não prova simultaneidade ou preenchimento de uma ordem.

Nessas amostras, a estimativa de custo de ida e volta, incluindo taxas assumidas de 10 bps no spot e 5 bps nos futuros, teve mediana de aproximadamente **30,01 bps** sobre o nocional spot. A maior parte veio das taxas assumidas; o spread e a profundidade observados contribuíram pouco naquele minuto. Esses dados atuais **não foram usados para reduzir os custos dos backtests**.

O planejamento também passou a considerar que a comissão de uma compra spot pode ser descontada em BTC. O cálculo compra uma quantidade bruta compatível com o lote, estima a comissão com arredondamento conservador e dimensiona o futuro pela quantidade líquida recebida. Ele deixa em caixa o valor que não consegue emparelhar adequadamente.

Na primeira amostra preservada, sob essa hipótese de comissão:

| Quantidade planejada | BTC |
|---|---:|
| Compra spot bruta | 0,01502000 |
| Comissão spot estimada | 0,00001502 |
| BTC líquido recebido | 0,01500498 |
| Venda equivalente no futuro | 0,01500000 |
| Sobra sem hedge | **0,00000498** |

A sobra correspondia a aproximadamente **0,40 USDT**, contra cerca de **58,26 USDT** ao comprar primeiro perto de 1.250 USDT e somente depois arredondar a quantidade do futuro. A compra planejada consumiria aproximadamente 1.191,69 USDT naquela fotografia. O cálculo foi reproduzido nas mesmas 12 amostras, sem nova consulta ou escolha de cotações favoráveis.

O planejador gera somente números para revisão. Não envia ordens. A taxa, o ativo efetivamente cobrado em comissão, os descontos da conta e a execução permanecem desconhecidos. Esse cálculo atual não substituiu silenciosamente a hipótese histórica de custos pagos em equivalente USDT.

## Dados, auditoria e preservação

A rodada preservou **532 respostas históricas públicas**, cerca de 15,47 MB de conteúdo transferido, e reconstruiu **29 séries normalizadas** a partir dos arquivos originais. O universo contém os 12 vencimentos trimestrais de março/2024 a dezembro/2026, incluindo contratos já encerrados; a seleção não usa somente o catálogo atual.

Um cuidado essencial foi tratar o campo `deliveryTime` do endpoint de preços de liquidação como rótulo do dia à meia-noite. O preço só fica disponível à simulação na saída contratual das **08h UTC**. A interpretação foi registrada antes da avaliação. Antecipá-lo para meia-noite introduziria informação futura. Arquivos de marcação que continuem após o vencimento não prolongam a posição.

A auditoria separada em Decimal conferiu **23.994 registros de decisão**, os **seis cenários contábeis**, **165.258 comparações numéricas** e **73.104 verificações de margem e choque**. A maior diferença numérica foi inferior a 10⁻⁹ USDT. Ela não importa o motor econômico. Os hashes e a reconstrução dos dados também passaram. Os testes de código abrangem causalidade, sinais de funding, liquidação, lacunas, caixa após a saída, profundidade insuficiente e quantidade líquida após taxas. **42 testes direcionados passaram**, sendo 28 novos e 14 de regressão da rodada anterior; Ruff e Pyright também passaram nos arquivos novos.

A primeira execução salvou os três cenários BR1 e depois parou porque um texto explicativo do protocolo foi tratado como cenário. A correção limitou a leitura aos três cenários registrados. Os quatro arquivos parciais, incluindo o plano, ficaram preservados e são idênticos aos correspondentes da execução concluída. Nenhum parâmetro econômico mudou.

Os períodos históricos continuam sendo **pesquisa adaptativa**, e os arquivos públicos podem ter revisões posteriores à data dos negócios. Filtros de lotes históricos, disponibilidade em tempo real, preços simultâneos, comissões reais, regras de margem, indisponibilidade, custódia, conversões e impostos continuam sem certificação. No estresse de BR1, apenas **78,42 USDT adicionais de custos ou perdas** caberiam antes de zerar o lucro do período inteiro.

O observador v6, sua automação, o projeto original e as evidências anteriores foram preservados. Não houve uso de agentes, contas autenticadas, ordens, movimentação de dinheiro, contratação de serviço ou push. Esta implementação e seus dados são uma entrega nova; os pacotes anteriores permanecem como registros das respectivas rodadas.
