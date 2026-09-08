from pathlib import Path

ROOT = Path('C:/Users/Superleo13/cripto-predictor')


def save(name, text):
    (ROOT/name).write_text(text, encoding='utf-8', newline='\n')


readme = (ROOT/'README.md').read_text(encoding='utf-8')
start = readme.index('## Próximos passos\n')
end = readme.index('## Histórico e decisões\n', start)
readme = readme[:start] + '''## Pendências vigentes

1. **Altcoins:** preservar o observador semanal `altcoin_reviewed_20260907`, seu
   diretório original e seu diário. A programação começa em 13/09/2026; a existência
   da configuração não garante uma execução futura. Consulte os caminhos e a
   situação registrada na [continuidade](docs/SESSION_HANDOFF_20260908.md).
2. **Carry BTC:** o código e o protocolo do observador de 84 dias estão prontos,
   mas o agendamento permanece pendente. O pré-teste não abriu posição.
   [Runbook](docs/evidence/carry_forward_20260908/RUNBOOK.md) e
   [registro do agendamento](docs/evidence/carry_forward_20260908/scheduling.json).
3. **Evidência econômica:** execução real, taxas da conta, tributação e margem
   efetiva continuam sem certificação. As coletas públicas e os cenários de custo
   não substituem essas evidências.
4. **Famílias antigas:** H6 e H9 estão encerradas por insuficiência de amostra;
   não retomar sua coleta como se estivessem ativas. H7 e H8 continuam registradas
   sem ativação, conforme o [charter](charters/scientific_state.json).
5. **Governança do Git e incidente antigo:** a consolidação esperou o CI completo;
   a configuração de branch protection não foi alterada. Os registros de
   [merge](docs/POLITICA_DE_MERGE.md) e do
   [incidente SerpAPI](docs/SECURITY_INCIDENT_SERPAPI.md) distinguem o que foi
   conferido do que depende de verificação externa.

As instruções de pesquisa posteriores autorizam linhas separadas com registro
prévio, sem reabrir silenciosamente famílias congeladas. Nenhuma validação de
software ou de hipótese autoriza ordens ou capital real.

''' + readme[end:]
start = readme.index('**Partida frio — leia primeiro:**')
end = readme.index('Os documentos datados são', start)
readme = readme[:start] + '''**Para retomar hoje:** [índice da documentação](docs/README.md) e
[continuidade de 08/09](docs/SESSION_HANDOFF_20260908.md).

O [roadmap de 21/08](docs/OVERVIEW_E_ROADMAP_2026-08-21.md) e o
[panorama daquela data](docs/PANORAMA_2026-08-21.md) documentam a etapa anterior;
suas pendências não substituem o estado vigente.

''' + readme[end:]
save('README.md', readme)

save('docs/NEXT_CHAT_PROMPT.md', r'''# Prompt de continuidade — atualizado em 08/09/2026

Retome o projeto a partir do estado abaixo e do meu pedido mais recente. Confira o repositório antes de agir; não repita pesquisas ou tarefas já encerradas apenas porque aparecem em documentos antigos.

## Projeto e leitura inicial

- Repositório principal: `C:\Users\Superleo13\cripto-predictor`, branch `main`.
- GitHub: [cripto-predictor](https://github.com/leonardosovienski/cripto-predictor).
- Leia [SESSION_HANDOFF_20260908.md](SESSION_HANDOFF_20260908.md), [CURRENT_RESEARCH_STATE_20260908.md](CURRENT_RESEARCH_STATE_20260908.md) e o [índice da documentação](README.md).
- A consolidação foi publicada em `dd8dbe26f10be23340d9248764da1e485633f7b8`. As branches anteriores foram integradas e removidas; só restou `main`. Commits documentais posteriores não representam novas avaliações econômicas. Confira o HEAD atual.
- A validação da consolidação teve 1.170 testes aprovados e quatro jobs do [CI](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34228309330) aprovados, incluindo container. Core 3.2.0 e Ops 4.1.0.

## Objetivo e limites da pesquisa

O objetivo é lucro líquido absoluto positivo, na mesma moeda e após os custos aplicáveis. Não exijo superar Selic, BTC ou outro benchmark. Quando houver pedido de pesquisa, você pode decidir moedas, corretoras públicas e abordagens sem perguntar novamente essas escolhas.

Trabalhe sozinho, sem coordenar agentes. Use dados públicos e recursos disponíveis. Não envie ordens, movimente dinheiro, use contas de negociação autenticadas ou contrate serviços pagos. Os 5.000 USDT são referência de simulação. O acesso ao GitHub para o push já autorizado não autoriza operações financeiras.

Registre especificação, parâmetros, critérios e orçamento de tentativas antes de avaliar variantes. Preserve resultados negativos, código congelado e períodos já consultados como pesquisa adaptativa. Não os apresente como validação independente nem reabra silenciosamente famílias encerradas. Não escolha custos favoráveis ou force entradas para fabricar lucro.

Use um diretório de trabalho separado dos observadores para mudanças de pesquisa. O pedido de consolidação autorizou a main e removeu as outras branches; não recrie branches antigas ou mude seus diretórios apenas para seguir um texto histórico. Preserve arquivos locais sem commit. Meus pedidos posteriores prevalecem sobre instruções históricas.

## Resultado que deve acompanhar a continuação

- Não há lucro real comprovado nem projeção validada de lucro futuro.
- AR1 BTC produziu +424,25 USDT base e +341,13 USDT adverso em 980 dias históricos. BR1 BTC produziu +230,17 e +110,07 no mesmo intervalo; são cenários separados de 5.000 USDT, não somáveis.
- No diagnóstico mais recente de 84 dias, o carry ficou em +10,56 USDT base, −6,97 adverso e −21,65 no estresse. O ganho recente não resistiu aos custos adversos.
- O seletor atual de altcoins não abriu operações nas 140 semanas históricas. Os números de +54,84 BTC e +34,62 ETH pertencem ao estudo anterior de um ano e não são comparação direta de melhoria.
- Taxas reais, preenchimentos, impostos, conversão e margem efetiva continuam desconhecidos. A reconstrução separada das contas foi feita pelo mesmo assistente; não é auditoria externa.

## Observadores e dados

O observador semanal de altcoins continua em `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-mentioned-by-the-user-cripto\work\cripto-v1.2`, com HEAD destacado em `fbf4c71`. Seus dados são diretórios irmãos: `altcoin-data`, `altcoin-payoff-results`, `altcoin-reviewed-data` e `altcoin-retro-data`. Preserve a `.venv`, os arquivos de aquisição e o diário.

A automação `observar-altcoins-semanalmente` foi recriada e vinculada à tarefa `01a07e75-d166-7430-859b-2af2c6ab0b0f`; sua configuração e seus arquivos foram preservados na consolidação. Horário: domingos às 21h de Brasília, primeira entrada prevista em 13/09/2026 e última saída em 06/12/2026. Verifique seu estado pelo recurso de automações antes de afirmar que está operante. Não recrie nem transfira automaticamente uma configuração existente. Avise somente em mudança relevante, falha, conclusão ou necessidade de informação; não retrodate janelas perdidas.

O observador de carry está preparado em `C:\Users\Superleo13\Documents\Codex\2026-09-07\files-pasted-by-the-user-quero\work\cripto-research`, com HEAD destacado em `2668865`, e dados irmãos em `carry-forward-data`. Seu agendamento não foi criado: o aplicativo recusou uma segunda automação na mesma tarefa. Leia [scheduling.json](evidence/carry_forward_20260908/scheduling.json) e o [runbook](evidence/carry_forward_20260908/RUNBOOK.md). Essa pendência não foi resolvida pelo push. Não crie tarefa separada ou cron alternativo sem a autorização correspondente.

## Recuperação e entrega

Os pacotes de código, dados, decisões e relatórios estão em [session_archive_20260908](session_archive_20260908/), com manifesto SHA256. Os arquivos da sessão anterior continuam em [session_archive_20260907](session_archive_20260907/) e na tag `cripto-session-20260907-final`. Consulte os guias dentro dos pacotes; extraia em diretórios novos. Não substitua diários operacionais por snapshots e não recalcule hashes para aceitar diferenças de bytes.

Explique em português simples o que mudou, o que foi verificado, os resultados nas condições declaradas e as pendências restantes. Não conclua que testes aprovados demonstram lucro. Não dependa da memória nem do histórico de outro chat para localizar o trabalho.
''')

save('docs/SESSION_HANDOFF_20260908.md', r'''# Continuidade da pesquisa — 08/09/2026

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
''')

save('docs/README.md', '''# Índice da documentação

## Estado vigente e continuidade

- [Estado da pesquisa](CURRENT_RESEARCH_STATE_20260908.md): conclusão econômica, correções e pendências atuais.
- [Continuidade de 08/09](SESSION_HANDOFF_20260908.md): Git, validação, observadores, dados e recuperação.
- [Prompt de continuidade](NEXT_CHAT_PROMPT.md): contexto atualizado para retomar o trabalho.
- [Auditoria da consolidação](evidence/git_consolidation_20260908/README.md): integração das branches e preservação.

## Evidências e reprodução

- [Coleta imediata e auditoria](evidence/immediate_audit_20260908/RESULTADOS.md).
- [Pacotes da pesquisa de 08/09](session_archive_20260908/deliverables/) e [manifesto](session_archive_20260908/DELIVERABLES_SHA256.json).
- [Sessão histórica de 07/09](SESSION_HANDOFF_20260907.md) e [arquivos preservados](session_archive_20260907/).
- [Runbook do carry](evidence/carry_forward_20260908/RUNBOOK.md) e [agendamento pendente](evidence/carry_forward_20260908/scheduling.json).

Os diretórios `evidence/` e `session_archive_*/` preservam decisões e entregas das respectivas etapas. Seus resultados e instruções de execução devem ser interpretados conforme a data e a versão. Não altere arquivos congelados para corrigir uma apresentação histórica; use os documentos de continuidade para a situação atual.

## Governança e referências anteriores

- [Histórico das hipóteses](HYPOTHESES.md) e [estado científico canônico](../charters/scientific_state.json).
- [Índice do congelamento](../CR_FREEZE_INDEX.md) e [manifesto das famílias anteriores](../CR_RESEARCH_FREEZE.md).
- [Política de merge](POLITICA_DE_MERGE.md), [backup e restauração](BACKUP_RESTORE.md) e [incidente SerpAPI](SECURITY_INCIDENT_SERPAPI.md).
- [Handoff com notas históricas](../HANDOFF.md), [roadmap de agosto](OVERVIEW_E_ROADMAP_2026-08-21.md) e [panorama de agosto](PANORAMA_2026-08-21.md).

H6 e H9 permanecem encerradas por insuficiência de amostra. Os runbooks e prompts antigos de acompanhamento da H6 documentam sua operação passada; não autorizam reiniciar essa coleta. As novas pesquisas têm protocolos separados.
''')
