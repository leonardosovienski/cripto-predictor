# Teste histórico da regra atual de cripto

**Concluído em 07/09/2026: lucro simulado zero. A regra não abriu nenhuma operação nas 140 semanas avaliadas.**

| Medida | Resultado |
|---|---:|
| Período dos resultados | 01/01/2024 a 06/09/2026 |
| Semanas avaliadas | 140 |
| Símbolos no catálogo histórico pesquisado | 661 |
| Registros diários coletados ou reutilizados | 727.447 |
| Candidatos com dados e liquidez suficientes, somados por semana | 13.996 |
| Operações selecionadas | **0** |
| Semanas inteiramente em caixa simulado | **140** |
| Capital hipotético inicial | 5.000 USDT |
| Capital hipotético final | **5.000 USDT** |
| Lucro simulado | **0 USDT / 0%** |
| Taxa de acerto das operações | Indefinida: nenhuma operação |

Os 13.996 candidatos são ocorrências de símbolos em semanas diferentes, não 13.996 moedas distintas. O universo cobre pares históricos Binance spot/USDT, incluindo símbolos retirados de negociação; não cobre todas as corretoras. O caixa foi uma referência contábil sem rendimento em USDT, não dinheiro realmente depositado.

## O que isso revela sobre a qualidade

**A configuração atual não demonstrou capacidade de gerar lucro nesse histórico.** Ela recusou todas as entradas. Isso mede a ausência de atividade e o resultado da carteira simulada, mas não permite calcular acerto, ganho médio ou qualidade de operações que nunca aconteceram.

Em 12.730 avaliações, a estimativa final não teve margem positiva. Outras 1.265 tinham um desfecho desconhecido entre os casos históricos semelhantes; uma tinha poucas semanas distintas de referência. Em 1.448 casos a média dos exemplos era positiva antes da penalidade de incerteza, mas nenhuma margem final passou do zero. A ausência de operações foi confirmada pelos cálculos independentes.

O próximo problema de pesquisa é definir uma regra que produza sinais economicamente úteis e testá-la de forma registrada. Reduzir o filtro até aparecer lucro neste mesmo histórico não demonstraria qualidade. Também não basta interpretar a espera por novas semanas como caminho garantido para lucro.

## Como foi medido

Foi usada a regra já existente, sem ajustes após os resultados: treinamento fixo de 2021–2023, 200 casos semelhantes, mesma penalidade de incerteza e até cinco posições de 20%. Cada segunda-feira usa somente os dados anteriores até o sábado; as decisões são gravadas antes de anexar os desfechos seguintes.

A simulação prevê entrada na abertura de segunda e saída no fechamento de domingo, com preços diários de referência. O cenário principal assume 0,10% de taxa e 0,10% de deslizamento em cada perna. Cenários de custo maiores e menores deram o mesmo zero, pois nenhuma compra foi selecionada. Não houve comparação com outros investimentos.

Como os anos avaliados já haviam sido consultados na pesquisa, este é um diagnóstico histórico adaptativo, não validação independente. Foram preservadas lacunas, dias parciais e desfechos desconhecidos; não se inventaram preços de saída. O catálogo histórico reduz o viés de olhar apenas moedas ainda ativas, mas sua cobertura e a negociabilidade em cada data não estão certificadas.

## Conferência e reprodução

Passaram 53 testes de software. A conferência por implementação independente verificou 1.133 respostas brutas, 32 conjuntos de indicadores, seus 200 vizinhos e notas, além das 560 contas semanais dos quatro cenários de custo. A repetição completa sem rede produziu decisões e resultados idênticos byte a byte.

O pacote de reprodução contém código, treinamento fixo, dados brutos e normalizados, protocolo, testes e resultados esperados. O lucro simulado de zero não representa lucro real realizado, resultado líquido em reais, ausência de risco nem comprovação de segurança. Nenhuma ordem foi enviada; o acompanhamento futuro e sua regra não foram alterados nesta rodada.
