# Correções da pesquisa de criptomoedas — 08/09/2026

Corrigi as falhas técnicas identificadas e retifiquei as conclusões. A suíte completa passou: **1.159 testes**, incluindo **49 novos casos**. Ruff passou e Pyright não encontrou erros. Isso valida o comportamento testado; não comprova lucro futuro nem ausência de todo defeito possível.

## O que ficou corrigido

- O planejador vigente é a versão 3. Rejeita livros cruzados/desordenados, valores não finitos, horários inválidos, JSON ambíguo e fontes inconsistentes. Falhas devolvem código de saída 1. As versões anteriores permanecem para reprodução histórica.
- A auditoria ganhou um leitor e normalizador separados, usando apenas a biblioteca padrão e sem importar o normalizador anterior. Conciliou **532 respostas públicas e 29 séries**. Continua sendo trabalho do mesmo assistente e da mesma fonte de dados; não é uma auditoria externa.
- O observador de carry BTC usa protocolo e código congelados, decisões persistidas antes das cotações, proteção contra processos simultâneos, diário encadeado, conferência dos dados brutos e estado gravado atomicamente. Uma entrada/saída interrompida não pode ser refeita com preço posterior. Dados ausentes permanecem desconhecidos.
- As contas do observador consideram profundidade dos livros, lotes atuais na entrada e saída, custos explícitos, funding com sinal e caixa de margem separado. Taxas reais da conta, execução simultânea, tributos e liquidação efetiva continuam não certificados.
- A referência vigente distingue retorno histórico acumulado, exposição residual, resultado prospectivo e lucro líquido real. Retira a interpretação de que os testes ou o tamanho dos números demonstraram uma estratégia rentável no futuro.

## Resultado econômico preservado

Nenhuma estratégia histórica foi ajustada para produzir um número melhor. Os **28 arquivos de resultados**, **26 arquivos de código/protocolo congelados** e os pacotes anteriores mantiveram seus hashes. Os **12 planos válidos salvos** mantiveram os campos econômicos. Repositório original, runtime e automação/diário de altcoins foram preservados; a conferência do runtime passou em 3.785 arquivos.

Com referência de 5.000 USDT por cenário, de 01/01/2024 a 07/09/2026:

| Modelo | Base | Adverso |
|---|---:|---:|
| Carry contínuo BTC (AR1) | +424,25 USDT | +341,13 USDT |
| BTC com vencimento (BR1) | +230,17 USDT | +110,07 USDT |

São lucros **modelados e acumulados em 980 dias**, não mensais. O BR1 não melhorou o AR1 e teve apenas cinco operações. Em 2026 até o corte, o AR1 BTC adverso contribuiu apenas 5,75 USDT. Resultados negativos, estratégias sem entradas e custos fixos hipotéticos continuam visíveis na documentação. A redução de aproximadamente 58 USDT de exposição residual em uma cotação não representa lucro criado pelo planejador.

## Acompanhamento preparado; agendamento pendente

O pré-teste passou com **seis requisições públicas**, sem conta autenticada ou ordem. O diário contém somente um registro de pré-teste; o estado é **WAITING**, sem posição prospectiva nem lucro registrado. Uma chamada normal antes do início preservou esse diário.

O protocolo prevê uma única posição hipotética de 84 dias, com coletas às **21h15 de Brasília**, primeira janela em **08/09/2026** e saída em **01/12/2026**. Uma rodada dessa duração não basta para confirmação estatística de lucro.

**A automação nova não foi criada.** O aplicativo recusou uma segunda automação nesta tarefa, que já possui o acompanhamento de altcoins. Solicitei autorização para criar uma tarefa separada, preservando a anterior. O prompt completo está preparado em `docs/evidence/carry_forward_20260908/scheduling.json` no pacote. Sem essa autorização, não há promessa de coleta automática. Não alterei a automação de altcoins nem criei um cron alternativo.

Quando autorizado e agendado, o computador e o aplicativo precisam estar em execução para o acesso aos arquivos locais. [Documentação oficial de tarefas agendadas](https://learn.chatgpt.com/pt-BR/docs/automations).

## Entrega e reprodução

`CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip` contém o código vigente e suas dependências locais, os 49 testes novos, protocolo/congelamento, registro de falhas e correções, runbook, cotações salvas para reprodução e a fotografia do pré-teste. Não substitua o diário operacional pela cópia do pacote.

Os dados históricos completos continuam nos pacotes anteriores. `CRIPTO_CORRECOES_VERIFICACAO.json` registra os checks e o pré-teste. `CRIPTO_CORRECOES_SHA256.json` identifica os arquivos entregues. A referência consolidada está em `docs/CURRENT_RESEARCH_STATE_20260908.md` dentro do ZIP.

Os campos de lucro real e expectativa futura validada permanecem nulos. A parte que depende de observações futuras, dados reais de conta ou auditoria externa continua explicitamente pendente, em vez de receber uma marca artificial de “resolvido”.
