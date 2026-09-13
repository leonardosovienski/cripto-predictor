# Pasta local e continuidade documental

Conferência em 12/09/2026, depois da consolidação em main. A raiz autorizada é `C:\Cripto`.

| Local | Papel e tratamento |
|---|---|
| `pesquisa-20260909` | Checkout principal em main. Usar para novo trabalho. |
| `CRIPTO.cmd` | Launcher que aponta ao checkout principal. |
| `operacao` | Dados, saídas, cache, logs, estado, temporários e relatórios separados. |
| `configuracao` | Configuração privada; não publicar seus valores. |
| `ferramentas`, `runtime` | Ferramentas e runtimes existentes; preservar dependências dos executores. |
| `restaurado-20260908` | Pacote original, ambientes, bancos e diários preservados. |
| `auditoria-ampliada-20260910` | Executor histórico congelado; não atualizar com main. |
| `correcao-pr110-20260910`, `fechamento-revisao-20260910`, `revisao-arquivos-20260910`, `publicacao-chat-20260909`, `cain-l0-exporter-20260911` | Checkouts históricos; HEAD destacado e conteúdo preservado. O conflito antigo de publicacao-chat continua no arquivo histórico. |
| `backups`, `captura-final-20260910`, `recuperacao-final-verificada-20260910` | Preservação e ensaios de recuperação anteriores. |
| `bundle-v1-completion-e2e`, `bundle-v1-e2e`, `bundle-v1-enriched-e2e`, `bundle-v1-final-e2e`, `cain-l0` | Ambientes e artefatos de integração anteriores; não são o checkout principal. |
| `clone-incompleto-open-source-20260911` | Clone interrompido preservado; não usar como fonte canônica. |

Não houve movimentação ou exclusão de pastas: caminhos fixos de executores, backups e evidências precisam continuar recuperáveis. Arquivos originais da migração e documentos datados conservam seu contexto. A organização consiste em identificar o destino canônico e o acervo, não em apagar duplicatas aparentes.

Leia [publicação e ordem de leitura](../PUBLICATION_STATUS_20260912.md) antes dos handoffs históricos. A conferência documental está em `C:\Cripto\operacao\relatorios\conferencia-pastas-md-20260912`, com inventário, cópias anteriores dos documentos editados e recibos. Os números de testes históricos continuam associados aos seus SHAs.
