# Fechamento e retomada — 11/09/2026

## Comece aqui

Checkout: `C:\Cripto\pesquisa-20260909`. Branch desta publicação: `research/aave-validation-20260910`. Remoto: https://github.com/leonardosovienski/cripto-predictor. Esta publicação faz commit e push da branch; não implica merge em main. Confira `git log -1`, `git status -sb` e `git ls-remote origin refs/heads/research/aave-validation-20260910`.

1. Leia [o relatório final](../open_source_research/20260911T0525/FINAL_REPORT.md), [a matriz](../open_source_research/20260911T0525/CAPABILITY_TRANSFER_MATRIX.md) e [o plano executado/backlog](../open_source_research/20260911T0525/IMPLEMENTATION_PLAN.md).
2. Leia [o README do toolkit](../../GarimpoInvestimentos/research/README.md) para rodar demo/run/list/verify/compare.
3. Consulte [o estudo baseline](../open_source_research/20260911T0233/REPORT.md) e os subdiretórios phase2, phase3 e phase3b. Não repetir discovery amplo ou auditoria concluída por causa do mandato histórico em NEXT_CHAT_PROMPT.

## O que foi entregue

Cinco capacidades locais: painel de fatores, filtros de universo por versões conhecidas, split de labels por intervalo/disponibilidade, caixa reservado por venue/moeda em cenário spot sintético e registro reproduzível de runs. Sete módulos Python novos, integração à CLI e 24 testes específicos. Zero dependências obrigatórias adicionadas.

Regressão: 1.528 aprovados e um ignorado. A bateria final de 24 passou; 23 deles já estavam na regressão, portanto não somar as contagens como testes únicos. Ruff, formato, Pyright e scanner aprovados. Build inicial sem isolamento falhou por hatchling ausente; build isolado passou e o demo importado diretamente do wheel fora do checkout passou. Veja [recibos completos](../open_source_research/20260911T0525/evidence/), especialmente CHECKS.json, FINAL_CHECKS.json, WHEEL_CHECK.json e tests_accepted.xml. CI remoto desta publicação não está certificado por esses resultados locais.

Os relatórios congelados descrevem o corte anterior ao commit como “sem commit/push”. Este documento registra a etapa posterior de publicação sem reescrever os bytes daqueles relatórios. A preservação de 229 arquivos refere-se ao corte da implementação; NEXT_CHAT_PROMPT recebeu agora apenas este novo prefácio de continuidade, por pedido do dono. Nenhum protocolo científico foi alterado.

## Estado científico e próximo trabalho

F01 identidade/contrato histórico permanece limitado; F02 Aave depende de corroboração independente tecnicamente disponível; F03 universo PIT e F04 replay econômico continuam bloqueados pelos contratos/dados pertinentes; F05 mantém seus resultados e limites sem retuning. H1/H2/H3/H5 CLOSED_NO_GO; H4/H6/H9 insuficientes; H7/H8 inativos. funding_oi_hmm_v3 e pilotos congelados permanecem assim. Nenhuma evidência suficiente para validação econômica prospectiva foi produzida pelo toolkit.

Próximo experimento técnico de maior valor: otimização restrita de carteira/caixa versus equal-weight e solução analítica de dois ativos (G06). Depois: contrato fit/infer por fold, fixture diferencial Alphalens, fila/latência calibrada e seleção multi-instrumento, conforme backlog. Isso não autoriza operações financeiras ou altera experimentos congelados. Não chamar inputs sintéticos de dados reais, falha de infraestrutura de rejeição científica ou resultado histórico de validação prospectiva.

## Mapa local e preservação

| Local | Conteúdo |
|---|---|
| `C:\Cripto\pesquisa-20260909` | Código, Markdown, testes e evidências versionadas |
| `C:\Cripto\operacao\relatorios\OPEN_SOURCE_20260911T0233` | Pesquisa original e arquivos operacionais complementares |
| `C:\Cripto\operacao\relatorios\CAPABILITY_TRANSFER_20260911T0525` | Recibos, fontes upstream fixadas, scripts, demos e wheel |
| `C:\Cripto\restaurado-20260908` | Snapshot e dados restaurados; não sobrescrever |
| `C:\Cripto\configuracao\pipeline.env` | Configuração privada, fora do Git; não publicar |
| `C:\Cripto\auditoria-ampliada-20260910` | Executor LLM congelado; não substituir pelo checkout |

A pasta local foi conferida por inventário e hashes das evidências desta rodada, não por nova restauração/revalidação integral dos 66 mil arquivos históricos. Pastas de worktrees, caches, ambientes e backups não foram apagadas nem publicadas indiscriminadamente. O Git guarda fontes e evidências selecionadas, não todas as bases/runtime/configuração privada. Preserve C:\Cripto para manter esses itens. Os arquivos de entrega exibidos pelo Codex não são a única cópia do resultado: fontes, relatórios e recibos estão nesta raiz.

O fechamento preserva decisões, comandos, testes e caminhos necessários para continuar; não é uma exportação literal de todas as mensagens do chat. Os backups privados anteriores mantêm seus próprios cortes históricos.

## Uso

```powershell
C:\Cripto\CRIPTO.cmd python -m GarimpoInvestimentos.research demo --store C:\Cripto\operacao\relatorios\research-runs
```

Use run_id novo a cada execução; o registro recusa sobrescrita. O demo não conecta a bolsas nem ativa capital. Leia AGENTS.md e CONFIGURACAO_LOCAL.md para caminhos e ambiente.
