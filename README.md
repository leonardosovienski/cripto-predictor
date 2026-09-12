
<!-- DOC-SYNC-20260912 -->
> **Estado de publicação em 12/09/2026:** leia [a continuidade atual](PUBLICATION_STATUS_20260912.md). Branch `validation/retest-six-20260911`. O código deste projeto foi publicado na branch indicada. O candidato CAIN Supply permanece sem aprovação de estabilização. Afirmações anteriores de “sem push” descrevem a etapa histórica anterior à autorização.
<!-- /DOC-SYNC-20260912 -->

> Continuidade atual: [fechamento de 11/09/2026](docs/continuity_20260911/README.md).

## Entrega arquitetural publicada — 11/09/2026

Versão **1.1.0** publicada: [release e artefatos](https://github.com/leonardosovienski/cripto-predictor/releases/tag/v1.1.0). [CI de engenharia aprovada](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34630038441) para a fonte `6ea0d2ccdcfc6a3858083acb6ded5cb39e178586`. Consulte [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md) para comportamento, migração e limites. Este registro atualiza a entrega de software; estados científicos e registros datados abaixo conservam sua autoridade e contexto histórico.

# cripto-predictor (GarimpoInvestimentos + DPL)

Sistema de pesquisa em criptoativos: ingestão e procedência de dados, análises com LLM, diagnósticos quantitativos e avaliação estatística. Nenhuma linha tem lucro pessoal ou futuro comprovado; os resultados históricos positivos de Aave são condicionais aos cenários de custo. A V3 emite diagnóstico `UNVALIDATED`.

## Comece aqui

- [Ferramentas de pesquisa offline](GarimpoInvestimentos/research/README.md): filtros de universo, fatores, splits temporais, ordens sintéticas e experimentos reproduzíveis. Execute `cripto-predictor research --help`; não ativa trading nem altera trials.
- [Continuidade atual](CONTINUAR_AQUI.md): ordem de leitura e limites de execução.
- [Conferência de arquivos e documentação de 10/09/2026](docs/CONFERENCIA_ARQUIVOS_20260910.md): conteúdo preservado, limpeza, backups e referências históricas.
- [Dados, fontes e resultados recentes preservados](docs/continuity_20260910/README.md): 2.685 arquivos em cinco pacotes verificáveis, incluindo o diagnóstico atual.
- [Configuração deste PC](docs/CONFIGURACAO_LOCAL.md): caminhos em `C:\Cripto`, ambiente e configuração privada.
- [Conferência do chat de 10/09](docs/CONFERENCIA_CHAT_20260910.md) e [auditoria ampliada](docs/AUDITORIA_AMPLIADA_20260910.md): correções, evidências e dependências.
- [Índice da documentação](docs/README.md): pesquisa, dados, recuperação e histórico.

Referência técnica anterior a esta conferência: `main` em `94fc9e7` (PR #117), validado no Windows com **1.505 testes aprovados e um skip de symlink**, e quatro jobs de CI aprovados no [commit integrado](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34525972190). Essa contagem é datada; confira o SHA e os checks do commit que pretende usar.

## Execução neste Windows

Código operacional: `C:\Cripto\pesquisa-20260909`. Use o atalho que aplica os caminhos e o ambiente do projeto:

```powershell
C:\Cripto\CRIPTO.cmd status
C:\Cripto\CRIPTO.cmd pipeline --help
C:\Cripto\CRIPTO.cmd uv --version
```

O `status` verifica a configuração sem consultar APIs. Credenciais ficam somente em `C:\Cripto\configuracao\pipeline.env`, conforme o [mapa local](docs/CONFIGURACAO_LOCAL.md). O [exemplo público](GarimpoInvestimentos/.env.example) documenta os nomes das variáveis; ele não substitui o perfil deste PC.

O ambiente aceita Python 3.13 ou 3.14. As dependências e suas fontes estão fixadas em [pyproject.toml](pyproject.toml) e [uv.lock](uv.lock); Core 3.2.0 e Ops 4.1.0 são distribuições externas, sem cópias vendorizadas. Para manutenção, a sincronização completa é `C:\Cripto\CRIPTO.cmd uv sync --frozen --all-extras`. Os extras `llm`, `v3`, `excel`, `science` e `test` são necessários para exercitar toda a suíte.

As verificações locais usam ambiente sintético e diretórios isolados, sem carregar as chaves privadas. O executor de validação e os resultados por commit ficam no [registro da revisão](docs/REVISAO_COMPLETA_20260909.md). Não apresente testes executados com extras faltantes como validação completa. No Windows, a falta de privilégio para symlink pode causar o único skip documentado.

Coletas conectadas exigem janela, fontes e orçamento disponíveis. Os limites atuais são 28 unidades de ingestão, 8 tentativas de notícias por provedor e 6 chamadas lógicas de LLM por provedor, por dia UTC. Consulte [guardas de API](docs/API_GUARDS.md) e os protocolos antes de executar; nenhum agendamento está ativado por esta configuração.

## Dados e componentes

| Componente | Contrato e limite |
|---|---|
| DPL | Ingestão com contratos de instrumento, moeda, temporalidade e procedência; cobertura depende da fonte e da versão histórica disponível. |
| Feature Store | Banco oficial em `C:\Cripto\operacao\saidas\feature_store.db`; snapshots e inputs versionados preservam o contexto das novas previsões. Atualizações de dados brutos e de resultados não equivalem a um banco inteiro imutável. |
| LLM | Mercado armazenado, notícias e juiz identificado; carimbos de recebimento e conteúdo preservado não recuperam fontes históricas perdidas. |
| Backtest | Retornos medidos após a previsão; bootstrap e DSR sujeitos aos contratos de amostra, unidades e comparabilidade das tentativas. |
| V3 | HMM, funding/OI e walk-forward; causalidade da filtragem depende do ajuste e dos dados de cada avaliação. Custos não têm calibração de execução pessoal comprovada. |
| Operação | Ferramentas de lock, heartbeat e diagnóstico disponíveis; executores manuais obedecem aos protocolos próprios. |

Em 10/09/2026, o banco operacional contém três previsões, dois snapshots de mercado e um registro de inputs. O snapshot v4 usa 200 barras BTCUSDT fechadas, recuperadas de um recibo já existente, e vence em **11/09/2026 às 02:00 UTC**. Ele não ficará atualizado pela existência deste README. Use [backup e restauração](docs/BACKUP_RESTORE.md) para preservar o estado real antes de manutenção.

## Estado científico

As famílias antigas seguem o [charter](charters/scientific_state.json), o [índice de congelamento](CR_FREEZE_INDEX.md) e o [manifesto científico](CR_RESEARCH_FREEZE.md). Novas linhas possuem registros separados; a infraestrutura não reabre hipóteses encerradas.

| # | Hipótese | Trial (`trials.json`) | Status |
|---|---|---|---|
| H1 | Funding/OI + regime HMM prevê retorno 24h | `v3-hmm-funding-oi-fr90` | **CLOSED_NO_GO** — bruto +0,44bps → líquido −0,09bps; PSR 0,445 |
| H2 | Janela curta de funding (fr21) | `v3-hmm-funding-oi-fr21` | **CLOSED_NO_GO** — PSR 0,215 |
| H3 | Horizonte 48h amortiza a fricção | `v3-hmm-funding-oi-fr90-h48` | **CLOSED_NO_GO** — edge bruto vira negativo; MaxDD 50,3% |
| H4 | Score do LLM prevê retorno D+7 | `v2-dpl-gemini-h7` | **CLOSED_INSUFFICIENT_SAMPLE** — coleta encerrada com n=5 |
| H5 | Idem, partição multi-juiz | `v2-dpl-multi-h7` | **CLOSED_NO_GO** — Spearman −0,166 [−0,266; −0,057], n=440 (IC não cruza zero, mas na direção oposta) |
| H6 | Leitura **invertida** do score do LLM | `h6-sinal-invertido-d7` | **CLOSED_INSUFFICIENT_SAMPLE** — rho −0,057 [−0,231; +0,129] com n=84: cruza zero, e o sinal voltou a ser negativo, não positivo como a inversão previa |
| H7 | Calendário macro (FOMC/CPI/PPI) + DXY | `h7-macro-dxy-hmm-v1` | **REGISTERED_NOT_ACTIVATED** — infra pronta; backtest TENTADO em 2026-09-04 e abortado por bug de infraestrutura (corrigido no PR #91), sem veredito válido |
| H8 | LLM como GERADOR de hipóteses (não preditor) | `h8-llm-hypothesis-generator` | **REGISTERED_NOT_ACTIVATED** — loop propor→avaliar→traçar implementado; coleta não iniciada |
| H9 | Razão OI/volume (crowding especulativo) | `h9-oi-volume-ratio-hmm-v1` | **CLOSED_INSUFFICIENT_SAMPLE** — PSR 0,162; IC cruza zero. Ressalva registrada: 44 dos 45 folds saíram `INSUFFICIENT_DATA`, então o agregado repousa sobre UMA janela |

A H5 continua com reprodutibilidade histórica limitada: faltam seus dados brutos originais. Os resultados e intervalos históricos são preservados com as ressalvas registradas em [HYPOTHESES.md](docs/HYPOTHESES.md). Controles sintéticos validam propriedades do software, sem demonstrar lucro de mercado.

## Dependências de pesquisa

- **Aave:** comparação com uma segunda fonte preparada, ainda sem execução conectada concluída; acesso a histórico, independência da fonte e orçamento precisam ser verificados. Veja [validação e custos](docs/AAVE_VALIDACAO_20260910.md).
- **Carry manual v2:** entrada prevista para 12/09/2026, das 00:00 às 01:00 UTC; encerramento em 05/12. O protocolo continua sem observações nesta conferência.
- **LLM pareado manual v3:** 84 janelas diárias de 12/09 a 04/12, das 12:00 às 13:00 UTC; o último alvo matura em 13/12. O executor está congelado em `C:\Cripto\auditoria-ampliada-20260910`, commit `595f120`.
- **Históricos e custos:** originais H5, versões macro com disponibilidade temporal comprovada e extratos pessoais de execução/custos continuam sem evidência suficiente. Ausência não significa custo zero.

Os caminhos, protocolos e condições de retomada estão na [conferência do chat](docs/CONFERENCIA_CHAT_20260910.md). As chaves atuais foram mantidas por decisão do dono; administração de segurança da branch ficou fora do escopo. Nenhuma ordem, agendamento, capital ou pagamento foi ativado.

## Preservação e histórico

Git contém código, documentação e evidências selecionadas. Configuração privada, banco operacional, dados completos e cópia privada do chat ficam em `C:\Cripto`; clonar o repositório sozinho não restaura toda a operação. O pacote original e `restaurado-20260908` permanecem preservados.

Documentos datados registram o estado de suas respectivas etapas. Para interpretar caminhos e instruções antigos, consulte a [conferência de arquivos](docs/CONFERENCIA_ARQUIVOS_20260910.md) e o [índice documental](docs/README.md). O [prompt original](docs/NEXT_CHAT_PROMPT.md) permanece intacto como mandato.


## Implementação arquitetural local — 2026-09-11

As alterações candidatas, seus limites, verificações e rollback estão em [ARCHITECTURE_IMPLEMENTATION.md](ARCHITECTURE_IMPLEMENTATION.md). Esta implementação local não publica releases, não atualiza automaticamente os consumidores e não altera os vereditos científicos históricos.
