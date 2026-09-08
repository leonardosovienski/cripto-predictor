# Modelos semelhantes: de onde vem o lucro e o que vale pesquisar

Pesquisa pública concluída em 07/09/2026, horário de Brasília (08/09/2026 UTC). Referência do projeto: resultados históricos preservados no commit e3d9483; recibo de entrega em c40b929. Esta nota acrescenta pesquisa bibliográfica e interpretação econômica. Não apresenta novos backtests nem altera o observador.

**O caminho mais sustentado pelo projeto continua sendo o carry. As duas extensões mais justificadas para investigação são o prêmio de futuros com vencimento e a convergência do preço do perpétuo ao spot.** A documentação consultada explica mecanismos de receita; não demonstra que todos os operadores que os utilizam têm lucro líquido.

## 1. Carry contínuo: receber por oferecer a contraparte da alavancagem

Compra-se a moeda à vista e vende-se quantidade equivalente no perpétuo. Quando o funding é positivo, a posição comprada no perpétuo paga à vendida. A proteção de preço permite receber esse fluxo com menor dependência da direção da moeda.

O estudo **Crypto carry**, de Schmeling, Schrimpf e Todorov, associa o prêmio à procura por exposição comprada alavancada e à escassez de capital disposto a fazer a operação oposta. Segmentação dos mercados e exigências de margem ajudam a explicar por que a oportunidade não desaparece imediatamente. Funding ou prêmio elevado não é, por si, sinal de segurança: a pesquisa também o relaciona a episódios de instabilidade. [BIS, Working Paper 1087](https://www.bis.org/publications/working-paper-1087-crypto-carry).

No projeto, a conta do BTC no cenário base foi:

| Componente, 980 dias | USDT |
|---|---:|
| Funding líquido recebido | +431,08 |
| Variação favorável da diferença futuro–spot | +2,07 |
| Taxas e deslizamento assumidos | −8,89 |
| **Lucro simulado** | **+424,25** |

O motor econômico foi o funding. O hedge apenas neutralizou grande parte da variação do preço. Com custos adversos, sobraram +341,13 USDT; acrescentando a compressão registrada de funding e o choque de execução, +104,12. Cada cenário parte separadamente de 5.000 USDT, de 01/01/2024 a 07/09/2026. São resultados do período inteiro, sem certificação dos custos reais.

## 2. Convergência do perpétuo: ganhar com a redução de uma diferença de preços

**Fundamentals of Perpetual Futures**, de He, Manela, Ross e von Wachter, estuda uma regra que entra quando o desvio de preço ultrapassa uma barreira de custos e sai na convergência. Na decomposição publicada, a convergência contribui mais que o funding. A amostra envolve 2020–2022; a faixa denominada de custos altos usa taxas de 6,75 bps no spot e 1,44 bps nos futuros, menores que as taxas base do nosso modelo. O perpétuo não tem vencimento que obrigue a convergência em uma data conhecida. [Artigo, versão de abril de 2023, seção 4.3 e tabelas 4–6](https://arxiv.org/html/2212.06888v3).

**Minha interpretação para o projeto:** há uma fonte de ganho diferente da explorada por AR1 e do filtro retrospectivo de funding de AR2. Para contratos lineares, quantidades iguais e valores na mesma moeda de liquidação, a identidade é:

`resultado = quantidade × (diferença inicial − diferença final) + funding líquido − custos`

Aqui, “diferença” significa preço do futuro menos preço spot. A identidade contábil não garante que a diferença diminuirá. Uma investigação precisaria de preços simultâneos realmente executáveis, duração até a saída, funding durante a espera e margem suficiente se a diferença aumentar. Máximas e mínimas de velas isoladas não comprovam que as duas pernas poderiam ser executadas juntas.

## 3. Futuros com vencimento: comprar hoje e fixar o preço da venda econômica

O cash-and-carry com vencimento compra spot e vende um futuro mais caro. Seu atrativo é conhecer o prêmio inicial e a data contratual de liquidação. A CME documenta operações combinadas de spot e futuros, chamadas EFP, inclusive para encerrar operações sobre essa diferença. Isso ilustra uma infraestrutura usada nesse mercado; não certifica acesso, custos ou adequação à referência de 5.000 USDT. [Documentação da CME sobre EFP](https://www.cmegroup.com/articles/2025/bitcoin-futures-exchange-for-physical-transactions.html).

Exemplo **hipotético**, com uma unidade, spot a 1.000 e futuro a 1.020. Supondo liquidação do futuro e venda do spot pelo mesmo preço de referência:

| Preço no vencimento | Resultado do spot | Resultado do futuro vendido | Total antes dos custos |
|---|---:|---:|---:|
| 900 | −100 | +120 | +20 |
| 1.100 | +100 | −80 | +20 |

O prêmio remunera o capital e a infraestrutura necessários para manter a moeda e a proteção até a liquidação. Na prática, chamadas de margem podem ocorrer antes do recebimento na outra perna. Taxas, financiamento efetivamente contratado, liquidação por um índice diferente do preço de venda e conversão USD/USDT podem consumir o prêmio. O exemplo não é uma cotação de mercado.

**Adequação:** alta como nova hipótese econômica, condicionada à obtenção de históricos de contratos vencidos, especificações, liquidação e margem. O adaptador atual de spot/USDT não oferece automaticamente essa cobertura.

## 4. Staking com hedge e carteiras de receitas: o exemplo da Ethena

Uma arquitetura possível mantém ETH em staking e uma posição vendida equivalente para reduzir a exposição ao preço. O staking remunera a participação na validação da rede, sujeita a penalidades; seu pagamento em ETH ainda precisa ser convertido ou protegido para produzir lucro mensurado em USDT. [Ethereum: recompensas e penalidades](https://ethereum.org/developers/docs/consensus-mechanisms/pos/rewards-and-penalties/).

A Ethena é um exemplo concreto de operação com proteção por derivativos. A documentação de risco descreve a combinação de staking, funding, futuros com vencimento e ativos estáveis. A página de receitas consultada também inclui empréstimos e ativos do mundo real. Portanto, o rendimento divulgado pelo produto pode combinar fontes diferentes da nossa simulação. A reserva é um amortecedor de perdas, não uma fonte recorrente criada pela estratégia. [Ethena: risco de funding](https://docs.ethena.fi/protocol-overview/risks/funding-risk.md), [receitas do protocolo](https://docs.ethena.fi/backing-assets/protocol-revenue.md).

Se o ativo em staking vale menos que o ETH usado no hedge, a proteção deixa essa diferença descoberta. A documentação também reconhece risco de falha da corretora e descreve custódia e liquidação fora dela. São declarações do próprio operador, não uma auditoria independente de rentabilidade. Algumas estatísticas dessas páginas são de 2024–2025; não as tratei como composição ou rendimento atual. [Risco dos ativos de lastro](https://docs.ethena.fi/protocol-overview/risks/backing-assets-risk.md), [risco de corretora](https://docs.ethena.fi/protocol-overview/risks/exchange-failure-risk.md).

**Adequação:** menor nesta etapa. Seria preciso modelar conversão do ativo em staking, recompensas, resgates, contratos e custos. Somar um percentual de staking ao backtest de ETH esconderia essas diferenças.

## 5. Arbitragem entre corretoras: receber por conectar mercados separados

Compra-se onde o preço executável está menor e vende-se onde está maior. Makarov e Schoar documentaram diferenças recorrentes entre mercados, especialmente entre países, associadas a barreiras ao movimento do capital. O estudo demonstra segmentação histórica, sem provar que qualquer diferença exibida hoje seja capturável. [MIT Sloan: Trading and Arbitrage in Cryptocurrency Markets, publicado em 2020](https://mitsloan.mit.edu/cfi/trading-and-arbitrage-cryptocurrency-markets).

Para o projeto, seria necessário manter saldo e inventário previamente disponíveis nas duas pontas ou contabilizar empréstimos. Comprar, transferir e só depois vender deixa o preço de saída em aberto. Uma variação mantém futuros opostos em duas corretoras e tenta receber a diferença de funding; nesse caso, ficam duas contas de margem e pagamentos futuros variáveis. Esta última é uma extensão conceitual, não um resultado demonstrado pelo artigo citado.

**Adequação:** intermediária, limitada por dados e operação. A diferença relevante é a que sobra depois das duas execuções e do reequilíbrio de saldos, na mesma moeda.

## 6. Momentum: tentar capturar continuação de movimentos

Liu, Tsyvinski e Wu encontraram fatores de mercado, tamanho e momentum na versão de 2019 de **Common Risk Factors in Cryptocurrency**, com amostra de 2014–2018. Seus portfólios combinam posições compradas e vendidas; o artigo discute limitações de venda a descoberto e, na análise de tamanho, a exclusão de custos. Isso não equivale a comprovar lucro líquido de uma seleção atual apenas comprada. [Texto dos autores hospedado em Yale](https://economics.yale.edu/sites/default/files/2022-10/LiuTsyvinskiWu2019%20COMMON%20RISK%20FACTORS.pdf).

A hipótese econômica é a continuação de fluxos ou a incorporação gradual de informação. Ela é menos diretamente observável que um pagamento de funding: o modelo precisa acertar movimentos futuros. Selecionar moedas que subiram mais é diferente de negociar cada moeda conforme sua própria tendência; também é diferente de comprar vencedoras e vender perdedoras.

No nosso teste, AR3 perdeu 98,91% no cenário base e continuou fortemente negativa mesmo retirando o deslizamento adicional. Isso rejeita essa regra nas condições estudadas. Não rejeita toda a literatura de momentum, mas tampouco justifica procurar novas janelas até aparecer um resultado positivo. Uma replicação seria outra hipótese, com desenho e limite de tentativas registrados antes da avaliação.

## 7. Formação de mercado: cobrar pela liquidez imediata

O formador de mercado mantém ofertas de compra e venda e tenta capturar a diferença entre elas. O modelo clássico de **Avellaneda–Stoikov** ajusta as cotações ao risco do inventário acumulado. O artigo destaca riscos de inventário e informação assimétrica, concentrando seu modelo no primeiro. É uma referência teórica de 2008, não uma comprovação de lucro atual em cripto. [Artigo original](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf).

Uma compra a 99,90 seguida de venda a 100,10 deixa 0,20 antes dos custos. Porém, a segunda execução pode não acontecer e a primeira pode ocorrer justamente antes de uma queda. Quem pede execução imediata paga o spread; isso só vira lucro se ele cobrir as perdas de inventário, as taxas e a execução desfavorável.

**Adequação:** baixa agora. Seriam necessários livro de ofertas, negócios, posição na fila, cancelamentos e latência. Considerar uma ordem executada apenas porque a vela tocou seu preço produziria evidência insuficiente.

## Por que resultados externos podem parecer maiores

Há quatro diferenças que precisam ser reconciliadas antes de comparar percentuais:

- **Capital no denominador.** Exemplo aritmético: uma receita de 10% sobre 1.250 gera 125, equivalentes a 2,5% sobre uma carteira de 5.000, antes dos demais custos. No nosso AR1, aproximadamente 25% foi usado inicialmente no spot; essa fração variou depois porque a quantidade ficou fixa. A reserva de margem faz parte do capital necessário.
- **Composição da receita.** Funding, convergência, staking, empréstimos e incentivos não são a mesma fonte. Receita do protocolo, remuneração do depositante e lucro líquido do operador também não são medidas intercambiáveis.
- **Custos e execução.** Categorias chamadas de “custos altos” em um estudo podem cobrar menos que nossa simulação. Uma estrutura com menor taxa pode conservar uma diferença pequena; isso não autoriza assumir que teremos a mesma tarifa.
- **Período e risco.** Um prêmio alto em anos anteriores não certifica o presente. No AR1 adverso, somente a contribuição de 2026 até o corte foi +5,75 USDT no BTC e −11,33 no ETH. Reduzir a reserva aumentaria a exposição por unidade de capital e também a vulnerabilidade a chamadas de margem.

O filtro de AR2 ilustra o problema: no BTC adverso, funding de +33,37 e convergência de +2,71 ficaram abaixo de 51,22 USDT de taxas e deslizamento, mesmo antes da despesa residual. Sua decisão usava funding passado; ela não fixava os pagamentos do período seguinte.

## Prioridade de pesquisa para o projeto

Minha ordem proposta, com base nas fontes e nos resultados existentes:

1. **Concretizar os custos e a execução do carry contínuo de BTC.** É a hipótese com evidência local mais favorável. Verificar preços simultâneos, cobrança das taxas, margem, interrupções e conversões reduz a principal distância entre simulação e resultado realizável.
2. **Pesquisar cash-and-carry com vencimento.** Registrar uma hipótese e verificar a cobertura histórica dos contratos antes de calcular desempenho. A pergunta é se o prêmio contratado cobre todos os custos efetivos e a necessidade de margem até a liquidação.
3. **Pesquisar convergência do perpétuo.** Definir previamente entrada, saída, prazo máximo, funding, custos e tratamento da ausência de convergência. Não reutilizar o filtro de AR2 como se fosse a mesma regra.

Staking com hedge e arbitragem entre corretoras ficam como extensões posteriores. Momentum e formação de mercado têm menor prioridade diante dos resultados e dos dados disponíveis.

Estas são **ideias ainda não registradas como novos experimentos**. As cinco séries da rodada anterior continuam encerradas, seus resultados negativos permanecem preservados e nenhuma família congelada foi reaberta. Os períodos já examinados continuam sendo pesquisa adaptativa. A pesquisa bibliográfica foi feita sozinho, com fontes públicas; não houve uso de conta autenticada, ordem, serviço pago ou alteração do acompanhamento semanal.
