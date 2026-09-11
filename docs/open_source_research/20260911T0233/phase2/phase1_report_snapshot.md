# Cripto Predictor — análise consolidada do mandato

**A melhor decisão é conservar o núcleo e concentrar o próximo trabalho em identidade dos dados, validação temporal e execução/capital.** Não encontramos evidência que justifique trocar o projeto por um bot externo, acrescentar um modelo complexo agora ou liberar estratégia para operar.

O prompt foi aplicado ao Cripto; o segundo documento era o guia dos prompts, não uma ordem de executar também Stocks. Esta é a consolidação da mesma iniciativa 20260911T0233. A primeira entrega parcial foi preservada em arquivo; as seis peças canônicas foram atualizadas com os resultados desta continuação.

## O que foi executado

- 53 candidatos triados; 23 revisões focadas: 16 implementações/referências de cálculo, 4 artigos com leitura de método/resultados e 3 contratos de fonte/produto. Releases/licenças dos 15 repositórios aprofundados inicialmente e issues relevantes foram examinadas; fontes fixadas por SHA/recibo.
- 18 capacidades comparadas, ranking mestre, 10 vistas por categoria e 6 composições com condições de falha.
- 6 benchmarks controlados aprovados. Suíte completa: **1505 aprovados, 1 ignorado**. CI do mesmo commit: **4 jobs com sucesso**.
- **1728 fluxos históricos Aave reconciliados** aos índices RPC originais e custos registrados. Segunda rota tentada sob protocolo: **ConnectTimeout na primeira chamada, 0 bytes recebidos**, sem repetição.
- Código operacional, dependências, locks e experimentos congelados preservados. Nenhuma operação financeira.

## Os achados que importam

**1. O projeto já ultrapassa forecasting.** Há DPL, discovery/prefiltro, snapshots, LLM, HMM/WFA, carry/basis, altcoins e Aave. A limitação não se resolve instalando mais bibliotecas: é preciso provar que cada dado e instrumento corresponde à pergunta econômica. Discovery direcional exclui stable/wrapped/staked; essa regra não deve definir universo de lending, staking, LP ou resgate.

**2. Os controles atuais têm valor demonstrado, mas alcance definido.** Spearman e SMA/Bollinger concordaram com referências; serving rejeitou 8 casos inválidos e aceitou o controle válido; VWAP/hedge líquido passaram. São vantagens de implementação verificadas dentro do próprio projeto, não superioridade econômica sobre concorrentes. O HMM usa inferência forward-only, mas treino causal ainda depende dos dados entregues pelo chamador.

**3. “PIT” precisa de mais que um timestamp.** Fechamento do candle, cálculo pelo provider, publicação e recepção são momentos diferentes. A documentação Glassnode separa computed_at da publicação e limita a história PIT ao início de rastreamento da métrica. ALFRED fornece vintage por data, sem resolver sozinho o horário do anúncio. No projeto, snapshot hash preserva inputs normalizados; não é recibo HTTP histórico completo. [Glassnode PIT](https://docs.glassnode.com/data/point-in-time-metrics), [ALFRED](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

**4. A separação treino/teste exige o fim de cada label.** No B05, gap de 2 linhas deixou um label longo sobreposto nos 3 folds. A purga por término eliminou as interseções. Isso não revela defeito no sklearn: demonstra que sua promessa é diferente. Para famílias novas, seleção de universo, filtros, features e parâmetros deve ser incluída no desenho; não reinterpretar trials encerradas.

**5. Rendimento anunciado e capital comprometido podem mudar a conclusão.** Aave local calcula índices realizados, enquanto o adapter DefiLlama examinado usa taxa anual instantânea em apyBase. Na carteira, custos reservados reduzem o principal que rende. No hedge, a comissão spot reduz BTC recebido e as duas pernas exigem financiamento. O estudo histórico de carry consultado também destaca margem/financiamento antes da convergência. [BIS Crypto carry](https://www.bis.org/publications/working-paper-1087-crypto-carry).

**6. Frameworks externos trazem premissas e manutenção.** Hummingbot examinado aceita equivalências entre quotes estáveis; não serve de prova de peg. Nautilus/hftbacktest modelam fills com hipóteses e precisam dados próprios; relato recente de settlement simultâneo reforça teste por evento. Alphalens-reloaded compartilha linhagem/SciPy, não fornece independência adicional para o mesmo IC. Releases recentes também mudam filtros, APIs e convenções.

## Análise econômica por frente

| Frente | O que merece investigação | O que decide antes do lucro |
| --- | --- | --- |
| Spot/ranking | Universo por data, ranking residual e atribuição BTC/ETH/tamanho | Delistings, turnover, hedge/borrow e net return sobre mesmo capital |
| Carry/basis | Convergência/funding e fragmentação de capital | Margem por perna, taxa realmente liquidada, financiamento e desmonte; manter piloto congelado |
| Valor relativo | Spreads com parâmetros estimados só em treino | Cointegração não prova short disponível, estabilidade ou execução |
| Eventos/news | Surpresa e fluxo com primeira publicação comprovada | Revisões, deduplicação e resposta temporal; LLM não recebe autoridade de capital |
| Microestrutura | Limites de fill/shortfall e falha de perna | L2/trades sequenciados; sem fila observada, não fabricar fill rate |
| On-chain/stables | Fluxos e concentração com rótulos conhecidos na data | Clustering revisado, finalização, chain/bridge, peg e resgate |
| Lending/staking | Renda por índice/shares e desconto contra fila | Reserva de custos, saque, tempo sem recompensa e perdas de conversão |
| LP | Fees menos seleção adversa contra rebalanceamento | Ticks/posição, gas/hedge e capital; pool agregado não é retorno individual |
| Opções | Superfície/risco relativo com bid/ask compatíveis | Settlement/currency, spread, hedge e margem; mark não é fill |
| Modelos avançados | Somente erro incremental sobre baseline simples | Amostra, calibração e custo de seleção; RL/transformer adiado |

Um resultado externo desfavorável merece destaque: no paper de fatores cripto, substituir a perna vendida por BTC altera a significância de estratégias de momentum. Portanto “hedge viável” pode mudar o que parece oportunidade. Não importamos os retornos 2014–2018 para o presente. [Liu, Tsyvinski e Wu](https://www.nber.org/papers/w25882).

## Resultado econômico histórico conferido

Os dois casos primários **já registrados** do estudo Aave usam capital total de 5.000 USDC, com 55 USDC reservados para os custos do protocolo e 4.945 USDC emprestados. A suíte desta rodada reconcilia essas contas às respostas RPC preservadas; não escolhemos os casos mais lucrativos da grade.

| Período histórico | Capital total | Principal que rende | Líquido após custos registrados | Sobre capital total | Cenário de perda de 5% na saída |
| --- | --- | --- | --- | --- | --- |
| 2024-06-01 a 2025-06-01 | 5.000 USDC | 4.945 USDC | 232.41 USDC | 4.65% | -29.21 USDC |
| 2025-06-01 a 2026-06-01 | 5.000 USDC | 4.945 USDC | 110.17 USDC | 2.20% | -145.34 USDC |

O cenário de saída desfavorável torna negativos os dois casos. Isso demonstra sensibilidade a perda/conversão, sem atribuir probabilidade a ela. Os custos são cenários registrados, não tarifas pessoais verificadas. Resultado condicional histórico, não lucro executado nem previsão. Fonte e hashes: [resumo dos casos primários](aave_historical_summary.json); método e reprodução em [EXPERIMENTS](EXPERIMENTS.md).

## Respostas finais às dez perguntas

| Pergunta | Resposta |
| --- | --- |
| 1. O que realmente faz e o que preservar? | Pesquisa multi-mecanismo, com controles de dados/custos e estudos históricos. Métricas/snapshots/contabilidade passaram no escopo testado. H1–H6/H9 mantêm seus estados de encerramento; H7/H8 e pilotos futuros não foram ativados. |
| 2. Que informação usa pouco ou precisa distinguir melhor? | Identidade quote/settlement/chain, universo PIT, vintages de entidades/macro, eventos funding por contrato, filas de resgate e trajetórias de execução. |
| 3. Está estreito demais? | O discovery operacional é direcional e limitado em mapas de símbolos; o projeto de pesquisa já inclui outras famílias. Ampliar universo por pergunta, preservando fracassos e custos, é mais útil que adicionar moedas indiscriminadamente. |
| 4. Quais mercados investigar? | Todos os nove domínios da tabela acima têm hipótese/condição necessária. Não são nove estratégias aprovadas; composiçõesX01–X06 consolidam o trabalho. |
| 5. O que perde interesse com custos? | Arbitragem de quotes sem conversão/caixa, carry sem margem por perna, pequeno lending com custos fixos, LP avaliado só por fees e momentum sem hedge viável. São condições de rejeição, não declaração universal de que esses mercados perdem dinheiro. |
| 6. Quais fontes/implementações ampliam capacidades? | SciPy/NumPy/sklearn para referência já disponível; Alphalens/arch para ranking/validação; cryptofeed/hftbacktest/Nautilus para execução isolada; contratos/RPC/PIT para dados. Escolher adapter depois do contrato e licença. |
| 7. O que é transferível/atual? | Métodos de decomposição, contabilidade, clocks e controles. Retornos externos são condicionais e NOT_DIRECTLY_COMPARABLE. API/release atuais foram consultados; performance histórica não virou E6 local. |
| 8. Onde há vantagem e commodity? | Reprodução de índices, rejeição de dados inválidos e métricas testadas são capacidades úteis já existentes. Splits, IC e simuladores são parcialmente commodity. Novo componente só precisa cobrir contrato/intervalo/execução que hoje não se representa. |
| 9. Maior ganho incremental? | K01/K05/K07/K11 primeiro; K02 já validado. X01 ranking+universo+hedge e X02 índice+custos+stress são hipóteses concentradas, condicionadas aos gates. |
| 10. Até cinco testes sem capital? | F01 identidade completa; F02 corroboração Aave após resolver acesso; F03 gate PIT para ranking residual; F04 falha parcial/caixa por perna; F05 intervalos e registro de seleção. Protocolos e métricas no arquivo EXPERIMENTS. |

## Decisão prática e limites

Avançar primeiro nos contratos de identidade e labels de **novas** pesquisas; conservar os cálculos que passaram. Aave tem reprodução contábil favorável e uma falha de acesso documentada. Não há lucro novo validado, comparação de velocidade entre engines ou autorização de capital. Hipótese sem dados segue bloqueada; teste futuro não pode ser antecipado.

A rodada de pesquisa foi fechada com os testes mínimos admissíveis e bloqueios explícitos previstos no próprio mandato. Isso não significa auditar integralmente todos os arquivos/repos nem validar economicamente todas as oportunidades. A adoção dos componentes e os experimentos condicionais são próximos gates, não atividades executadas escondidamente.

## Arquivos da entrega

- [BASELINE.md](BASELINE.md): projeto, dados, proteção e CI.
- [SURVEY.md](SURVEY.md):53 candidatos,23 fichas, artigos, licenças, releases/issues e fontes.
- [CAPABILITY_MATRIX.md](CAPABILITY_MATRIX.md):18 capacidades, ranking, categorias, scores e composições.
- [EXPERIMENTS.md](EXPERIMENTS.md):6 benchmarks, suíte, Aave e 5 próximos protocolos.
- [DECISIONS.md](DECISIONS.md): manter, ampliar, adiar e rejeitar premissas.
- [REGISTRY.json](REGISTRY.json): registro único; [MANIFEST.json](MANIFEST.json): integridade do pacote.

Evidência local completa em `C:\Cripto\operacao\relatorios\OPEN_SOURCE_20260911T0233`; documentação canônica em `docs/open_source_research/20260911T0233`. O pacote entregue contém os relatórios e recibos técnicos, sem credenciais, dados privados ou redistribuição integral dos artigos/códigos externos.
