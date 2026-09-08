# Coleta e auditoria feitas agora — BTC, 08/09/2026

Foi possível coletar dados públicos e conferir as contas agora. O resultado recente **não sustentou lucro positivo sob os custos adversos registrados**. A diferença é entre executar uma auditoria hoje e já possuir 84 dias de observações futuras; a segunda coisa ainda não existe.

## Resultado dos 84 dias encerrados

Período: **16/06/2026, 00h UTC, a 08/09/2026, 00h UTC**. Referência de **5.000 USDT por cenário**, com até 1.250 USDT na perna spot. Uma posição hipotética de 0,018 BTC comprada no spot e vendida no perpétuo, quantidade fixa. Cada cenário é financiado separadamente.

| Cenário | Lucro/prejuízo modelado | Retorno sobre 5.000 USDT |
|---|---:|---:|
| Base | **+10,56 USDT** | +0,211% |
| Adverso | **−6,97 USDT** | −0,139% |
| Estresse | **−21,65 USDT** | −0,433% |

O funding líquido de sinais, antes de aplicar custos, somou 17,22 USDT. A mudança do diferencial entre os preços das pernas contribuiu −0,12 USDT. No cenário base, taxas e deslizamento assumidos consumiram 6,54 USDT. No adverso, consumiram 18,32 USDT, acrescidos de 5,75 USDT de custo fixo proporcional. No estresse, somente funding positivo foi reduzido à metade e foi descontado um choque inicial adicional de 0,5% do valor spot.

Foram verificadas **251 liquidações de funding** e **2.016 horas de mark price**. Os drawdowns calculados pelas marcas diárias de encerramento foram aproximadamente 0,124%, 0,339% e 0,470%, respectivamente. Houve 1, 1 e 4 semanas negativas entre as 12 semanas. O caixa separado permaneceu positivo no teste horário registrado com salto adicional de 30%; isso não certifica as regras reais de liquidação da corretora.

As entradas e saídas históricas usam aberturas de candles com custos assumidos. Não existem livros históricos de ofertas ou execuções reais certificados para esses pontos. A abertura do candle final foi isolada de sua máxima, mínima e fechamento. **83 dos 84 dias já estavam dentro do período anteriormente consultado**: baixar os dados novamente não os transforma em teste independente fora da amostra.

## O que foi observado ao vivo

Entre aproximadamente **03h40 e 03h45 de Brasília**, foram obtidos **11 pares válidos de livros Binance spot/perp**, espaçados por 30 segundos. A primeira e a última cotações foram fixadas pelo protocolo; não houve escolha posterior de uma entrada favorável. A duração entre elas foi de 300,12 segundos.

O preço spot BTC/USDT também foi consultado na **OKX** nos 11 momentos. A maior diferença absoluta entre os preços médios foi **0,873 ponto-base**, aproximadamente **0,00873%**. As amostras cumpriram as verificações de horário, validade dos livros e tolerância entre fontes. Isso confere a consistência dos preços; a OKX não autentica os eventos internos de funding da Binance e não certifica negócios simultâneos.

Para a posição hipotética de 0,015 BTC, as marcas de encerramento após cinco minutos foram:

| Cenário | Resultado modelado de entrada e saída |
|---|---:|
| Base | **−5,87 USDT** |
| Adverso | **−16,45 USDT** |
| Estresse | **−22,34 USDT** |

A variação do diferencial das pernas contribuiu apenas +0,0126 USDT. O cenário base descontou 5,8809 USDT de taxas/deslizamento de entrada e saída. Uma consulta pública adicional de funding estritamente entre as duas cotações não retornou pagamentos. Uma janela de cinco minutos serve para verificar custos e cotações; não substitui um teste de carry mantido por 84 dias. Nenhuma hora inteira ficou contida no intervalo; a margem horária dessa observação curta permanece não certificada.

O diagnóstico separado de comissão cobrada em BTC calculou compra bruta de 0,01502000 BTC, posição vendida de 0,015 BTC e residual de aproximadamente 0,39 USDT. É uma hipótese de tarifa/ativo da comissão, não uma informação da conta e não lucro criado.

## O que passou na auditoria

- **44 respostas públicas** da rodada principal, mais **uma consulta** adicional de funding, com dados brutos, URLs, horários e hashes preservados.
- Reconstrução histórica com **Decimal**, por implementação separada que não importa o normalizador ou o motor contábil principal.
- **334 comparações numéricas**, com maior diferença de aproximadamente **0,00000000000178 USDT**. Conferência de funding, custos, resultado, margem, curvas diárias e semanas.
- Conferência do diário encadeado: decisões anteriores às cotações, resultados ligados às respostas brutas e ausência de troca dos pontos de entrada/saída.
- **1.167 testes aprovados**, incluindo oito novos; Ruff passou e Pyright não encontrou erros. O runtime original passou na verificação de 3.785 arquivos.
- Código congelado antes da coleta. Relatórios antigos e os diários de carry prospectivo e altcoins foram preservados. Nenhuma ordem, conta autenticada ou movimentação de dinheiro.

As duas implementações foram feitas pelo mesmo assistente. A segunda corretora é uma segunda fonte para os preços, mas **não houve auditoria externa de autoria**.

## O que continua desconhecido

As taxas públicas servem como referência: a [documentação Binance de futuros](https://www.binance.com/en/support/faq/detail/360033544231) exemplifica a cobrança pelo valor da operação. A tarifa efetiva da conta é fornecida por um [endpoint autenticado](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account#user-commission-rate), que não foi acessado. Execuções reais, tributos, residência fiscal, conversão para reais e regras efetivas de margem não podem ser certificados por essa coleta pública.

O acompanhamento futuro de 84 dias não foi adiantado nem iniciado retroativamente. A automação nova continua não criada, pelo limite já registrado de uma automação por tarefa; esta coleta imediata não alterou a de altcoins.

**Conclusão:** a coleta e a auditoria disponíveis agora foram feitas. Os dados recentes mostram que o ganho é pequeno e desaparece com custos adversos; ainda não há evidência suficiente para classificar esta estratégia como fonte confiável de lucro líquido futuro.

## Arquivos reproduzíveis

`CRIPTO_AUDITORIA_AGORA.zip` contém código e congelamento, testes, protocolo, diário, respostas públicas, cálculos e auditoria. O `README.md` do pacote explica a reprodução offline. `CRIPTO_AUDITORIA_AGORA.json` registra as métricas e verificações; `CRIPTO_AUDITORIA_AGORA_SHA256.json` identifica a entrega.
