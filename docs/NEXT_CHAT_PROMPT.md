# Prompt de continuidade — atualizado em 09/09/2026

Retome o projeto a partir do estado abaixo e do meu pedido mais recente. Confira o repositório antes de agir; não repita pesquisas ou tarefas já encerradas apenas porque aparecem em documentos antigos.

**Regra de armazenamento deste PC:** trabalhe somente em `C:\Cripto` e suas subpastas. Leia primeiro [CONFIGURACAO_LOCAL.md](CONFIGURACAO_LOCAL.md). Código atual em `C:\Cripto\pesquisa-20260909`, arquivos restaurados em `C:\Cripto\restaurado-20260908`, configuração privada em `C:\Cripto\configuracao\pipeline.env` e novas entregas em `C:\Cripto\operacao\relatorios`. Use `C:\Cripto\CRIPTO.cmd` para aplicar também os caminhos de cache, estado e temporários. Não crie novos arquivos do projeto no AppData, Documents, Desktop ou nas pastas de tarefas do Codex.

Atualização de pesquisa de 09/09/2026: leia primeiro o [registro canônico da rodada econômica](evidence/economic_round_20260909/RESULTADOS.md), com protocolo, decisões, fontes, contas e condições de retomada. A rodada terminou com H1 bloqueada por acesso histórico e H2 rejeitada como correção suficiente das perdas adversas modeladas; não existe autorização de capital nem nova rentabilidade final demonstrada. O trabalho Windows desta rodada está em `C:\Cripto\pesquisa-20260909`; os caminhos abaixo são históricos.

## Projeto e leitura inicial

- Repositório de trabalho: `C:\Cripto\pesquisa-20260909`; confira a branch atual e `origin/main`. `C:\Cripto\restaurado-20260908\projeto` é o snapshot preservado da migração.
- GitHub: [cripto-predictor](https://github.com/leonardosovienski/cripto-predictor).
- Leia [SESSION_HANDOFF_20260908.md](SESSION_HANDOFF_20260908.md), [CURRENT_RESEARCH_STATE_20260908.md](CURRENT_RESEARCH_STATE_20260908.md) e o [índice da documentação](README.md).
- A consolidação foi publicada em `dd8dbe26f10be23340d9248764da1e485633f7b8`. As branches anteriores foram integradas e removidas; só restou `main` naquele momento. Commits documentais posteriores não representam novas avaliações econômicas. Confira o HEAD atual.
- A validação da consolidação teve 1.170 testes aprovados e quatro jobs do [CI](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34228309330) aprovados, incluindo container. Core 3.2.0 e Ops 4.1.0.

## Entrega posterior: pesquisa de lucro multiestratégia

O dono ampliou explicitamente a autonomia de alteração de código para quaisquer criptoativos e estratégias, com foco em lucro líquido absoluto. A entrega [PR #105](https://github.com/leonardosovienski/cripto-predictor/pull/105), iniciada a partir de `522de73`, acrescenta `GarimpoInvestimentos.profit_research`. Consulte [PROFIT_RESEARCH.md](PROFIT_RESEARCH.md) e [scope.json](evidence/profit_research_20260908/scope.json) antes de continuar. Confira no PR o estado da integração e do CI, sem inferir isso deste texto.

Essa entrada compara contas econômicas, preserva custos desconhecidos, implementa descoberta pública de rendimentos sem excluir stablecoins/wrapped e diagnostica o giro de ajustar uma posição em vez de fechar/reabrir. É ferramenta de pesquisa, não nova estratégia validada: os testes novos são sintéticos, não houve replay histórico AR2, consulta real de yields ou demonstração de lucro adicional nessa entrega. A reconciliação dos valores arredondados publicados mantém teto parcial de −6,97 USDT antes dos custos desconhecidos. Nenhuma permissão de capital foi ativada.

O trabalho usa a branch nova `research/profit-opportunity-screening-20260908` para validação antes da integração; não recria branches históricas ou muda os diretórios dos observadores. Os congelamentos, charters, resultados negativos, diários, dados locais e agendamentos anteriores permanecem preservados. Novos estudos empíricos exigem especificação, orçamento de tentativas e critérios prévios; famílias fechadas continuam sujeitas ao dossiê de reabertura.

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

O observador semanal de altcoins foi restaurado em `C:\Cripto\restaurado-20260908\sessoes\20260907-altcoins\work\cripto-v1.2`, a partir da versão congelada `fbf4c71`. Seus dados são diretórios irmãos: `altcoin-data`, `altcoin-payoff-results`, `altcoin-reviewed-data` e `altcoin-retro-data`. Preserve a `.venv`, os arquivos de aquisição e o diário.

A configuração histórica da automação `observar-altcoins-semanalmente`, vinculada à tarefa antiga `01a07e75-d166-7430-859b-2af2c6ab0b0f`, foi preservada no pacote. Não foi ativada por esta migração/configuração local. O horário histórico era domingo às 21h de Brasília, com entradas previstas de 13/09 a 06/12/2026. Não recrie, transfira ou ative agendamentos por interpretar essa configuração como autorização atual. Não retrodate janelas perdidas.

O observador de carry foi restaurado em `C:\Cripto\restaurado-20260908\sessoes\20260907-pesquisa\work\cripto-research`, a partir da versão congelada `2668865`, com dados irmãos em `carry-forward-data`. Seu agendamento continua desativado neste PC. [scheduling.json](evidence/carry_forward_20260908/scheduling.json) e o [runbook](evidence/carry_forward_20260908/RUNBOOK.md) preservam o contexto histórico; seus caminhos antigos não são destinos atuais.

## Recuperação e entrega

Os pacotes de código, dados, decisões e relatórios estão em [session_archive_20260908](session_archive_20260908/), com manifesto SHA256. Os arquivos da sessão anterior continuam em [session_archive_20260907](session_archive_20260907/) e na tag `cripto-session-20260907-final`. Consulte os guias dentro dos pacotes; extraia em diretórios novos. Não substitua diários operacionais por snapshots e não recalcule hashes para aceitar diferenças de bytes.

Explique em português simples o que mudou, o que foi verificado, os resultados nas condições declaradas e as pendências restantes. Não conclua que testes aprovados demonstram lucro. Não dependa da memória nem do histórico de outro chat para localizar o trabalho.
