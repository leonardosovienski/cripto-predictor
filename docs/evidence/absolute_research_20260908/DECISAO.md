# Resultado da investigação histórica de lucro absoluto

O carry contínuo de BTC e ETH apresentou lucro simulado positivo mesmo nos cenários desfavoráveis registrados. É uma evidência histórica mais forte do que o checkpoint anterior, dentro de um modelo explícito de custos e margem. **Ainda não demonstra lucro líquido real nem confirma que o resultado se repetirá.** O carry condicionado ao funding não resistiu aos custos maiores. A regra nova de momentum foi fortemente negativa.

Cada linha abaixo usa **separadamente 5.000 USDT hipotéticos**. Período: 01/01/2024 a 07/09/2026, 980 dias, 140 semanas. Não somar os ganhos como se viessem de uma única carteira. Não são valores anuais.

| Hipótese | Cenário base | Custos adversos | Custos adversos + funding comprimido |
|---|---:|---:|---:|
| AR1 — Carry contínuo BTC | **+424,25 USDT (+8,49%)** | **+341,13 USDT (+6,82%)** | **+104,12 USDT (+2,08%)** |
| AR1 — Carry contínuo ETH | **+328,94 USDT (+6,58%)** | **+250,01 USDT (+5,00%)** | **+65,94 USDT (+1,32%)** |
| AR2 — Carry condicionado BTC | +17,79 USDT | −82,26 USDT | −117,42 USDT |
| AR2 — Carry condicionado ETH | +30,69 USDT | −80,18 USDT | −130,09 USDT |
| AR3 — Momentum de moedas líquidas | **−4.945,35 USDT (−98,91%)** | **−4.974,35 USDT (−99,49%)** | Não se aplica; com deslizamento de 90 bps por lado: −4.992,77 USDT |

## O que mudou e por quê

O projeto ganhou um coletor público limitado, dois modelos de carry, uma regra simples de seleção spot e uma auditoria independente dos resultados. Tudo está em outro worktree, iniciado no encerramento completo fbf4c71; nenhuma ordem ou conta foi usada. O protocolo foi versionado em e41773a e as cinco séries registradas antes da primeira avaliação. Não houve busca de parâmetros após os resultados. As famílias congeladas, os arquivos antigos e o observador v6 permaneceram preservados.

O seletor anterior não ficou sem universo: existiam 13.996 candidatos elegíveis nas 140 semanas. Em 12.730 casos foi possível calcular o score; apenas 1.448 tinham média de payoff positiva antes da penalidade. Nenhum permaneceu positivo depois dela. A mediana dessa média era −2,45% em log, e a penalidade mediana era 7,49% em log; são estatísticas de vizinhos de treino, não retornos de operações realizadas. Outros 1.265 casos foram bloqueados por vizinhos censurados, e um por poucas semanas distintas. O treino continha somente 5 a 25 observações efetivas segundo a heurística de dependência. Isso explica a abstinência; não demonstra que retirar a penalidade criaria uma vantagem. O piloto mantém a regra original.

AR1 usa aproximadamente 25% do capital inicial para comprar a moeda e reserva o restante em USDT para a posição vendida equivalente no perpétuo. A quantidade fica fixa durante os 980 dias. A hipótese é receber os pagamentos de funding sem depender da valorização da moeda; a reserva maior enfrenta o risco de a posição vendida consumir margem. A demanda por posições compradas alavancadas pode gerar funding positivo, mas o sinal se inverte. [Mecânica de funding da Binance](https://www.binance.com/en/support/faq/detail/360033525031).

AR2 verifica, a cada 28 dias, os 28 dias de funding conhecidos com um dia de atraso. Só entra se a soma superar 1,35% — cobertura de um custo conservador de ida e volta com uma margem de 50%. A posição dura 28 dias e é fechada antes da próxima. Houve apenas três operações completas no BTC e quatro no ETH, todas em 2024. Os períodos seguintes ficaram em caixa. O filtro evitou exposição, mas também descartou grande parte dos recebimentos e adicionou gastos de entrada e saída.

AR3 escolhe até cinco moedas com retornos positivos em 7 e 30 dias, ordenadas pelo retorno de 30 dias, depois de exigir histórico completo e liquidez. Os sinais terminam no sábado; o preço de entrada é a abertura da segunda-feira. As posições duram uma semana. A regra operou 630 vezes, em 138 semanas, com duas semanas em caixa e exposição média de 90%. Foram 231 ganhos e 399 perdas, acerto de 36,67%. Mesmo sem deslizamento adicional, mas descontando taxas, perdeu 4.929,71 USDT. Portanto, o problema desta regra não se resume aos custos. Não a promover nem tentar salvá-la com ajustes nesta rodada.

## Custos e tamanho das posições

No carry base, as taxas assumidas são 10 bps por lado no spot e 5 bps no perpétuo, mais 5 bps de deslizamento em cada perna. No adverso, as taxas sobem para 20 e 10 bps, com 20 bps de deslizamento em cada perna e uma despesa residual de 25 USDT por ano. Essa despesa continua após a primeira entrada, inclusive nas semanas em caixa; não é uma tarifa observada. O cenário de compressão mantém esses custos, corta pela metade os recebimentos positivos de funding, preserva todos os pagamentos negativos e acrescenta uma perda de 0,5% do nocional spot em cada entrada por falha de sincronização das pernas. As três configurações estavam registradas antes dos resultados.

No momentum, o cenário base cobra 10 bps de taxa e 10 bps de deslizamento por lado; o adverso usa a mesma taxa e 40 bps de deslizamento. Uma posição repetida é encerrada e reaberta semanalmente, pagando novamente. O modelo mantém o peso de posições sem preço e só usa conversões de identidade previamente documentadas.

Depois da primeira rodada, a revisão encontrou que os filtros atuais da corretora não deveriam determinar o tamanho histórico. A correção foi registrada em 3ceef8f antes da nova execução: uma grade fixa de 0,001 unidade é uma convenção da simulação, e os filtros atuais são apenas diagnóstico presente. O teste altera radicalmente os filtros atuais e exige decisões e quantidades históricas idênticas. A correção **não alterou nenhuma quantidade nem os resultados econômicos**. Não significa que a grade e as restrições eram realmente essas em toda a história. Os dados e resultados anteriores continuam guardados.

## Perdas, exposição, margem e concentração

| Série, cenário base | Operações completas | Semanas expostas / caixa | Maior queda entre marcações |
|---|---:|---:|---:|
| Carry contínuo BTC | 1 hedge; 4 transações de perna | 140 / 0 | 0,164%, fechamentos diários e saída final |
| Carry contínuo ETH | 1 hedge; 4 transações de perna | 140 / 0 | 0,137%, mesma medição |
| Carry condicionado BTC | 3 hedges; 12 transações de perna | 12 / 128 | 0,121%, mesma medição |
| Carry condicionado ETH | 4 hedges; 16 transações de perna | 16 / 124 | 0,121%, mesma medição |
| Momentum | 630 posições semanais | 138 / 2 | **99,15%**, fechamentos semanais |

Essas quedas de carry são de uma carteira perfeitamente pareada no modelo. **Não medem a perda possível em falha de corretora, liquidação, descolamento prolongado, erro de execução ou indisponibilidade.** A reserva inicial é de aproximadamente 75%; o nocional cresce ou diminui com o preço, pois a quantidade não é rebalanceada. O relatório JSON também guarda a exposição bruta média das duas pernas, não apenas o delta líquido igual a zero.

Foram examinadas máximas horárias de marcação, sem considerar o spot como garantia transferível. A conta reserva 1% do nocional para manutenção e 0,5% para encerramento, ambos parâmetros conservadores assumidos. No carry contínuo adverso, o menor excedente calculado foi **1.597,12 USDT no BTC** e **2.490,07 USDT no ETH**. Acrescentando uma alta instantânea de 30% à máxima de cada hora, os menores excedentes foram **482,88** e **1.664,75 USDT**, respectivamente. Nenhum cenário registrado rompeu essa barreira, inclusive o de compressão. Isso é um teste de suficiência sob hipóteses, não certificação das regras reais de liquidação, que usam o preço de marcação. [Protocolos de liquidação da Binance](https://www.binance.com/en-AU/support/faq/detail/360033525271).

No carry contínuo adverso, as cinco semanas de maior ganho representaram 19,15% dos incrementos positivos no BTC e 27,25% no ETH. Subtraindo aritmeticamente essas cinco contribuições, ainda restaram +268,17 e +173,77 USDT. Isso descreve concentração; não simula outra estratégia. Os ganhos também estão concentrados temporalmente nos anos anteriores:

| Carry contínuo, custos adversos | 2024 | 2025 | 2026 até o corte |
|---|---:|---:|---:|
| BTC | +204,67 | +130,71 | **+5,75 USDT** |
| ETH | +198,97 | +62,37 | **−11,33 USDT** |

Sob compressão, 2026 ficou negativo nos dois: −21,95 USDT no BTC e −25,73 USDT no ETH. O saldo total positivo depende também da história anterior; não caracteriza lucro em todos os regimes. O bootstrap descritivo em blocos de quatro semanas tem limite inferior positivo no adverso dos dois carries contínuos. No cenário de compressão, o intervalo do ETH cruza zero. Esses intervalos não corrigem toda a pesquisa adaptativa passada, não tratam 140 semanas como 140 estratégias independentes e não são probabilidade de lucro futuro. Houve apenas uma entrada e uma saída por ativo no carry contínuo.

## Dados, temporalidade e identidade

O carry usa 68 respostas públicas preservadas: funding, preços diários de negócios spot/perpétuo, preços horários de marcação e catálogos atuais. As fontes têm URL, horário real de obtenção e SHA256. As oito séries normalizadas foram reconstruídas a partir das respostas originais. As séries de preço são contínuas no período exigido; os intervalos de funding foram conferidos sem preenchimento de lacunas. A última vela só fornece a abertura no corte: seus campos posteriores não entram no cálculo. O funding da hora de entrada e os eventos de saída ou posteriores são excluídos.

O universo spot preservado contém 661 históricos, incluindo pares que deixaram de existir; não é uma lista só de sobreviventes atuais. A auditoria refez as 140 ordenações de 13.996 casos elegíveis e conferiu 1.133 hashes originais e 36.830 barras usadas pelas posições escolhidas. Uma operação atravessou a migração de BNX para FORM: mantivemos a proporção de 1 para 1 e o preço do sucessor no dia correto, conforme o registro anterior e o [comunicado oficial](https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2). Não houve desfecho selecionado ainda censurado. A disponibilidade histórica de todo o universo, restrições operacionais e classificação de todos os ativos continuam incompletamente certificadas; há produtos no catálogo além das moedas convencionais. Não ajustamos a composição após ver a perda.

2024, 2025 e 2026 são cortes temporais descritivos, **todos adaptativos**. A pesquisa anterior já havia consultado esses períodos. Não foram convertidos em validação independente. Não há otimização de parâmetros ou refit entre os cortes. Dados de desempenho a partir de 07/09/2026 ficaram reservados; a criação de evidência nova requer regra congelada antes da decisão real de observação. O piloto v6 existente é outra regra e não confirma AR1, AR2 ou AR3.

## O que está demonstrado e o que continua desconhecido

Está demonstrada uma conta histórica reproduzível: os dois carries contínuos terminam com mais USDT após os custos e choques declarados; as alternativas de timing e momentum não resistem à avaliação registrada. O carry contínuo é candidato a uma observação futura separada, com prioridade de investigação para BTC pela menor fragilidade nesta rodada. Não é recomendação para enviar ordens.

Continuam desconhecidos os custos efetivos e o acesso da conta, lotes e filtros históricos, preços de execução simultânea e profundidade, tratamento real de comissões, regras históricas de margem, atrasos/interrupções, ADL, entrega efetiva de funding, risco da corretora e do USDT, conversões, transferências e impostos. A hipótese de taxa paga em USDT mantém as quantidades pareadas; isso não certifica o débito real de taxa em cada mercado. Nenhum custo desconhecido foi certificado como zero. Depois do cenário adverso, ainda caberiam **341,13 USDT extras no BTC** ou **250,01 no ETH** antes de zerar o lucro total; no cenário de compressão, apenas **104,12** e **65,94 USDT**. Esses orçamentos cobrem todo o período, não cada ano.

O objetivo não exige superar outro investimento. A decisão antiga que usava comparação externa não foi reutilizada. Os +54,84 USDT de BTC e +34,62 USDT de ETH do checkpoint anterior continuam preservados, para outro período e outro tamanho. Também foi encontrado e mantido o estudo antigo de SMA200, de julho/2021 a julho/2026: ganhos históricos de 94,70% no BTC e 230,55% no ETH, mas quedas de 36,40% e 38,47% e intervalos cruzando zero. A retirada do benchmark não elimina essas limitações; não rerodamos nem retunamos essa família.

## Validação e acompanhamento

Passaram **58 testes locais direcionados**, Ruff e Pyright. A auditoria Decimal refez 27 ciclos de hedge considerando os cenários de custo, 155.232 verificações de margem horária e 2.520 contas de payoff spot; a maior diferença de um fluxo de carry foi menor que 10⁻¹² USDT. Os controles abrangem informação futura, funding de entrada, sinais negativos, reserva separada do spot, arredondamento, censura e caixa sem operação. Testes de software não provam rentabilidade. Docker, CI remoto e execução em conta não foram validados nesta rodada.

A automação antiga estava ausente. Foi recriada **uma única heartbeat ACTIVE nesta tarefa**, mantendo o nome, o prompt, os caminhos e o domingo às 21h de Brasília. Um tick fora de janela leu o protocolo, os hashes, o treino e o ledger e terminou sem erros; as duas linhas do ledger e seu head permaneceram idênticos. Não houve retrodatação. A primeira entrada segue prevista para 13/09/2026 e a última saída para 06/12/2026. A configuração foi verificada, mas uma execução futura do agendador ainda não ocorreu. O computador e o app precisam estar ativos para o trabalho local agendado. [Documentação oficial](https://learn.chatgpt.com/docs/automations?surface=app).

O protocolo, a correção causal, o histórico de execuções, os dados, os resultados negativos, os logs e a auditoria estão preservados. A entrega reproduzível permite verificar hashes e repetir a conta independente sem consulta pública. Os commits são locais, sem push.
