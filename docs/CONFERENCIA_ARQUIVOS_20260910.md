# Conferência de arquivos e documentação — 10/09/2026

Esta conferência complementa a [publicação do chat](CONFERENCIA_CHAT_20260910.md) e o registro vivo `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909\REVISAO.md`. Ela parte do `main` integrado em `94fc9e769fe6aaf16439e845ca29378701d34886`, após o PR #117. Datas, testes e saldos descritos em registros anteriores são cortes históricos.

## Onde está o necessário

| Local em `C:\Cripto` | Conteúdo e preservação |
|---|---|
| `AGENTS.md`, `CRIPTO.cmd`, `LEIA_PRIMEIRO.md` | Mandato, entrada do ambiente e índice local atual. |
| `pesquisa-20260909` | Checkout operacional, ambiente Python e arquivos de desenvolvimento; confirmar HEAD e checks antes de executar. |
| `auditoria-ampliada-20260910` | Executor LLM manual v3 congelado em `595f1203475d04b01966ac3471bbafd6770dbb4d`; não atualizar pelo código de desenvolvimento. |
| `dados.zip`, `MANIFESTO.json`, `VALIDACAO.json`, `runtime`, `restaurar.py`, `validar.py`, `LEIA-ME.md`, `RETOMAR_NO_CODEX.md` | Pacote original de migração e ferramentas de recuperação; preservar. |
| `restaurado-20260908` | Arquivos originais restaurados, runtimes, sessões, dados, protocolos e diários; preservar integralmente, incluindo `fred_test.csv`. |
| `operacao/dados`, `operacao/saidas`, `operacao/estado` | Dados novos, Feature Store, quotas e estado operacional; não são reconstruídos apenas por clonar o Git. |
| `configuracao/pipeline.env` | Configuração privada; não publicar nem imprimir valores. O arquivo privado antigo na raiz também foi preservado. |
| `operacao/relatorios` | Evidências completas, scripts executados e resultados por commit. |
| `operacao/relatorios/REVISAO_COMPLETA_20260909/chat_closure_20260910` | Cópia privada do chat até o corte de 10/09 21:12 UTC; manifesto verificado. Não inclui automaticamente mensagens posteriores. |
| `RETOMADA_APOS_CHAT_20260910.md` | Guia vinculado ao manifesto do backup do chat; preservado sem alteração. `LEIA_PRIMEIRO.md` aponta também para esta conferência posterior. |
| `backups/operational-20260910-files-audit` | Novo backup consistente do Feature Store e das quotas, manifesto e cópia dos caches retirados. |
| Demais worktrees de correção e histórico | Preservados quando contêm estado diferente ou necessário; a cópia limpa redundante identificada abaixo foi retirada. |

`publicacao-chat-20260909` ainda contém o estado intermediário de uma integração antiga, com conflitos. Ele não é a versão final nem o local de retomada. A resolução efetiva está no [registro do PR #110](continuity_20260909/RESOLUCAO_PR110.md) e no Git integrado. Não apagar esse estado como se fosse uma cópia limpa redundante.

## Verificação e limpeza

O inventário inicial leu metadados de **186.120 arquivos**, totalizando **15.712.251.255 bytes**, sem erros de leitura de diretórios. Um link de runtime foi identificado e não seguido, evitando dupla contagem. A pasta de evidências da própria conferência foi excluída da varredura; os números descrevem esse instante, antes dos novos backups e desta publicação.

Os **114 Markdown então versionados** foram decodificados em UTF-8, e **424 destinos locais** foram conferidos. As referências históricas que dependem da pasta original estão explicitadas abaixo. A varredura verifica destinos de arquivos; não equivale a certificar a disponibilidade de todos os sites externos nem todas as âncoras de seção.

A conferência dos arquivos do manifesto original passou: **63.632 arquivos restaurados**, **2.728 arquivos de runtime restaurado** e **2.728 arquivos da cópia de runtime do pacote**, todos conferidos individualmente por SHA-256. Foram aceitas somente as quatro adaptações de ambiente já registradas em `restaurado-20260908/RESTAURACAO.json`. Os primeiros 50 mil resultados seriais foram preservados; a faixa restante foi concluída com quatro leituras concorrentes após lentidão na abertura dos arquivos. O ZIP original também passou nos **22.817 objetos internos**. Os resultados, scripts e limites ficam nas [evidências desta conferência](evidence/file_document_audit_20260910/).

Foram retirados os caches `.pytest_cache` da raiz e do checkout operacional e `.ruff_cache` desse checkout: **195.848 bytes**, preservados em um ZIP verificado de **51.981 bytes**. Ferramentas podem recriar esses caches posteriormente.

A cópia de publicação `publicacao-conferencia-20260910` também foi removida pelo comando `git worktree remove`, sem `--force`: seus **2.920 arquivos versionados** estavam limpos, sem arquivos extras/ignorados, e sua árvore era exatamente a já integrada em `94fc9e7`. Ela ocupava **625.000.474 bytes** no inventário. O commit `08dc4f7` e a branch `docs/reconcile-chat-20260910` continuam preservados. O [comprovante e comando de recuperação](evidence/file_document_audit_20260910/redundant_worktree.json) permitem recriar essa área. Caminhos dessa publicação em evidências anteriores são históricos.

Nenhum conteúdo exclusivo de código, ambiente congelado, banco, dado bruto, diário, relatório, credencial, pacote de migração ou cópia privada do chat foi removido. A presença de arquivos parecidos em outras worktrees e pacotes históricos não demonstra que sejam descartáveis.

## Backup atual e teste de recuperação

O novo backup foi capturado em **10/09/2026 21:36 UTC**. A ferramenta do projeto criou e verificou o Feature Store, e a restauração em `C:\Cripto\operacao\temporarios\restore-feature-store-20260910-files-audit` passou. Todas as tabelas, seus conteúdos e o esquema coincidem com o corte original. O banco de quotas também foi copiado pela API SQLite e conferido. Os dois bancos ativos permaneceram inalterados.

O Feature Store tem **3 previsões, 2 snapshots, 1 registro de inputs e 200 barras de mercado**. O segundo snapshot foi recuperado depois do backup histórico publicado; essa diferença é esperada. O procedimento atual está em [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

Esse backup cobre os dois bancos, não toda a pasta `C:\Cripto`. Código, evidências selecionadas e pacotes históricos estão no Git; dados operacionais completos, ambientes e configuração privada continuam nos locais do mapa. Os backups locais compartilham o mesmo disco e não comprovam recuperação após perda física dele. Não existe sincronização automática externa ativada.

## Correções dos guias

O README foi reduzido a uma entrada atual: removidas instruções repetidas, contagens antigas apresentadas como atuais, comandos de configuração incompatíveis com este PC e afirmações excessivas de imutabilidade/ausência de lookahead. A tabela H1–H9 permanece conforme o charter.

`CONTINUAR_AQUI.md`, o índice documental, a configuração local, o guia de notícias, o de quotas, o de backup e `C:\Cripto\LEIA_PRIMEIRO.md` agora apontam para os cortes corretos. Os limites de API são persistentes; limite zero não é uma solução para orçamento esgotado. Os comandos de backup usam `C:\Cripto\CRIPTO.cmd` e destinos novos dentro da raiz autorizada.

| Registro anterior preservado | Como interpretar agora |
|---|---|
| `CURRENT_RESEARCH_STATE_20260908.md`, `SESSION_HANDOFF_20260908.md`, `HANDOFF.md` e guias de migração antigos | Estados de suas datas. Use os índices atuais para caminhos, validação e retomada neste PC. |
| Runbook e `scheduling.json` do carry original | Registro do piloto cuja entrada passou. O protocolo manual v2 é separado; não existe obrigação nova de ativar agendamento. |
| `POLITICA_DE_MERGE.md` e `SECURITY_INCIDENT_SERPAPI.md` | Preservam incidentes e recomendações históricas. A administração de segurança da branch está excluída; o dono manteve as chaves atuais. A validação do código integrado continua sendo feita. |
| `PRONTIDAO_DADOS.md`, relatórios econômicos e ZIPs anteriores | Cortes de disponibilidade/resultados. A recuperação Aave e o snapshot v4 posteriores não são retroativamente inseridos nesses pacotes. |
| `NEXT_CHAT_PROMPT.md`, diretórios `evidence`, `session_archive`, `source_archive` e `continuity_20260909/local-root` | Mandato ou evidências preservadas. Corrigir apresentação não autoriza reescrever seus bytes e invalidar hashes. |

## Referências históricas que precisam da pasta original

Foram identificadas **103 referências** em duas cópias históricas, todas com destino presente quando resolvidas a partir da origem correta. O [mapa de referências](evidence/file_document_audit_20260910/historical_links.json) registra arquivo, linha, destino escrito, pasta original e existência verificada.

| Cópia no Git | Pasta original para resolver os caminhos |
|---|---|
| `docs/continuity_20260909/local-root/LEIA_PRIMEIRO.md` | `C:\Cripto` |
| `docs/evidence/remaining_dependencies_20260910/review_snapshot.md` | `C:\Cripto\operacao\relatorios\REVISAO_COMPLETA_20260909` |

São cópias com hashes preservados, não páginas independentes com todas as evidências hospedadas ao lado. No Git, use [CONFERENCIA_CHAT_20260910.md](CONFERENCIA_CHAT_20260910.md) e o [pacote público correspondente](evidence/remaining_dependencies_20260910/README.md); neste PC, use o relatório vivo na pasta original. A cópia integral de logs e evidências locais não foi publicada indiscriminadamente para consertar links de uma reprodução histórica.

## Dependências que continuam reais

A organização não produz dados ausentes: carry e LLM aguardam suas janelas a partir de 12/09; a comparação Aave com segunda fonte aguarda acesso e orçamento; originais H5, versões macro com disponibilidade comprovada e extratos pessoais continuam sem evidência suficiente. O snapshot v4 vence em **11/09/2026 02:00 UTC**. Consulte os protocolos e o [estado registrado no fechamento](CONFERENCIA_CHAT_20260910.md), sem tratar documentação ou software aprovado como lucro validado.
