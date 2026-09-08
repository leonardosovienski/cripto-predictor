# Continuidade da pesquisa — 08/09/2026

O destino desta consolidação é a branch `main` de https://github.com/leonardosovienski/cripto-predictor. O pedido atual autoriza push e remoção das outras branches. O histórico dos commits anteriores permanece incorporado; suas instruções de trabalhar em uma branch agora removida são históricas.

Leia `CURRENT_RESEARCH_STATE_20260908.md` e `evidence/immediate_audit_20260908/RESULTADOS.md` para a conclusão vigente. Não há lucro real comprovado. O carry histórico recente perdeu sob custos adversos; testes de software não certificam rentabilidade.

## Recuperação das entregas

Os 30 arquivos de entrega estão em `session_archive_20260908/deliverables`, com hashes em `session_archive_20260908/DELIVERABLES_SHA256.json`. Incluem código congelado e dados públicos necessários à reprodução. Use os guias dentro dos próprios pacotes e extraia em diretórios novos, nunca sobre observadores existentes:

- `CRIPTO_CODIGO_DADOS_REPRODUCAO.zip` e `COMO_REPRODUZIR.md`: pesquisa absoluta original e reprodução offline.
- `CRIPTO_BASIS_IMPLEMENTACAO.zip` e `CRIPTO_BASIS_REPRODUZIR.md`: pesquisa de futuros com vencimento e diagnóstico de execução.
- `CRIPTO_REVISAO_DO_CHAT_CORRECAO.zip` e os relatórios de revisão: retificações posteriores.
- `CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip`: planejador v3, auditor separado e observador público de carry.
- `CRIPTO_AUDITORIA_AGORA.zip`: coleta imediata, respostas brutas, diagnóstico e reconstrução Decimal.

Os pacotes anteriores continuam imutáveis. Leia as retificações mais recentes antes de interpretar números antigos. `.gitattributes` preserva os bytes de código congelado em novos checkouts; não recalcule hashes para contornar falha de integridade.

## Observadores

O observador de altcoins permanece no diretório original `files-mentioned-by-the-user-cripto/work/cripto-v1.2`, agora com HEAD destacado no mesmo commit fbf4c71. O runtime e os dados irmãos não são copiados por um checkout Git. A automação semanal conserva os caminhos existentes; mudar a branch não muda sua configuração.

O código operacional de carry permanece em `files-pasted-by-the-user-quero/work/cripto-research`, no commit 2668865, também com HEAD destacado. A criação do seu agendamento permanece pendente conforme `evidence/carry_forward_20260908/scheduling.json`; consolidar branches não cria uma nova automação. Nenhum diário foi substituído por um snapshot de entrega.

A sessão de 07/09 continua recuperável pela tag `cripto-session-20260907-final` e pelo arquivo `SESSION_HANDOFF_20260907.md`. A tag histórica não é uma branch e foi preservada.

## Auditoria Git

`evidence/git_consolidation_20260908/README.md` explica a resolução de cada divergência; `reconciliation.json` registra todos os tips originais, ancestralidade e hashes dos backups. Alterações locais sem commit em worktrees antigos continuam preservadas e não equivalem a uma branch pendente de merge.
