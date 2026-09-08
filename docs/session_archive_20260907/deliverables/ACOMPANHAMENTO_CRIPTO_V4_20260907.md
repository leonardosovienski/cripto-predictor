# Cripto — foco em lucro líquido

**Objetivo confirmado: terminar com mais dinheiro do que começou, depois de todos os custos. Sem exigir superar Selic, Bitcoin ou qualquer outro investimento. Você não precisa escolher a corretora agora.**

A escolha de moedas e corretoras fica aberta para a pesquisa. A infraestrutura já implementada coleta Binance spot em USDT; isso não significa cobertura de todas as corretoras ou criptos do mundo.

## O que foi ajustado

- Retirada a exigência de uma referência de investimento e removidas as carteiras de comparação do acompanhamento futuro.
- Retirado o limite da amostra inicial de 240 moedas. Agora a busca percorre todos os pares Binance spot/USDT atualmente negociáveis, com as exclusões declaradas e os mesmos filtros de dados e liquidez.
- Mantida a regra de considerar ganhos, perdas e custos, sem forçar uma entrada quando o cálculo não oferece margem positiva.
- Atualizado o acompanhamento existente para essa configuração. Evidências anteriores foram preservadas.

## Resultado da busca ampliada em 07/09/2026

| Verificação | Resultado |
|---|---:|
| Pares spot/USDT ativos no catálogo | 487 |
| Pares após as exclusões declaradas | 472 |
| Pares com dados e liquidez suficientes | 44 |
| Pares aprovados pela regra atual | **0** |
| Testes de software aprovados | 46 |

Portanto, o diagnóstico atual continua sem entrada simulada. A retirada da comparação com Selic não transforma uma previsão desfavorável em lucro. Nenhuma ordem foi enviada e nenhum dinheiro foi movimentado.

## Como será acompanhado

Primeira janela em **13/09/2026 às 21h de Brasília**; primeiro resultado semanal possível em 20/09 às 21h. São 12 janelas previstas, com última saída em 06/12 às 21h. O computador precisa estar ligado e o aplicativo aberto. Decisões são registradas antes das cotações de entrada; uma janela perdida não será reconstruída como observada a tempo. O acompanhamento avisará quando houver mudança relevante, falha ou conclusão.

As marcas de preços em USDT usam hipóteses explícitas de custos. Taxas de conta, conversão e impostos desconhecidos não serão tratados como zero, e uma marca positiva em USDT não será apresentada como lucro líquido confirmado em reais. A documentação da Binance descreve comissões específicas por conta/par. [Fonte oficial](https://developers.binance.com/en/docs/products/spot/faqs/commission_faq).

As 12 semanas fornecem observações novas e testam a operação do registrador. **Ainda não há lucro demonstrado nem prazo garantido para obtê-lo.**
