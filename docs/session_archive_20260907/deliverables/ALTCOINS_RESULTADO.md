# Seleção de altcoins por padrões anteriores às altas

Executado em 07/09/2026. **Decisão: não promover esta regra para operação.**

O protótipo foi construído, testado e aplicado a dados públicos. A seleção encontrou maior frequência de altas fortes, mas o resultado da carteira foi negativo e inferior à cesta simples. Isso rejeita a especificação na triagem de pesquisa; não demonstra que toda seleção de altcoins seja impossível.

**O P&L abaixo é uma simulação com premissas de custo e recuperação, não perda realizada nem estimativa confiável de execução.** A auditoria encontrou migrações de tokens entre os dados ausentes. O veredito científico sobre P&L executável permanece `INCONCLUSIVE_DATA_FIDELITY`; a decisão de pesquisa é `DO_NOT_PROMOTE_THIS_SELECTOR`.

O treinamento usou 5.204 observações de 121 símbolos em 156 semanas de 2021–2023: 504 episódios-alvo e 4.700 controles. “Alta forte” significa pelo menos 20% em sete dias e vantagem de pelo menos 10 pontos percentuais sobre BTC. Preço, força relativa, volume e volatilidade foram calculados antes da entrada, com atraso de um dia. Os controles incluem altas menores, lateralização, quedas e casos sem saída observável.

O modelo procura os 200 vizinhos históricos mais próximos, estima a frequência do alvo nesse grupo e escolhe cinco moedas com pesos iguais. As regras, os custos e as datas foram fixados antes da coleta em lote, no commit `444aa02`; implementação e controles sintéticos ficaram registrados em `acaa925` antes do primeiro resultado. Não houve ajuste de modelo, janela ou ativos depois dos resultados.

| Regra simulada | 2024, 52 semanas | 2025–2026, 87 semanas |
|---|---:|---:|
| 5 moedas por padrões semelhantes | -55,10% | -98,67% |
| Cesta das moedas elegíveis | -37,21% | -93,24% |
| 5 moedas por momentum | -67,07% | -97,29% |
| BTC, mesmas semanas de exposição | 80,06% | -52,63% |

Retornos compostos em USDT, reinvestindo o saldo semanal. Entrada na abertura de segunda e saída no fechamento de domingo, preços de referência diários. Custo assumido de 10 bps de taxa mais 10 bps de slippage em cada ponta; inclusive posições mantidas são encerradas e reabertas. Com menos de dez moedas elegíveis, todos os métodos ficam em caixa sem rendimento. Isso ocorreu em nove semanas de julho/agosto de 2026; a linha BTC também segue essa regra e **não é buy-and-hold de BTC**. A semana de 30/12/2024 foi purgada por atravessar os segmentos. A última posição avaliada entrou em 31/08/2026 e terminou em 06/09/2026.

A diferença média semanal de log-retorno contra a cesta, no segundo segmento, foi -1,87%; intervalo de 95% por bootstrap de blocos de quatro semanas: [-3,43%; -0,45%]. A conta agrupa as moedas por semana, respeitando dependência temporal e de mercado. É inferência condicional a esta busca exploratória, sem ajuste por todo o histórico de pesquisa do projeto. O planejamento conservador tinha poder apenas para efeitos grandes: cerca de 0,61 desvio padrão semanal no segundo segmento. Não se declara ausência de efeitos pequenos.

O achado que responde à ideia original é concreto: no segundo segmento, a seleção acertou o alvo em **7,18%** das posições (28/390), contra **5,27%** na média semanal da cesta — aumento relativo descritivo de 36%. Em 2024 foram 13,08% contra 8,82%. Essa concentração de altas não gerou vantagem econômica. No segundo segmento somente 133 de 390 posições tiveram retorno bruto positivo; o ganho médio das positivas foi 13,75%, e a perda média das demais foi 13,69%, sob o tratamento de lacunas descrito abaixo. O alvo binário não remunera a gravidade das perdas que o acompanham. Isso é uma explicação compatível com a contabilidade, não uma identificação causal definitiva.

## Conferência das perdas e dos dados

A amostra foi sorteada por hash fixo entre os símbolos do arquivo, sem ranking por retorno ou capitalização atual: 240 pares entre 735 pares USDT catalogados. Foram coletadas 251.930 velas, incluindo BTC de referência. 77 históricos terminam antes do último dia da amostra; não se afirmou que todos sejam deslistagens, pois migrações e pausas também encerram um símbolo. BCHABC e BCHSV não tinham observações dentro do intervalo, confirmado na API e no catálogo de arquivos. Não foram substituídos por vencedores.

Houve sete desfechos ausentes entre todas as moedas elegíveis na avaliação, quatro deles na carteira por analogia: CVP, FTM, BNX e VIDT. A regra pré-fixada atribui perda total a esses desfechos, como stress de recuperação. Isso não pode ser confundido com o valor econômico dos tokens. FTM migrou para S e BNX para FORM, ambos 1:1, conforme [comunicado FTM/S](https://www.binance.com/en/support/announcement/detail/aec6fcbc84b749eeab6690e6bcac2f3d) e [comunicado BNX/FORM](https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2), consultados em 07/09/2026.

Para medir a dependência da decisão dessas premissas, fiz diagnósticos **após o resultado**, preservando posições, sinais e treinamento. Não são novos testes independentes:

| Diagnóstico da carteira por analogia | 2024 | 2025–2026 |
|---|---:|---:|
| Lacunas com retorno zero, demais custos mantidos | -40,56% | -97,43% |
| Todos os custos de negociação zerados, stress de lacunas mantido | -44,72% | -98,18% |
| Custos zerados e lacunas com retorno zero | -26,88% | -96,49% |

Mesmo o último cenário fica abaixo da cesta equivalente nos dois segmentos. Retorno zero nas migrações é uma hipótese diagnóstica; não é avaliação real da troca nem limite superior universal. Não se corrigiu o histórico de rótulos ou se reexecutou o treinamento para favorecer a conclusão. O cálculo independente a partir dos preços brutos confirmou 9.430 retornos individuais, com diferença máxima de 4,45×10⁻¹⁶, e seis carteiras usando Decimal.

Os arquivos públicos permitem incluir símbolos antigos, mas não garantem inventário histórico completo ou ausência de revisões. A hora em que observamos os dados foi 18:50–18:51 UTC de 07/09/2026; disponibilidade histórica após o fechamento é uma premissa de simulação. O arquivo da Binance pode ser revisado, como informa a [documentação oficial](https://github.com/binance/binance-public-data). A exclusão textual de sufixos UP/DOWN/BULL/BEAR também retirou JUP e SYRUP: limitação de cobertura registrada, sem trocar a amostra após ver os resultados.

## Ranking disponível e decisão

Há 14 moedas elegíveis na fotografia de 07/09/2026 00:00 UTC, usando informações até a vela de 05/09. A lista completa e exemplos de vizinhos vencedores e não vencedores estão em `ALTCOINS_RANKING_PESQUISA.md` e no JSON. O horizonte é sete dias, não previsão intradiária. A frequência entre vizinhos não é uma probabilidade futura calibrada. O ranking permanece **resultado de pesquisa de um modelo reprovado**, sem ativação de sinais ou ordens.

Para o objetivo de lucro, encontrar mais episódios de alta não basta. A próxima pesquisa só se justifica com rótulos e identidade de tokens corrigidos, regra de saída e universo historicamente negociável definidos, novo protocolo e evidência nova. Trocar o alvo para retorno líquido esperado seria outra hipótese adaptativa; os períodos já vistos não voltam a ser teste intocado. A família funding/OI/HMM continua congelada.

USDT é a moeda de P&L; conversão USDT/USD 1:1 é apenas premissa. O reporte econômico é em BRL. Com FX constante 5,1253, a ilustração sobre US$5.000 produz perdas de aproximadamente R$14.120 no primeiro segmento e R$25.285 no segundo, sob o stress original. Isso não é previsão de perda nem comparação sincronizada com Tesouro. O benchmark condicional apurado na rodada anterior era R$2.900–2.907/ano sobre R$25.626,50, antes de prêmio de risco e atenção; acessibilidade, imposto aplicável ao operador, FX e fricção real seguem desconhecidos. Não há retorno esperado futuro demonstrado para comparar honestamente com esse hurdle. Exposição cambial também existe nas semanas em caixa USDT.

Validação: 11 testes novos de temporalidade, custos, amostragem e controles sintéticos; oito testes do gate de freeze; 395 respostas brutas com hash conferido; Ruff e Pyright passaram. A reprodução a partir do ZIP extraído gerou resultados, carteiras, amostras e auditoria idênticos byte a byte. Não foram alterados produção, coleta, capital, ledger formal H1–H9, custos congelados ou selos. A pesquisa tem registro próprio em `docs/evidence/altcoin_analogs_20260907/search_log.json`. O pacote inclui dados e scripts para reprodução offline.
