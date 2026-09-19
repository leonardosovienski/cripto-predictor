# Continuar o projeto Cripto

Este é o ponto de entrada de continuidade. O corte econômico mais recente foi conferido em **19/09/2026** na branch `profit-recovery-20260919`; o último corte integrado em `main` descrito abaixo continua sendo o de 17/09. Este documento não é um painel ao vivo do computador, dos provedores ou de commits futuros. Documentos datados descrevem suas próprias etapas.

## Execução econômica Nível 2/3 — 19/09/2026

Leia primeiro o [handoff autocontido](docs/continuity_20260919/README.md) e o [relatório completo](docs/continuity_20260919/REUSE_VERIFY_GAP_EXECUTION.md). A branch contém o laço causal de recuperação de lucro, ledger V2, agrupamento em episódios, custos comparáveis e as rodadas BTC/ETH/SOL.

Resultado: `INCONCLUSIVE`; operação `RESEARCH_ONLY`; paper trading e microcapital `NOT_READY`; reservado final `RESERVED_FINAL_INSUFFICIENT`. Não foi provado edge incremental do PR122. A branch não está integrada em `main`, não foi instalada na operação principal e não autoriza capital.

## Último corte de engenharia conferido

- Repositório: `leonardosovienski/cripto-predictor`, branch `main`.
- Código após o PR #120: `e5997104f9c72f31764acdbdd4d26ec176791b68`.
- [CI 35274798009](https://github.com/leonardosovienski/cripto-predictor/actions/runs/35274798009): `completed / success` nesse SHA.
- [Integração instalada 35274798091](https://github.com/leonardosovienski/cripto-predictor/actions/runs/35274798091): `completed / success` nesse SHA.
- Core selecionado: `3.2.1`; Ops selecionado: `4.2.1`. Fontes e hashes: [pyproject.toml](pyproject.toml) e [uv.lock](uv.lock).
- Integração pinada: Ecosystem `c51d9e63e8441e15b2d045ea4d6a7c67f4ebbdfd`; CAIN `5ba4177a11b9312900e5035517aa5ef25d509859`. O [guia de integração](docs/FINAL_INTEGRATION_AUDIT.md) separa configuração atual de reprodução histórica.

Esses runs não certificam commits documentais posteriores, uma instalação principal do CAIN, dados privados ou lucro. A release `v1.1.0` de 11/09 e a fonte posterior de `main` não são artefatos intercambiáveis apenas porque os metadados conservam a mesma versão. Não houve nova release nem implantação nesta atualização documental.

## Ordem de leitura

1. Neste Windows, leia `C:\Cripto\LEIA_PRIMEIRO.md` e `C:\Cripto\AGENTS.md`, depois [CONFIGURACAO_LOCAL.md](docs/CONFIGURACAO_LOCAL.md). São regras do perfil local, não prova de que esta sessão acessou o PC.
2. Leia este documento e o [README](README.md) para engenharia, capacidades e limites.
3. Leia a [errata de evidências](docs/ERRATA_AUDITORIA_20260915.md) **antes de reutilizar** HYPOTHESES, EVIDENCE_REGISTRY, o texto de notes do charter ou os índices de congelamento.
4. Use o [índice documental](docs/README.md) para selecionar o protocolo, evidência ou runbook pertinente. O [prompt original](docs/NEXT_CHAT_PROMPT.md) é um mandato preservado, não uma ordem para repetir automaticamente todas as auditorias antigas.
5. Para recuperação, consulte a [conferência dos arquivos](docs/CONFERENCIA_ARQUIVOS_20260910.md), os [pacotes de 09/09](docs/continuity_20260909/README.md) e os [pacotes de 10/09](docs/continuity_20260910/README.md). Não extraia sobre bancos, snapshots ou ambientes existentes.

## Conferir antes de executar ou manter o ambiente

```powershell
git -C C:\Cripto\pesquisa-20260909 status --short --branch
git -C C:\Cripto\pesquisa-20260909 rev-parse HEAD
git -C C:\Cripto\pesquisa-20260909 ls-remote origin refs/heads/main
C:\Cripto\CRIPTO.cmd status
```

Registre o SHA efetivo e eventuais alterações locais. Se houver divergência, preserve o trabalho e investigue antes de sincronizar; não use reset, limpeza ou cópia cega para forçar igualdade. Consulte os checks do SHA que será utilizado. A aprovação de um corte anterior não se transfere automaticamente.

O checkout do perfil local é `C:\Cripto\pesquisa-20260909`. O executor LLM do protocolo manual v3 é separado, em `C:\Cripto\auditoria-ampliada-20260910`, fonte congelada `595f1203475d04b01966ac3471bbafd6770dbb4d`. Não substitua esse executor pelo código de desenvolvimento. Novos relatórios desse PC ficam em `C:\Cripto\operacao\relatorios`.

## Pendências e ressalvas que não desapareceram com a CI

**Dados operacionais:** o snapshot v4 documentado em 10/09 venceu em 11/09 às 02:00 UTC. A [auditoria de 15/09](docs/AUDITORIA_TECNICA_20260915.md) ainda relatava `STALE`. O banco privado não foi consultado nesta atualização; contagens antigas não são contagens atuais.

**Janelas manuais:** carry v2 tinha entrada em 12/09, 00:00–01:00 UTC; LLM pareado v3 tinha início em 12/09, 12:00–13:00 UTC. São calendários já iniciados, não próximas janelas. Não foi verificada nova coleta. Leia os protocolos e recibos antes de agir; não retroaja horários nem desloque o calendário silenciosamente.

**Aave:** a tentativa de segunda fonte de 11/09 foi `INCOMPLETE`, com `ConnectTimeout`, sem corroboração dos 38 pontos. **H5, macro e custos pessoais:** as lacunas históricas permanecem sem solução comprovada nos registros consultados.

**H6:** n observado=84; a tabela estática de poder usa n de referência=60. Não atribua 23,3%/47,3% a n=84. H6/H9 continuam `CLOSED_INSUFFICIENT_SAMPLE`; H7/H8 continuam registradas sem ativação. Atestados históricos que expiraram não são renovados por edição documental.

**Exportação:** os exportadores preservam os estados e textos literais das fontes admitidas; não aplicam automaticamente a errata. Reutilize resultados com a ressalva correspondente e não altere hashes de admissão para disfarçar mudanças de fonte.

## Registros históricos e escopo desta correção

A [publicação de 12/09](PUBLICATION_STATUS_20260912.md), a [consolidação de 15/09](docs/CONSOLIDACAO_MAIN_20260915.md) e o [handoff integral preservado](HANDOFF_HISTORICO_ATE_20260917.md) mantêm seus respectivos cortes. O [conteúdo anterior desta página](https://github.com/leonardosovienski/cripto-predictor/blob/e5997104f9c72f31764acdbdd4d26ec176791b68/CONTINUAR_AQUI.md) permanece recuperável no Git.

Esta rodada corrige os problemas documentais identificados. Não declara revisão semântica integral de todos os Markdown, verificação de todos os links externos ou restauração do acervo privado. Fontes científicas congeladas, protocolos, resultados, atestados e seus hashes não foram reescritos. Não foram ativados agendamentos, coletas, modelos, ordens, pagamentos ou capital. Segurança da branch e administração de credenciais não são alteradas por esta tarefa.
