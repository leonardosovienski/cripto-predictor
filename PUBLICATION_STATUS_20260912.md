# Publicação atual e ordem de leitura

Consolidação de engenharia encerrada em 12/09/2026. Esta seção substitui o estado de publicação das seções históricas abaixo.

- Checkout principal: `C:\Cripto\pesquisa-20260909`, branch `main`, limpo na conferência.
- Commit de código certificado: `9db8e9300dd5f743b71675e5217bee8cbeee5c90`.
- Ecosystem entregue em `main`: `6a998520825292895bcae71e589fa8ac0e02bb85`; CAIN inalterado: `5ba4177a11b9312900e5035517aa5ef25d509859`.
- [CI da main](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34726096966) e [integração instalada](https://github.com/leonardosovienski/cripto-predictor/actions/runs/34726096957): aprovadas nesse commit. Não atribuir esses runs a commits documentais posteriores.
- As 16 branches remotas antigas do Crypto foram removidas após preservação e certificação; os stores locais operacionais mantêm somente `main`. Worktrees históricos conservam seus commits, arquivos e conflitos, com HEAD destacado.
- Relatório completo local: `C:\Cripto\operacao\relatorios\auditoria-main-20260912-01\RELATORIO_FINAL.md`. Recibos: subpasta `retomada-02`.

## Leia nesta ordem

1. `C:\Cripto\LEIA_PRIMEIRO.md` e `C:\Cripto\AGENTS.md`: raiz, preservação e regras locais.
2. Este documento: entrega atual e distinção dos registros históricos.
3. [Configuração local](docs/CONFIGURACAO_LOCAL.md) e [mapa da pasta e continuidade](docs/LOCAL_FOLDER_AUDIT.md).
4. [Auditoria e combinação reproduzível](docs/FINAL_INTEGRATION_AUDIT.md) e o relatório completo local.
5. [Índice documental](docs/README.md), protocolos e evidências específicas do próximo trabalho.

## Conferência após novos commits

```powershell
git -C C:\Cripto\pesquisa-20260909 status --short --branch
git -C C:\Cripto\pesquisa-20260909 rev-parse HEAD
git -C C:\Cripto\pesquisa-20260909 ls-remote origin refs/heads/main
C:\Cripto\CRIPTO.cmd status
```

O SHA de HEAD deve coincidir com a main remota. Mudanças apenas documentais posteriores têm sua própria conferência; não mudam a identidade dos testes do código certificado. Consolidação não reinstala bibliotecas operacionais, não ativa agendamentos e não autoriza capital. O conflito preservado em `publicacao-chat-20260909` pertence ao acervo histórico e não à árvore canônica.

---

## Registro histórico anterior à consolidação — superado

As branches, bloqueios e próximos passos abaixo descrevem uma etapa anterior. Não são pendências atuais da auditoria encerrada.

# Estado de publicação e continuidade — Crypto

Conferência documental de 12/09/2026. Este registro complementa os protocolos científicos e substitui apenas afirmações anteriores de que o candidato ainda não teve commit/push.

- Checkout de trabalho: `C:\CRIPTO\pesquisa-20260909`.
- Branch de trabalho: `validation/retest-six-20260911`. Não presumir que `main` contém esta entrega.
- HEAD conferido antes desta atualização documental: `aeb1b779703def8e3b188e05cde0e7fbfc4552f1`.
- O código deste projeto foi publicado na branch indicada. O candidato CAIN Supply permanece sem aprovação de estabilização.
- Sem merge, release, instalação operacional ou nova execução científica nesta conferência.

## Validação e pendências

A [CI geral do CAIN](https://github.com/leonardosovienski/cain/actions/runs/34674661122) passou para `7e6105e`.
O [gate Linux dedicado](https://github.com/leonardosovienski/cain/actions/runs/34674661161) falhou na suíte completa em Python 3.13 e 3.14.
No artefato 3.13, equivalência do candidato confirmada e 187 testes direcionados passaram sem skips. A suíte completa registrou 547 passes, 13 falhas, 4 erros e 2 skips: faltam arquivos de cenários na instalação isolada do wheel CAIN. Esses resultados não certificam o runtime científico deste projeto.
As etapas posteriores de E2E instalado, restore offline, testes dos produtores e mini-auditoria não foram alcançadas nessa execução. Próximo gate: corrigir a localização/empacotamento dos cenários, congelar o candidato corrigido, repetir os testes afetados e concluir o Linux antes de discutir estabilização.

## Preservação e retomada

Foram inventariados 140 Markdown versionados antes da atualização, com hashes e verificação de leitura UTF-8. Inventário local: `C:\CRIPTO\operacao\relatorios\documentation-sync-20260912`.
Inventário não é recertificação semântica de cada relatório histórico nem prova de backup dos arquivos ignorados pelo Git. Relatórios datados, fontes, bancos, manifests e snapshots congelados conservam seus bytes e contexto. Outros worktrees são checkouts de outras branches; não devem receber cópia cega desta branch.
Leia os documentos de entrada deste checkout e seus protocolos antes de executar trabalho de domínio. Para verificar publicação após novos commits: `git status --short`, `git rev-parse HEAD` e `git ls-remote origin refs/heads/validation/retest-six-20260911`; os dois SHAs devem coincidir e o status deve estar vazio.

## Exceções locais encontradas nesta conferência

O checkout ativo acima é o destino atualizado. O worktree histórico
`C:\Cripto\publicacao-chat-20260909` conserva alterações anteriores e conflitos
não resolvidos em README.md, tests/test_review_failure_boundaries.py e
tests/test_store_history.py. Não é um checkout limpo nem uma entrega atual;
seu trabalho não foi descartado, resolvido automaticamente ou incorporado à branch ativa.
O snapshot `C:\Cripto\restaurado-20260908\projeto` contém `fred_test.csv`
não versionado, igualmente preservado. Portanto a sincronização da branch ativa
não significa que todos os diretórios históricos sejam cópias limpas do GitHub.


## Encerramento e retomada da sessão

Registro consolidado: [decisões, acertos, erros, pendências e próximo prompt](https://github.com/leonardosovienski/cain/blob/feature/research-bundle-v1/docs/research/SESSION_HANDOFF_20260912.md). O gate Linux permanece reprovado. A conferência documental não foi uma revisão semântica integral dos relatórios históricos. Os dois skips conferidos no XML Linux 3.13 são testes exclusivos do launcher Windows; não incluem o teste obrigatório de symlink, que passou.
