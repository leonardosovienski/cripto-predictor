# Relatório Final de Verificação — GarimpoInvestimentos + DPL

**Data/hora da verificação:** 2026-07-02, ~00:45–00:50 (hora local da máquina).
**Método:** cada item conferido no repositório (git log, leitura de código, execução
de suítes e smokes ao vivo) — não na memória da conversa.

## 1. Marcos (17) — status

Todos os 17 marcos **verificados e concluídos** — detalhe item a item em
[CONFERENCIA_GERAL.md](CONFERENCIA_GERAL.md) §1. Resumo: auditoria original (1) ·
--discover `799cd27` (2) · controle positivo `e00e776` (3) · DSR+trials `ab346d3` (4) ·
equivalência `6416a71` (5) · DPL Fases 1-3 + fixes `27f8163..9a06a22` (6-9) · ADR do
merge `a9465aa` (10) · merge `e8b2fa3` (11) · resgate V3 `3507809` (12) · plano de
reconciliação `08c2dd3` (13) · Feature Store oficial `c6529a0` (14) · auditoria HMM
`0b35566` (15) · custos `1beea4e` (16) · **WFA concluído com veredito NO-GO** (17).

## 2. Suítes de teste (executadas nesta verificação)

| Onde | Resultado |
|---|---|
| `claude/merge-dpl-discovery` (principal) | **118 passed** (117 + regressão nova do fix abaixo) |
| Raiz / `claude/v3-quant-wip` (V3 — testes em `tests/test_v3_*`) | **87 passed, 2 skipped** (skips = hmmlearn, que roda na `.venv_v3`: 3/3 do look-ahead verdes lá) |
| `claude/clever-mclean-16f6d8` (DPL standalone) | **85 passed** |
| `claude/frosty-goldstine-1092c9` (origem discovery/controle) | **39 passed** |
| Controle positivo (verbose) | 3/3 PASSED |

Nota de roteiro: os testes da V3 vivem em `tests/` da raiz (prefixo `test_v3_`),
não em `v3/tests/`.

## 3. Integridade do histórico (verificada ao vivo)

- CSV legado **absorvido** pela Feature Store (idempotente; backfill `Fonte='direct'`
  para linhas pré-carimbo — coberto por teste; as linhas reais deste worktree já
  nasceram `dpl:fallback` e migraram com carimbo intacto).
- Novos registros **nascem carimbados**: smoke de hoje persistiu MORPHO (score 92,0,
  `fonte=dpl:fallback`, juiz gemini) na tabela `predictions`.
- Smoke `--ingest --discover 3` → 3×200 candles materializados → análise offline com
  universo da store → `--summary` destacando ≥60.

**Bug real encontrado e corrigido pela conferência (`9c94b59`):** um `store.close()`
herdado do fluxo pré-passo-4 rodava **antes** do `append_history` — previsões
pontuavam, exportavam e **não persistiam** (erro sqlite engolido). Os smokes
anteriores não pegaram porque as linhas entravam via migração do CSV. Corrigido
(close após append), regressão estrutural adicionada, persistência provada ao vivo.
É exatamente o tipo de furo que conferência de ponta a ponta existe para achar.

## 4. Documentação — estado

| Doc | Estado |
|---|---|
| `README.md` | ✅ Reescrito (2 camadas + V3, operação, status honesto) |
| `HANDOFF-2026-07-02.md` | ✅ Criado (linha do tempo, branches, ambientes, invariantes, pendências) |
| `docs/CONFERENCIA_GERAL.md` | ✅ Criado (marcos, matriz de riscos, recomendação) |
| `docs/ARQUITETURA_CONSOLIDADA.md` | ✅ Nota 6,0/10; riscos 1-4 fechados; §7 = veredito |
| `docs/AUDITORIA_HMM.md`, `RECONCILIACAO_V3.md`, `DECISAO_MERGE_DPL_DISCOVERY.md` | ✅ Existentes e fiéis ao código |

## 5. Matriz de riscos final (10 originais)

**Fechados (6):** look-ahead HMM · múltiplos testes (DSR/trials) · pipeline sem poder
(controle positivo) · custos · decisão por anedota (gates formais) · caminho live.
**Mitigados (2):** leakage por revisão (bitemporal; falta ADR-015) · divergência de
ambientes (3.13/3.14 documentados; falta CI).
**Abertos (2):** regime shift em produção (irrelevante sem produção) ·
**rotação das chaves antigas — ação pendente do proprietário desde 14/06**.

## 6. Veredito estatístico e nota

- **WFA determinístico com custos: NO-GO** (BTC: bruto +0,44bps → líquido −0,09bps
  por sinal, n=3.958; PSR 0,445; **DSR ≤ 0,445**, registrado em `trials.json`
  [v3-hmm-funding-oi-fr90, sharpe −0,0022]; kelly-invariante → nenhum sizing salva.
  ETH: PSR 0,051). Primeiro veredito com governança completa.
- **Nota final consolidada: 6,0/10** (dados 8,0 · software 7,5 · arquitetura 7,0 ·
  validação 7,0 · risco 5,0).

## 7. Próximos passos e recomendações

1. **Aprovar a reconciliação V3** ([RECONCILIACAO_V3.md](RECONCILIACAO_V3.md)) →
   executar merge → promover a `main` (hoje intacta em `a78580c`).
2. **Coleta diária** (`--ingest --discover` + análise) até o backtest do pipeline LLM
   ter n (hoje: 4 previsões, D+7 imaturo).
3. **Pivot de pesquisa da V3** — hipótese funding/OI+HMM fechada como formulada; novas
   hipóteses nascem registradas no `trials.json` e avaliadas líquidas de custos.
4. Menores: rotação de chaves (proprietário), C-03 (consenso ao vivo), equivalência
   ETH/SOL, ADR-015 (proveniência com hash), CI.

## 8. Declaração de fechamento

O projeto está **pronto e resolvido no estado atual de pesquisa**: todas as
verificações passando (329 testes verdes no ecossistema), documentação fiel ao
código, histórico oficial na Feature Store com carimbos, veredito estatístico
registrado com governança completa. **Sem recomendação para capital real** — a
infraestrutura está pronta; o edge, comprovadamente, ainda não existe.


