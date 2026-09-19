# Índice da documentação

> **Comece pela [continuidade do projeto](../CONTINUAR_AQUI.md).** Ela é o ponto de entrada para o último corte de engenharia conferido e para a ordem de leitura. Os relatórios datados abaixo conservam o contexto de suas respectivas execuções.
>
> **Leitura obrigatória antes das fontes científicas históricas:** [errata de evidências de 15/09](ERRATA_AUDITORIA_20260915.md), com orientação de reutilização destacada em 17/09. H6: n observado=84, mas poder tabelado para n de referência=60. A errata também trata BR2, segunda fonte Aave, atestados expirados e contagens de trials. Os exportadores não aplicam essas correções automaticamente aos textos congelados.

## Uso e engenharia

- [README principal](../README.md): capacidades, dependências selecionadas, instalação e limites.
- [Configuração do Windows em C:\Cripto](CONFIGURACAO_LOCAL.md): mapa do perfil local; não comprova o estado ao vivo da instalação.
- [Integração instalada](FINAL_INTEGRATION_AUDIT.md): combinação do script atual e reprodução separada da auditoria de 12/09.
- [Ferramentas de pesquisa offline](../GarimpoInvestimentos/research/README.md): universo, fatores, splits, simulação sintética e RunStore.
- [Exportador Snapshot](../packages/research-export/README.md) e [ResearchBundleV1](RESEARCH_BUNDLE_V1.md): instalação independente, contratos e admissão de fontes.
- [Guardas de API](API_GUARDS.md) e [backup/restauração](BACKUP_RESTORE.md): contratos operacionais; não ativam tarefas por sua existência.

A fonte de código conferida em 17/09 é `e5997104f9c72f31764acdbdd4d26ec176791b68`, após o PR #120. Os links e resultados das suas execuções estão na continuidade. A [publicação de 12/09](../PUBLICATION_STATUS_20260912.md) não descreve o HEAD posterior.

## Auditorias e continuidade datadas

- [Recuperação econômica Nível 2/3 de 19/09](continuity_20260919/README.md): relatório reuse/verify/gap, baseline congelado, resumo, manifesto e distinção GitHub/local para retomada sem o chat.
- [Consolidação em main de 15/09](CONSOLIDACAO_MAIN_20260915.md): integração e remoção das branches incorporadas naquele corte, preservando arquivos locais.
- [Auditoria técnica e correções de 15/09](AUDITORIA_TECNICA_20260915.md): testes, tipagem, publicação e limites da verificação; não transferir contagens para outros commits.
- [Fechamento de 11/09](continuity_20260911/README.md): código research, estudos preservados, evidências de teste e mapa local para continuar sem o chat.
- [Conferência de arquivos de 10/09](CONFERENCIA_ARQUIVOS_20260910.md) e [conferência do chat de 10/09](CONFERENCIA_CHAT_20260910.md): preservação, snapshot recuperado, estado dos itens após #116 e calendários manuais.
- [Auditoria ampliada de 10/09](AUDITORIA_AMPLIADA_20260910.md): correções de fontes, temporalidade, execução simulada, persistência e estatística.
- [Revisão geral de 09/09](REVISAO_COMPLETA_20260909.md): acesso ao registro local daquela revisão e suas dependências.
- [Fechamento da preparação de 09/09](FECHAMENTO_PENDENCIAS_20260909.md): correções, execução real e limites.

Os calendários manuais que começam em 12/09 não são instrução para executar janelas perdidas retroativamente. A presença de um protocolo ou runbook não prova que a coleta ocorreu. Consulte recibos e a continuidade antes de qualquer execução.

## Pesquisa, dados e dependências

- [Aave: validação histórica, custos e execução](AAVE_VALIDACAO_20260910.md): resultados positivos condicionais, sem comprovação de lucro pessoal ou futuro. A tentativa posterior de segunda fonte está reconciliada na [errata](ERRATA_AUDITORIA_20260915.md).
- [Dependências executadas em 10/09](manual_dependencies_20260910/EXECUCAO.md): histórico Aave, custos e executor/avaliador LLM congelado. [Retomada anterior](manual_dependencies_20260910/RETOMADA.md): calendário dos gaps, volume intradiário e carry separado.
- [Prontidão de dados](PRONTIDAO_DADOS.md): bases e lacunas verificadas no seu corte, limites de API e critérios de preparação.
- [Rodada econômica de 09/09](evidence/economic_round_20260909/RESULTADOS.md): resultados, limitações e condições de retomada.
- [Estado da pesquisa em 08/09](CURRENT_RESEARCH_STATE_20260908.md): registro histórico; suas pendências não substituem adendos posteriores. Leia a correção de BR2 na errata antes de reutilizá-lo.
- [Continuidade de 08/09](SESSION_HANDOFF_20260908.md): Git, validação, observadores, dados e recuperação.
- [Prompt original de continuidade](NEXT_CHAT_PROMPT.md): mandato preservado, não ordem para repetir automaticamente trabalho concluído.

## Evidências e recuperação

- [Dados e fontes: complemento de 10/09](continuity_20260910/README.md), [manifesto](continuity_20260910/MANIFEST.json) e [teste de recuperação](continuity_20260910/VALIDACAO.json): cinco ZIPs com 2.685 arquivos no corte registrado.
- [Pacotes anteriores de 09/09](continuity_20260909/README.md) e [manifesto](continuity_20260909/MANIFEST.json).
- [Coleta imediata e auditoria de 08/09](evidence/immediate_audit_20260908/RESULTADOS.md).
- [Pacotes da pesquisa de 08/09](session_archive_20260908/deliverables/) e [manifesto](session_archive_20260908/DELIVERABLES_SHA256.json).
- [Sessão histórica de 07/09](SESSION_HANDOFF_20260907.md) e [arquivos preservados](session_archive_20260907/).
- [Runbook histórico do carry](evidence/carry_forward_20260908/RUNBOOK.md) e [registro do agendamento daquela etapa](evidence/carry_forward_20260908/scheduling.json).
- [Migração Windows](MIGRACAO_WINDOWS.md) e [mapa da pasta local](LOCAL_FOLDER_AUDIT.md).
- [Auditoria da consolidação de 08/09](evidence/git_consolidation_20260908/README.md).

Os diretórios `evidence/`, `session_archive_*/`, `source_archive_*/`, os estudos OSS e os pacotes de continuidade preservam decisões e entregas datadas. Não reescreva seus bytes para atualizar caminhos ou apresentações históricas. Git não contém a configuração privada, todos os bancos, ambientes ou recibos locais. Recuperação deve usar destino novo, sem sobrescrever o acervo.

## Governança e fontes científicas preservadas

Leia primeiro a [errata](ERRATA_AUDITORIA_20260915.md); depois consulte [HYPOTHESES](HYPOTHESES.md), [EVIDENCE_REGISTRY](EVIDENCE_REGISTRY.md) e o [charter](../charters/scientific_state.json). As hipóteses seguem seus estados literais; ressalvas narrativas, inclusive as notes do charter sobre poder da H6, não devem ser reutilizadas sem a correção.

- [Índice do congelamento](../CR_FREEZE_INDEX.md) e [manifesto das famílias anteriores](../CR_RESEARCH_FREEZE.md).
- [Política de merge e histórico de incidentes](POLITICA_DE_MERGE.md) e [incidente SerpAPI](SECURITY_INCIDENT_SERPAPI.md). Esta revisão não administra segurança da branch nem credenciais; ações históricas não são novas autorizações.
- [Handoff de entrada](../HANDOFF.md) e [handoff integral histórico](../HANDOFF_HISTORICO_ATE_20260917.md).
- [Roadmap de agosto](OVERVIEW_E_ROADMAP_2026-08-21.md) e [panorama de agosto](PANORAMA_2026-08-21.md).

H6 e H9 permanecem encerradas por insuficiência de amostra. Runbooks e prompts antigos da H6 não autorizam reiniciar sua coleta. As novas pesquisas exigem protocolos próprios. Esta correção de navegação não recertifica semanticamente todos os documentos históricos.
