# Continuidade da pesquisa — 08/09/2026

**Atualização de localização em 09/09/2026:** o checkout atual é `C:\Cripto\pesquisa-20260909`; os dados e snapshots estão em `C:\Cripto\restaurado-20260908`. Toda nova execução, configuração, cache, saída e entrega deve ficar em `C:\Cripto`, conforme [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md). As referências ao computador antigo e ao Git abaixo são registros da consolidação de 08/09, não caminhos de execução neste PC.

A consolidação foi concluída e publicada no commit `dd8dbe26f10be23340d9248764da1e485633f7b8`, na [main do GitHub](https://github.com/leonardosovienski/cripto-predictor/tree/main). Todas as branches anteriores foram integradas e removidas; restou somente `main`, local e remota. A revisão documental posterior não altera os resultados científicos.

O checkout principal é `C:\Users\Superleo13\cripto-predictor`. Confira o HEAD atual antes de trabalhar. O arquivo sem commit `fred_test.csv` pertence ao usuário e foi preservado.

Leia o [estado vigente](CURRENT_RESEARCH_STATE_20260908.md), os [resultados da coleta imediata](evidence/immediate_audit_20260908/RESULTADOS.md) e o [prompt de continuidade](NEXT_CHAT_PROMPT.md). Não há lucro real comprovado; o carry histórico recente perdeu sob custos adversos.

## Validação concluída

A suíte completa passou em **1.170 testes**. Os quatro jobs do [CI da consolidação](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34228309330) passaram: `quality`, `all-extras`, `python-314-experimental` e `container`. Core 3.2.0 e Ops 4.1.0 permanecem fixados. A [validação local](evidence/git_consolidation_20260908/local_validation.json) registra os comandos e resultados.

O pacote fonte foi corrigido para incluir somente as fontes necessárias ao build. `dist/` é gerado por `uv build` e não é versionado. Os pacotes da pesquisa são preservados separadamente abaixo.

## Recuperação das entregas

Os 30 arquivos de entrega estão em [deliverables](session_archive_20260908/deliverables/), com hashes no [manifesto SHA256](session_archive_20260908/DELIVERABLES_SHA256.json). Incluem código congelado e dados públicos necessários à reprodução. Use os guias dos pacotes e extraia em diretórios novos:

| Etapa | Código e dados | Guia ou resultado |
|---|---|---|
| Pesquisa absoluta | [CRIPTO_CODIGO_DADOS_REPRODUCAO.zip](session_archive_20260908/deliverables/CRIPTO_CODIGO_DADOS_REPRODUCAO.zip) | [COMO_REPRODUZIR.md](session_archive_20260908/deliverables/COMO_REPRODUZIR.md) |
| Futuros com vencimento | [CRIPTO_BASIS_IMPLEMENTACAO.zip](session_archive_20260908/deliverables/CRIPTO_BASIS_IMPLEMENTACAO.zip) | [CRIPTO_BASIS_REPRODUZIR.md](session_archive_20260908/deliverables/CRIPTO_BASIS_REPRODUZIR.md) |
| Revisão das conclusões | [CRIPTO_REVISAO_DO_CHAT_CORRECAO.zip](session_archive_20260908/deliverables/CRIPTO_REVISAO_DO_CHAT_CORRECAO.zip) | [CRIPTO_REVISAO_DO_CHAT.md](session_archive_20260908/deliverables/CRIPTO_REVISAO_DO_CHAT.md) |
| Planejador v3 e observador | [CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip](session_archive_20260908/deliverables/CRIPTO_CORRECOES_CODIGO_E_EVIDENCIAS.zip) | [CRIPTO_CORRECOES.md](session_archive_20260908/deliverables/CRIPTO_CORRECOES.md) |
| Coleta imediata e auditoria Decimal | [CRIPTO_AUDITORIA_AGORA.zip](session_archive_20260908/deliverables/CRIPTO_AUDITORIA_AGORA.zip) | [CRIPTO_AUDITORIA_AGORA.md](session_archive_20260908/deliverables/CRIPTO_AUDITORIA_AGORA.md) |

Os pacotes e relatórios originais continuam imutáveis. Neles, afirmações como “sem push”, nomes de branches e contagens antigas de testes descrevem a data de emissão. Leia as retificações mais recentes antes de interpretar os números. `.gitattributes` preserva os bytes congelados; não recalcule hashes para contornar falha de integridade. Restaurar um pacote não transfere automaticamente uma automação nem seus caminhos absolutos.

## Observadores preservados

As pastas operacionais continuam separadas do checkout principal:

- **Altcoins:** `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2`, com HEAD destacado em `fbf4c71`. Dados e diário em diretórios irmãos, especialmente `altcoin-reviewed-data`. A automação semanal conserva seus caminhos e está vinculada à tarefa `01a07e75-d166-7430-859b-2af2c6ab0b0f`, conforme a última verificação; isso não garante execução futura do agendador.
- **Carry BTC:** `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-pasted-by-the-user-quero\work\cripto-research`, com HEAD destacado em `2668865`; dados irmãos em `carry-forward-data`. O agendamento continua pendente conforme [scheduling.json](evidence/carry_forward_20260908/scheduling.json). O push não criou uma automação.

O runtime e os dados irmãos não são copiados por um checkout Git. Não sobrescreva essas pastas com a main nem substitua seus diários por snapshots de entrega. A sessão anterior permanece recuperável pela tag `cripto-session-20260907-final` e pelo [handoff histórico](SESSION_HANDOFF_20260907.md).

## Auditoria Git e backups

A [auditoria da consolidação](evidence/git_consolidation_20260908/README.md) explica a resolução das divergências. [reconciliation.json](evidence/git_consolidation_20260908/reconciliation.json) registra os 21 tips anteriores, sua ancestralidade e os hashes dos backups. Os commits originais permanecem alcançáveis pela main.

Os backups locais `GIT_BACKUP_TODAS_BRANCHES_20260908.bundle` e `GIT_ALTERACOES_LOCAIS_PRESERVADAS_20260908.zip` estão em `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-pasted-by-the-user-quero\outputs`. Nesse diretório também estão `GIT_MAIN_CONCLUIDO_20260908.md` e `.json`, com a verificação final. Alterações antigas sem commit foram preservadas no lugar e em backup; não equivalem a uma branch pendente de merge.
