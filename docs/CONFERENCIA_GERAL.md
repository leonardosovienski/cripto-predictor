# Conferência Geral — 2026-07-02

> ## ⚠️ ERRATA 2026-08-21
>
> Retrato de 2026-07-02, preservado sem reescrita. Na matriz do §3, o risco 7
> ("falta CI") e o risco 8 ("rotação recomendada desde 14/06") **fecharam** — há CI
> com 4 jobs e as chaves foram rotacionadas em 2026-08-19. No §5, "reconciliação V3
> pendente", "DPL não promovida ao core" e "sem CI" também deixaram de valer; e dos
> pontos abertos do §6, restam apenas fragmentos (ver índice). O veredito do §4 e a
> nota do §5 continuam válidos.
>
> Índice: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).

> Revisão de TODOS os marcos do ciclo (auditoria → consolidação → veredito), com
> verificação de código, testes, commits e documentação. Método: cada marco foi
> conferido no repositório (não na memória da conversa); suítes re-executadas hoje.

## 1. Marcos — sumário de verificação

| # | Marco | Evidência | Status |
|---|-------|-----------|--------|
| 1 | Auditoria original (nota 5,0; riscos identificados) | Conversa + riscos rastreados neste doc §3 | ✅ |
| 2 | `--discover` (varredura + filtros + momentum) | `799cd27`; 10 testes; smoke ao vivo (10 candidatos reais) | ✅ |
| 3 | Controle positivo (edge sintético→validado; ruído→RUÍDO) | `e00e776`; 3 testes; prova de falha sem edge; re-executado verde hoje | ✅ |
| 4 | DSR + `trials.json` versionado | `ab346d3`; 7 testes; fio no backtest; 4 tentativas registradas, v3-fr90 com veredito preenchido | ✅ |
| 5 | Equivalência DPL vs direto | `6416a71`; bit-idêntico em candle fechado (btc/kaspa/aave); `change_*` 0,1-7,8pp quantificado; ETH/SOL pendentes (429) | ✅ (parcial declarado) |
| 6-8 | DPL Fases 1-3 (fallback, Feature Store+Alignment, agregação+breaker) | Branch `clever-mclean-16f6d8`; 85 verdes @ `80eb744`; smokes reproduzidos independentemente (fallback ao vivo, ingest 200 candles, degradação do consenso) | ✅ |
| 9 | Correções pós-auditoria (migração 0005 aditiva + teste de preservação) | `789f568`/`9a06a22`; `test_migration_0005_preserva_dados_existentes` | ✅ |
| 10 | ADR do merge (D1 symbol_map, D2 Fonte, D3 main.py) | `a9465aa`, [DECISAO_MERGE_DPL_DISCOVERY.md](DECISAO_MERGE_DPL_DISCOVERY.md) | ✅ |
| 11 | Merge DPL+discovery (linha principal) | `e8b2fa3`+`8e1451f`; smoke ponta a ponta com carimbo | ✅ |
| 12 | Resgate da V3 (estava não-commitada no checkout de main) | `3507809` em `claude/v3-quant-wip`; `data/` 130MB gitignored; `main` intacta | ✅ |
| 13 | Plano de reconciliação V3×principal | `08c2dd3`, [RECONCILIACAO_V3.md](RECONCILIACAO_V3.md); **merge aguarda aprovação** | ✅ (plano) |
| 14 | Feature Store = histórico oficial (migração 0006; backtest estratifica por Fonte) | `c6529a0`; CSV absorvido ao vivo (3 linhas, carimbos intactos); predictions conferida hoje | ✅ |
| 15 | Auditoria look-ahead HMM | `0b35566`, [AUDITORIA_HMM.md](AUDITORIA_HMM.md); invariância + contraprova; verde nas 2 venvs | ✅ |
| 16 | Modelo de custos | `1beea4e` (+`13522b9` persistência da série); 5 testes; gate opera sobre líquido | ✅ |
| 17 | WFA final com custos + DSR + controle positivo | Executado 2026-07-02: **NO-GO BTC e ETH** (ver §4) | ✅ **concluído** |

**Suítes (re-executadas hoje):** principal 117 ✅ · V3 87+2 skips ✅ · clever 85 ✅ (@tip, inalterada) · frosty 39 ✅ (@tip, inalterada). Worktrees limpas (1 inconsistência achada e corrigida: `_events_test.jsonl` era artefato de teste versionado — `0f01b65`).

## 2. Documentação gerada (finalidades)

| Doc | Finalidade |
|---|---|
| `README.md` | Visão geral atual, instalação, operação (reescrito hoje) |
| `HANDOFF-2026-07-02.md` | Onboarding: linha do tempo, branches, ambientes, invariantes, pendências |
| `HANDOFF.md` | Registro histórico da era pré-DPL (congelado) |
| `docs/ARQUITETURA_CONSOLIDADA.md` | Plano de 5 passos, nota, riscos, **veredito 5.3** |
| `docs/DECISAO_MERGE_DPL_DISCOVERY.md` | ADR do merge (D1-D3) |
| `docs/RECONCILIACAO_V3.md` | Plano de unificação V3×principal (aguarda aprovação) |
| `docs/AUDITORIA_HMM.md` | Fechamento do Risco 1 com prova automatizada |
| `docs/AUDITORIA_DPL.md` + `docs/DOSSIE_PLATAFORMA.md` | Auditoria interna e desenho da plataforma (pré-existentes) |
| `docs/CONFERENCIA_GERAL.md` | Este documento |

## 3. Matriz de riscos original (10) — estado final

| # | Risco (auditoria de 01/07) | Estado | Evidência |
|---|---|---|---|
| 1 | Look-ahead na decodificação do HMM | **FECHADO** | Forward causal + scaler congelado + IS-only + invariância testada |
| 2 | Falso GO por múltiplos testes | **FECHADO** | DSR + trials.json; o "GO" pré-custos de 27/06 foi efetivamente desmascarado |
| 3 | Pipeline sem poder estatístico | **FECHADO** | Controle positivo (verde hoje) |
| 4 | Custos não modelados | **FECHADO** | CostModel; resultado: custos comem o edge (§4) |
| 5 | Leakage por revisão de dados | **MITIGADO** | Feature Store bitemporal daqui em diante; falta hash de proveniência (ADR-015) |
| 6 | Regime shift estrutural | **ABERTO** | WFA ancorado mitiga; sem monitor de drift em produção (não urgente: sem produção) |
| 7 | Divergência de ambientes | **MITIGADO** | 3.13 (venvs) + 3.14 (suítes) documentados e validados; falta CI |
| 8 | Chaves antigas hardcoded em cópias | **ABERTO** | Rotação recomendada desde 14/06 — ação do usuário |
| 9 | Decisão de arquitetura por anedota | **FECHADO (processo)** | Gates formais (pedágio+DSR+controle positivo); dois NO-GO aceitos com base em número |
| 10 | Caminho live nunca exercitado | **FECHADO** | Smokes reais: fallback, ingestão, análise LLM, migração de histórico |

## 4. Veredito estatístico final (passo 5.3)

**NO-GO** — BTCUSDT: bruto +0,44bps/sinal → **líquido −0,09bps** (n=3.958 OOS, 44 folds);
PSR 0,445; DSR ≤ 0,445 (corte 0,95); IC do líquido cruza zero; MaxDD 29%. ETHUSDT pior
(PSR 0,051). PSR/IC invariantes a Kelly → nenhum sizing salva. Detalhe e leitura completa:
[ARQUITETURA_CONSOLIDADA.md §7](ARQUITETURA_CONSOLIDADA.md). É o primeiro veredito do
projeto emitido com TODA a governança ativa — a hipótese funding/OI+HMM está fechada
como formulada, com confiança.

## 5. Nota final: **6,0/10** (era 5,0 na auditoria original; 5,5 pós-DPL)

Sobe pela qualidade da resposta, não pelo resultado: engenharia de dados 8,0 ·
software 7,5 · arquitetura 7,0 · validação estatística 7,0 · gestão de risco 5,0.
O que impede nota maior: edge inexistente (produto ainda não tem razão econômica),
reconciliação V3 pendente, DPL não promovida ao core, sem CI, proveniência parcial.

## 6. Pontos abertos

1. **Aprovação da reconciliação V3** (RECONCILIACAO_V3.md) → depois, promoção a `main`.
2. Coleta diária do pipeline LLM (backtest do Garimpo segue "dados insuficientes", n=3).
3. Pivot de pesquisa da V3 (hipótese atual fechada; novas nascem no trials.json).
4. C-03 (consenso ao vivo), equivalência ETH/SOL, ADR-015 (hash de proveniência),
   rotação de chaves antigas, CI.

## 7. Recomendação final

**Continuar como projeto de pesquisa; produção (mesmo assistida) NÃO autorizada** —
não por imaturidade de engenharia (essa barreira caiu neste ciclo), mas porque **não
existe edge demonstrado para operar**. A infraestrutura construída (DPL bitemporal,
pedágio estatístico com controle positivo, DSR, custos) é exatamente o que torna os
próximos ciclos de hipótese baratos e confiáveis: formular → registrar tentativa →
backtest líquido → veredito em que se pode confiar. O projeto aprendeu a dizer "não"
com rigor; o próximo objetivo é ter uma hipótese que mereça um "sim".


