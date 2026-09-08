# Continuação do seletor de moedas — 07/09/2026

**A base existente foi aproveitada. A próxima versão já calcula ganhos, perdas e custos e pode decidir não selecionar nenhuma moeda. Ainda não demonstrou lucro.**

O trabalho desta rodada teve dois resultados concretos. Primeiro, corrigi o tratamento de moedas que mudaram de nome ou de par. Segundo, implementei um protótipo que considera quanto cada cenário histórico ganhou ou perdeu, com margem para incerteza, em vez de apenas contar grandes altas.

Dos 13 casos problemáticos da rodada anterior, dez tiveram preço de referência reconstruído. BTT, CVP e VIDT continuam sem retorno verificável no horizonte original e agora aparecem como **desconhecidos** no dataset derivado. Não se atribui perda total por conveniência. A versão original permanece preservada como histórico da pesquisa.

| Caso antigo | Tratamento | Retorno bruto de referência em 7 dias |
|---|---|---:|
| NPXSUSDT | PUNDIXUSDT; 0.001 unidade(s) por antiga | -37,34% |
| BZRXUSDT | OOKIUSDT; 10 unidade(s) por antiga | 129,67% |
| BTTUSDT | BTTCUSDT; 1000 unidade(s) por antiga | desconhecido |
| HNTUSDT | HNTBUSD × BUSDUSDT | -1,09% |
| FTTUSDT | FTTBUSD × BUSDUSDT | -11,66% |
| COCOSUSDT | COMBOUSDT; 1 unidade(s) por antiga | -16,49% |
| OCEANUSDT | FETUSDT; 0.433226 unidade(s) por antiga | -21,30% |
| CVPUSDT | saída não verificada | desconhecido |
| MATICUSDT | POLUSDT; 1 unidade(s) por antiga | 3,43% |
| FTMUSDT | SUSDT; 1 unidade(s) por antiga | -19,35% |
| BNXUSDT | FORMUSDT; 1 unidade(s) por antiga | 42,55% |
| VIDTUSDT | saída não verificada | desconhecido |
| EOSUSDT | AUSDT; 1 unidade(s) por antiga | -15,72% |

Esses são preços de referência de fechamento e direitos de conversão; não são vendas realizadas. HNT e FTT usam o preço em BUSD convertido pelo BUSD/USDT observado, com uma perna adicional de custo na conta líquida. Não foi suposta paridade perfeita. O BTT novo começou a negociar depois do prazo da operação antiga; usar esse preço posterior seria alterar o teste.

As proporções foram conferidas em fontes oficiais, incluindo [NPXS/PUNDIX](https://www.binance.com/en/support/announcement/detail/3776ecbf694a4dfda138c0d7262ea4b2), [BZRX/OOKI](https://www.binance.com/en/support/announcement/detail/dff27dc6bcbb432c902bcbea5e24ddfa), [OCEAN/FET](https://www.binance.com/en/support/announcement/detail/3dc0eae584cd4accb34cb914dacf670d), [MATIC/POL](https://www.binance.com/en/support/announcement/detail/619c4929fc3f4a0d9df7f9ae1d4519a5) e [BNX/FORM](https://www.binance.com/en/support/announcement/detail/7d5accdcf8f446f3ba3d79f8747a28e2). Todos os 13 registros têm suas fontes no JSON; consulta em 07/09/2026. As 13 novas respostas de preços foram registradas às 19:25 UTC, com URL e hash. Data do evento e hora da consulta são campos diferentes.

**A correção não recuperou a estratégia anterior.** Mantendo exatamente suas escolhas de 2025–2026, a carteira continua negativa: aproximadamente -97,83% com perda total apenas no caso VIDT ainda desconhecido, ou -97,33% se essa posição tiver retorno zero. São cenários de diagnóstico, não uma faixa garantida de perda real; o P&L executável exato permanece desconhecido.

## Como a nova regra decide

1. Compara a moeda com os mesmos 200 exemplos históricos usados como vizinhos, preservando preços, volume, volatilidade e atraso de informação.
2. Calcula o ganho ou a perda líquidos de cada exemplo, com custos assumidos. Duas altas grandes deixam de esconder muitas perdas pequenas.
3. Agrupa os exemplos pela semana de origem para reduzir o peso artificial de várias moedas subindo juntas.
4. Desconta uma margem heurística para incerteza. Essa margem não é probabilidade calibrada nem limite estatístico garantido.
5. Só admite até cinco candidatos com margem positiva, a 20% cada. As vagas não preenchidas ficam em caixa simulado. Se houver um desfecho desconhecido entre os vizinhos, a moeda não é aprovada; esse exemplo não é apagado do treinamento.

Na fotografia de 07/09 já utilizada anteriormente, **nenhuma das 14 moedas passou**. A resposta do protótipo foi **100% em caixa simulado**. Isso mostra que ele consegue se abster; não prova que saberá escolher as próximas altas ou que sua margem está calibrada. A lista mantém o universo anterior para isolar a mudança de critério; não é uma seleção completa do mercado e contém RLUSD, que exige classificação no universo futuro. O helper de classificação por nome já evita excluir JUP/SYRUP como se fossem produtos alavancados, sem rescrever a amostra antiga.

## O que fazer a seguir

O próximo teste deve registrar as escolhas **antes** dos movimentos seguintes e comparar o retorno líquido com alternativas simples, incluindo ficar sem exposição. Antes de ativá-lo, faltam três itens concretos:

- Completar o universo e o calendário de migrações/suspensões com a hora em que cada informação ficou disponível. Os 13 casos corrigidos não são um cadastro completo de todos os eventos.
- Verificar preços de entrada/saída, atraso e custos numa simulação acompanhada ao vivo. Os custos atuais continuam assumidos; retornos em USDT também precisam de tratamento explícito de câmbio para comparação em BRL.
- Fixar uma amostra e um critério econômico suficientes. Algumas semanas favoráveis não demonstram lucro repetível. Atestado de poder/harness e gates de execução continuam necessários antes de promoção formal.

A primeira semana futura possível deste protocolo é 14/09/2026. Os resultados ainda não existem. Esta rodada preparou código, regras e uma execução diagnóstica; **não iniciou agendamento ou acompanhamento automático**. Os períodos 2024–2026 já vistos continuam exploratórios e não serão apresentados como novo teste independente. Foram feitos zero novos testes de performance histórica da V2, conforme o orçamento registrado antes de consultar os preços corrigidos.

Validação: 30 testes direcionados passaram, incluindo conservação de quantidade nas migrações, censura sem apagar perdas, custos, dependência entre moedas e capacidade de recusar uma carteira desfavorável. Ruff/Pyright passaram. A reprodução em modo offline gerou resultado e dataset derivados idênticos byte a byte. Protocolo: `bbe7a8b`; implementação inicial: `34b599a`. Produção, coleta, custos congelados e evidência anterior preservados.
