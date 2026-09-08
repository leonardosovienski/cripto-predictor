# Funding carry: decisão econômica — 07/09/2026

**Decisão: não aprofundar agora o carry passivo de BTC/ETH nesta estrutura de
US$5.000 e com o benchmark em BRL adotado como referência.** A remuneração
observada ficou muito abaixo do custo de oportunidade, inclusive em cenários
que favorecem o carry. Isso encerra esta triagem; não prova que toda forma de
carry, venue, ativo ou período futuro seja incapaz de gerar lucro.

## A conta que importa

Estrutura ilustrativa sem empréstimo: US$2.500 de spot + US$2.500 de margem
USDT separada; quantidade igual vendida no perpétuo. Spot e futuro cancelam
a maior parte da exposição à direção da criptomoeda. Os ganhos restantes são
funding e mudança do diferencial entre os preços das duas posições.

Conta histórica de 07/09/2025 a 07/09/2026, com quantidade fixa, preços de
referência e câmbio constante de R$5,1253 por USD. Não são operações realizadas:
fees e slippage abaixo são cenários, e mark price não é preço de execução.

| Ativo | Funding recebido | Mudança de basis | Fees + slippage ilustrativos | Saldo em BRL |
|---|---:|---:|---:|---:|
| BTC | US$ 65,99 | US$ -0,35 | US$ 10,81 | **R$ 281,08** |
| ETH | US$ 45,26 | US$ -0,71 | US$ 9,93 | **R$ 177,46** |

Os saldos são **antes de imposto, custos cambiais, atenção e prêmio de risco**.
O funding da entrada foi excluído: comprar após a liquidação não dá direito
a receber aquela parcela. Foram utilizados 1.094 pagamentos subsequentes.

A alternativa candidata, Tesouro Reserva, gera aproximadamente **R$2.900 a
R$2.907 em 365 dias** no cenário de Selic efetiva constante de 13,90%, IR 17,5%,
custódia B3 e isenção disponível de R$10 mil. Acesso do operador ao produto,
taxas adicionais e tributação pessoal continuam não confirmados. Não é taxa
líquida contratada nem promessa. [Tesouro Reserva](https://www.tesourodireto.com.br/tesouro-reserva),
[B3](https://www.b3.com.br/pt_br/produtos-e-servicos/tesouro-direto/tesouro-direto/perguntas-frequentes/).

**Distinção temporal:** os pagamentos cripto são retrospectivos; o benchmark
é uma referência construída com a taxa corrente. A comparação serve para
priorizar pesquisa, não simula o Tesouro efetivamente mantido no mesmo ano
histórico e não prevê que o funding se repetirá no próximo ano.

## Mesmo favorecendo o carry, a conta não fecha

Como comparação padronizada, somei as taxas assinadas de funding, mantendo
nocional constante e sem capitalização. Isso produz um índice de remuneração,
não o caixa de uma quantidade fixa de moedas:

| Janela terminada em 07/09/2026 00:00 UTC | BTC anualizado simples | ETH anualizado simples |
|---|---:|---:|
| 30 dias | 7,46% | 6,13% |
| 90 dias | 5,70% | 3,85% |
| 365 dias | 3,35% | 2,49% |

As janelas de 30/90 dias são apenas descrições, anualizadas por 365/dias;
não foram escolhidas após os resultados e não são APYs previstos. A janela
principal de 365 dias estava registrada antes da consulta.

No cenário deliberadamente favorável de colocar os **US$5.000 inteiros em
nocional**, com zero fee, zero slippage e sem reservar margem adicional, o
funding padronizado do ano seria R$859 no BTC e R$637 no ETH. Até esses
valores ficam abaixo de R$2.900. Esse cenário não é executável no envelope
atual nem um limite superior universal para toda estratégia.

Na estrutura N=US$2.500, o funding anual exigido seria cerca de **23,14% do
nocional**, incluindo os custos ilustrativos e excluindo risco, câmbio,
tributação cripto e atenção. Com atenção de 2h/mês a R$50/h, sobe a **32,50%**.
O observado foi **3,35% BTC / 2,49% ETH**. Aumentar apenas o capital, mantendo
essa estrutura e essas taxas, não resolve o déficit percentual contra o
benchmark; a capacidade em tamanhos maiores não foi medida.

## Custos e câmbio

Fee spot: 10bps por lado na [tabela pública Regular User](https://www.binance.com/en/fee/trading).
Fee perp: cenário de 5bps por lado do [exemplo público Binance](https://www.binance.com/en/support/faq/detail/360033544231),
explicitamente hipotético no FAQ; tabela atual de futuros não retornou linhas.
Slippage: 5bps em cada uma das quatro pontas, hipótese de sensibilidade.
Nada disso foi rotulado como custo realizado ou como tarifa da conta do operador.

Foram calculadas 18 combinações descritivas por ativo: slippage 0/5/10bps,
custo cambial total 0/0,5/1% do capital e atenção 0/R$1.200 por ano. Todas
continuam abaixo do benchmark. No índice de nocional constante, 1% de custo
FX derruba o saldo BTC de R$365,49 para R$109,23 e o ETH de R$254,61 para
−R$1,65, antes de impostos. A conta com quantidade fixa é ainda menor.

O hedge cripto não protege BRL/USD. Aplicando variações de câmbio ao capital
e ao saldo da conta com quantidades fixas, sem custo FX nem tributação:

| Mudança USD/BRL | Resultado BTC | Resultado ETH |
|---|---:|---:|
| -10% | R$ -2.309,68 | R$ -2.402,94 |
| +0% | R$ 281,08 | R$ 177,46 |
| +10% | R$ 2.871,83 | R$ 2.757,85 |

São cenários, não variações previstas. O dólar precisaria subir aproximadamente
**10,11% no BTC / 10,55% no ETH** para igualar o benchmark, mesmo antes de
tributação cripto/FX. Essa contribuição é exposição cambial, não alpha do carry.
A PTAX utilizada é marca contábil, não spread de conversão acessível ao usuário.
[BCB, fechamento de 04/09](https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do).

Também existe sensibilidade ilustrativa de imposto 15% sobre o resultado total
positivo em BRL, incluindo FX; não foi determinado o enquadramento tributário
do operador ou de cada instrumento. A [Receita](https://www.gov.br/fazenda/pt-br/acesso-a-informacao/perguntas-frequentes/tributacao-offshore/perguntas-e-respostas-offshores-in-rfb-2-180-22-05-24.pdf)
distingue natureza do ativo e instituição de custódia/negociação. A decisão de
não aprofundar já aparece com imposto cripto zero, portanto não depende dessa
hipótese fiscal.

## Fidelidade, riscos e limite da conclusão

- Dois ativos fixados antes do download, uma venue, três janelas; nenhum
  threshold de entrada/saída, alavancagem ou ativo foi escolhido pelo resultado.
- 2.190 registros públicos de funding: 1.095 por ativo; zero duplicações e
  zero lacunas no calendário de 8h verificado. Funding foi negativo em 23,84%
  das observações BTC e 26,85% ETH na janela de 365 dias.
- As fontes foram baixadas em 07/09/2026. `fundingTime` é o momento do evento;
  `known_at` é a consulta atual. Esta evidência é Discovery, nunca prospectiva.
- As velas finais contêm campos intradiários posteriores ao corte: somente a
  abertura exatamente no corte foi usada como referência de saída. Máximas,
  mínimas, fechamento e volume posteriores foram excluídos.
- A identidade spot+short foi reconciliada com a mudança de basis. O custo
  de encerramento usa nocionais finais, que mudam com o preço das moedas.
- A maior perda apenas por preço da perna short, usando máximas diárias
  anteriores ao corte, foi US$364 BTC / US$288 ETH para essas quantidades.
  Isso não valida margem nem ausência de liquidação: manutenção, mark/fill,
  outages, contraparte e regras reais da conta continuam não modelados.
- Rendimento da margem: zero nesta estrutura. Remunerar colateral, usar
  portfolio margin ou mudar venue requer nova estrutura e nova avaliação;
  não foi presumido para resgatar o resultado.

Fonte primária dos pagamentos: [Binance Funding Rate History](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History).
Cada resposta, URL, instante de coleta e SHA256 está no pacote reproduzível.
Somas foram conferidas independentemente com Decimal; o ledger H1-H9 e os
parâmetros congelados permaneceram intactos. Nenhuma operação foi enviada.

## Consequência operacional

**REJECT nesta triagem econômica; retirar carry passivo BTC/ETH da prioridade
de pesquisa sob as premissas registradas.** G1 de deployment segue bloqueado;
a falsificação econômica one-shot foi autorizada pelo pedido atual do usuário.
Não há passagem por G1–G7, Proof, paper ou capital.

Reconsiderar apenas com mudança material verificável: remuneração sustentável
líquida substancialmente maior, benchmark efetivamente acessível mais baixo,
ou estrutura de capital/colateral diferente e mensurável. Simplesmente reduzir
fees ou aumentar o capital nesta mesma estrutura não corrige a diferença
observada. Nenhuma outra família ganhou prioridade automaticamente.
