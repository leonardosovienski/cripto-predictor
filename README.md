# cripto-predictor (GarimpoInvestimentos + DPL)

Sistema de pesquisa em criptoativos: ingestão e procedência de dados, análises com LLM, diagnósticos quantitativos e avaliação estatística. Nenhuma linha tem lucro pessoal ou futuro comprovado; os resultados históricos positivos de Aave são condicionais aos cenários de custo. A V3 emite diagnóstico `UNVALIDATED`.

> **Continuidade:** [CONTINUAR_AQUI.md](CONTINUAR_AQUI.md) é o ponto de entrada para o último corte conferido, a ordem de leitura e as pendências. A execução econômica Nível 2/3 de 19/09 está no [handoff reuse/verify/gap](docs/continuity_20260919/README.md). [Índice documental](docs/README.md). Documentos datados não são painéis ao vivo da instalação.
>
> **Antes de reutilizar resultados históricos:** leia a [errata de evidências](docs/ERRATA_AUDITORIA_20260915.md). Na H6, a amostra observada é n=84, mas os poderes de 23,3% e 47,3% pertencem à tabela de referência n=60. As fontes congeladas conservam seus bytes e devem ser acompanhadas da errata.

## Engenharia: último corte de código conferido

Em 17/09/2026, o PR #120 está integrado em `main`, commit `e5997104f9c72f31764acdbdd4d26ec176791b68`. A [CI desse commit](https://github.com/leonardosovienski/cripto-predictor/actions/runs/35274798009) e a [integração instalada desse commit](https://github.com/leonardosovienski/cripto-predictor/actions/runs/35274798091) concluíram com sucesso. Esses resultados pertencem exclusivamente a esse SHA; alterações posteriores precisam de verificações próprias.

| Componente | Configuração no corte conferido |
|---|---|
| Pacote principal | Metadados `1.1.0`; Python `>=3.13,<3.15` |
| Core | Wheel `3.2.1`, selecionado em `pyproject.toml` e `uv.lock` |
| Ops | Wheel `4.2.1`, selecionado em `pyproject.toml` e `uv.lock` |
| Exportador independente | `crypto-research-export` `1.0.1`; Python `>=3.11` |
| Contratos do produtor | Snapshot `>=1.0.1,<2`; extra Bundle `1.0.0` |

As versões selecionadas por URL não devem ser confundidas com os limites inferiores das faixas de dependência. Fontes e hashes ficam em [pyproject.toml](pyproject.toml), [uv.lock](uv.lock) e nos verificadores de instalação. A [documentação de integração](docs/FINAL_INTEGRATION_AUDIT.md) distingue a combinação atual da reprodução do corte histórico de 12/09.

A [release v1.1.0 de 11/09](https://github.com/leonardosovienski/cripto-predictor/releases/tag/v1.1.0) é uma entrega anterior. O número nominal `1.1.0` não significa que seus artefatos contenham todas as mudanças posteriores de `main`. Esta atualização documental não publica release, não reinstala o ambiente operacional e não autoriza capital.

## Comece aqui

- [Continuidade e estado conferido](CONTINUAR_AQUI.md): leitura, limites e verificação após novos commits.
- [Configuração do Windows em C:\Cripto](docs/CONFIGURACAO_LOCAL.md): diretórios, ambiente e configuração privada.
- [Ferramentas de pesquisa offline](GarimpoInvestimentos/research/README.md): universo, fatores, splits temporais, ordens sintéticas e experimentos reproduzíveis.
- [Exportador Snapshot](packages/research-export/README.md) e [ResearchBundleV1](docs/RESEARCH_BUNDLE_V1.md): ambientes independentes e admissão explícita das fontes.
- [Índice da documentação](docs/README.md): pesquisa, recuperação, protocolos e registros históricos.

## Execução neste Windows

Checkout de referência: `C:\Cripto\pesquisa-20260909`. Confira seu HEAD e estado local antes de manutenção. Use o atalho que aplica os caminhos e o ambiente do projeto:

```powershell
C:\Cripto\CRIPTO.cmd status
C:\Cripto\CRIPTO.cmd pipeline --help
C:\Cripto\CRIPTO.cmd uv --version
```

O `status` verifica a configuração sem consultar APIs. Credenciais ficam somente em `C:\Cripto\configuracao\pipeline.env`, conforme o [mapa local](docs/CONFIGURACAO_LOCAL.md). O [exemplo público](GarimpoInvestimentos/.env.example) documenta nomes de variáveis; não substitui o perfil deste PC.

A sincronização de manutenção documentada é `C:\Cripto\CRIPTO.cmd uv sync --frozen --all-extras`. Esse comando altera o ambiente e só deve ser executado em uma manutenção autorizada, após conferir fonte, lockfile e preservação. Não atualize os runtimes congelados dos observadores junto com o checkout de desenvolvimento. Os extras `llm`, `v3`, `excel`, `science` e `test` são necessários para exercitar toda a suíte.

Na CI do corte conferido, `quality` e `all-extras` usam todos os extras em Python 3.13; `python-314-experimental` usa o perfil reduzido `test` + `science`, com lock. Um resultado do perfil reduzido não substitui a validação completa. A integração tem seus próprios ambientes e matriz, descritos no [guia de integração](docs/FINAL_INTEGRATION_AUDIT.md).

As verificações devem usar dados sintéticos e diretórios isolados, sem carregar chaves privadas. O [registro da revisão de 09/09](docs/REVISAO_COMPLETA_20260909.md) e a [auditoria técnica de 15/09](docs/AUDITORIA_TECNICA_20260915.md) preservam contagens e limitações de suas respectivas execuções. No Windows, a disponibilidade de symlinks depende dos privilégios; não transforme um skip em teste aprovado.

Coletas conectadas exigem janela, fontes e orçamento disponíveis. O perfil local documenta 28 unidades de ingestão, 8 tentativas de notícias por provedor e 6 chamadas lógicas de LLM por provedor, por dia UTC. Consulte [guardas de API](docs/API_GUARDS.md). A revisão documental não consultou provedores, não verificou quotas atuais e não ativou agendamentos.

## Dados e componentes

| Componente | Contrato e limite |
|---|---|
| DPL | Ingestão com contratos de instrumento, moeda, temporalidade e procedência; cobertura depende da fonte e de sua versão histórica. |
| Feature Store | Caminho do perfil local: `C:\Cripto\operacao\saidas\feature_store.db`. Snapshots e inputs preservam o contexto das novas previsões; isso não torna o banco inteiro imutável. |
| LLM | Mercado armazenado, notícias e juiz identificado; recibos e conteúdo preservado não recuperam fontes históricas perdidas. |
| Backtest | Retornos após a previsão; bootstrap e DSR sujeitos aos contratos de amostra, unidades e comparabilidade das tentativas. |
| V3 | HMM, funding/OI e walk-forward; os controles de engenharia não comprovam eficácia econômica. Custos pessoais de execução não estão calibrados por extratos disponíveis. |
| Operação | Lock, heartbeat e diagnóstico; executores manuais obedecem aos próprios protocolos e não são ativados por documentação. |

O corte operacional de 10/09 registrou três previsões, dois snapshots e um registro de inputs. Seu snapshot v4 venceu em **11/09/2026 às 02:00 UTC**. A auditoria de 15/09 ainda relatava dados operacionais `STALE`. Não houve acesso ao banco privado nesta atualização; essas contagens não são uma leitura atual. Consulte [backup e restauração](docs/BACKUP_RESTORE.md) antes de manutenção.

## Estado científico

As famílias antigas seguem o [charter](charters/scientific_state.json), acompanhado da [errata de interpretação](docs/ERRATA_AUDITORIA_20260915.md), e os registros de congelamento. Novas linhas têm protocolos separados; infraestrutura não reabre hipóteses encerradas.

| # | Hipótese | Trial (`trials.json`) | Status |
|---|---|---|---|
| H1 | Funding/OI + regime HMM prevê retorno 24h | `v3-hmm-funding-oi-fr90` | **CLOSED_NO_GO**; resultado histórico sob o modelo de custos registrado |
| H2 | Janela curta de funding (fr21) | `v3-hmm-funding-oi-fr21` | **CLOSED_NO_GO** |
| H3 | Horizonte 48h amortiza a fricção | `v3-hmm-funding-oi-fr90-h48` | **CLOSED_NO_GO** |
| H4 | Score do LLM prevê retorno D+7 | `v2-dpl-gemini-h7` | **CLOSED_INSUFFICIENT_SAMPLE**; coleta interrompida com cinco previsões declaradas, sem veredicto estatístico |
| H5 | Score D+7 com partição multi-juiz | `v2-dpl-multi-h7` | **CLOSED_NO_GO**; resultado histórico negativo, reprodução limitada pelos dados originais ausentes |
| H6 | Leitura invertida do score do LLM | `h6-sinal-invertido-d7` | **CLOSED_INSUFFICIENT_SAMPLE**; n observado=84, IC cruza zero; poder tabelado para n de referência=60, não 84 |
| H7 | Calendário macro (FOMC/CPI/PPI) + DXY | `h7-macro-dxy-hmm-v1` | **REGISTERED_NOT_ACTIVATED** |
| H8 | LLM como gerador de hipóteses, não preditor | `h8-llm-hypothesis-generator` | **REGISTERED_NOT_ACTIVATED** |
| H9 | Razão OI/volume | `h9-oi-volume-ratio-hmm-v1` | **CLOSED_INSUFFICIENT_SAMPLE**; 44 dos 45 folds insuficientes |

H4 foi interrompida com cinco previsões declaradas, sem veredicto estatístico. H5 preserva resultado histórico negativo, mas faltam seus dados brutos originais. H6 tem rho aproximadamente -0,0567 e IC95 [-0,2312; +0,1294], com n=84; o intervalo cruza zero e não deve ser chamado de refutação. Os valores de poder disponíveis têm **n de referência 60, não 84**. H9 teve 44 de 45 folds insuficientes. Não foram recalculados resultados nem alterados estados nesta correção.

Leia a errata **antes** de [HYPOTHESES.md](docs/HYPOTHESES.md), [EVIDENCE_REGISTRY.md](docs/EVIDENCE_REGISTRY.md), [CR_FREEZE_INDEX.md](CR_FREEZE_INDEX.md) ou [CR_RESEARCH_FREEZE.md](CR_RESEARCH_FREEZE.md). Os originais continuam sendo fontes históricas, com suas ressalvas e proveniência, não sínteses corrigidas automaticamente pelo exportador.

## Pendências de pesquisa: última evidência disponível

- **Aave:** a tentativa de segunda fonte de 11/09 terminou `INCOMPLETE` por `ConnectTimeout`, sem corroboração dos 38 pontos. Veja a [errata](docs/ERRATA_AUDITORIA_20260915.md) e a [validação histórica e custos](docs/AAVE_VALIDACAO_20260910.md).
- **Carry manual v2 e LLM pareado manual v3:** os calendários registrados começam em 12/09. Essa data já passou; não a trate como próxima janela nem conclua que houve coleta sem recibo. Preserve o calendário e registre ausências conforme o protocolo, sem retroagir previsões. O executor LLM permanece uma referência congelada distinta do desenvolvimento: `595f1203475d04b01966ac3471bbafd6770dbb4d`.
- **Históricos e custos:** originais H5, versões macro com disponibilidade temporal comprovada e extratos pessoais continuam lacunas nos registros consultados. Ausência não significa custo zero.

Os protocolos, diretórios e calendários completos permanecem na [conferência do chat](docs/CONFERENCIA_CHAT_20260910.md), nas [dependências executadas](docs/manual_dependencies_20260910/EXECUCAO.md) e na [continuidade de 11/09](docs/continuity_20260911/README.md). Nenhuma coleta, ordem, pagamento ou autorização de capital foi executada nesta revisão.

## Preservação e histórico

Git contém código, documentação e evidências selecionadas. Configuração privada, banco operacional, dados completos e cópia privada do chat ficam fora do repositório; clonar o Git não restaura toda a operação.

A [conferência de arquivos de 10/09](docs/CONFERENCIA_ARQUIVOS_20260910.md), os [cinco pacotes com 2.685 arquivos daquele corte](docs/continuity_20260910/README.md) e o [handoff histórico](HANDOFF_HISTORICO_ATE_20260917.md) permanecem referências de preservação. O [README anterior integral](https://github.com/leonardosovienski/cripto-predictor/blob/e5997104f9c72f31764acdbdd4d26ec176791b68/README.md) é recuperável pelo SHA imutável. Contagens históricas de testes e afirmações sobre máquinas antigas não devem ser substituídas por números atuais.
