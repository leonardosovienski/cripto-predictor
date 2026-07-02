# Plano de Reconciliação — V3 quantitativa × linha mergeada (DPL + discovery)

> Passo 4.1 do plano. Pré-requisito de qualquer merge entre `claude/v3-quant-wip`
> (`3507809`, resgate da linha V3 que estava não-commitada no checkout de main) e
> `claude/merge-dpl-discovery` (linha principal, 113 verdes). **Merge só após
> aprovação deste documento.**

## 1. Inventário das duas linhas

| | `merge-dpl-discovery` (principal) | `v3-quant-wip` (resgate) |
|---|---|---|
| Base | `a78580c` (main) | `a78580c` (main) |
| Núcleo | `dpl/` (Feature Store bitemporal, routers, providers), `discovery`, DSR/trials, equivalência | `v3/` (regime_engine HMM causal, signal_engine, paper_trader, backtest_v3, collectors funding/OI/vision) |
| Utilitários | `core/` (com carimbo **Fonte** no history) | `store/` = rename mecânico do `core/` original (conteúdo idêntico exceto imports) |
| `main.py` | Fluxo DPL (ingest/serving) + `--discover` | Base ANTIGA (coleta direta) + melhorias: Semaphore LLM (máx 5), alerta de cota (>20% fallback), logging estruturado |
| vendor | `predictor_core` da época do merge | **mais novo**: stats descarta reamostras não-finitas no bootstrap + aviso de subconjunto condicionado |
| Testes | 113 verdes | 80 verdes + 1 skip |
| Dados | `output/feature_store.db` (ignorado) | `data/` 130MB brutos (agora ignorado) |

## 2. Colisões e resoluções (decisões propostas)

| # | Colisão | Resolução | Racional |
|---|---------|-----------|----------|
| R1 | `core/` × `store/` (rename) | **`core/` vence** (com Fonte). Imports da V3 (`store.*` → `core.*`) repontados; `store/` morre | Rename é cosmético; `core/` carrega o carimbo Fonte (obrigatório pós-equivalência) e é referenciado por DPL/docs/ADRs |
| R2 | `main.py` (3 vias) | **Base = linha principal** (DPL+discover). Melhorias da V3 (Semaphore, alerta de cota, logging) re-enxertadas como commits separados | Mesmo princípio do ADR D3: base = linha com mais estrutura; enxerto do que agrega |
| R3 | vendor `predictor_core` | **V3 vence** (é sync mais novo do core canônico). Suíte da linha principal re-executada sobre ele antes de aceitar | Vendor não se edita local; versão mais nova = verdade do core. Melhorias do stats são desejáveis (bootstrap robusto) |
| R4 | `ai_insights/config/reporter` divergentes | Diff a diff no merge; default = linha principal, mudanças V3 avaliadas individualmente | Volume pequeno; decisão caso a caso é barata |
| R5 | Coleta V3 (funding/OI/vision) fora da DPL | **Fase 2 da reconciliação** (não bloqueia): collectors V3 viram providers da DPL (`SignalPoint` p/ funding/OI com `published_at` no FIM da janela de 8h) e materializam na Feature Store | É a convergência arquitetural correta, mas exige desenho próprio (bitemporal do funding) — não misturar com o merge mecânico |
| R6 | Testes V3 (`test_history`, `test_cache`, `test_backtest` novos) | Repontar imports para `core/`; rodar junto com os 113. Sem colisão de nomes de arquivo detectada | Soma esperada ≈ 113 + 81 − duplicatas de fixture (verificar no ato) |

## 3. Ordem de execução (cada etapa = commit próprio, suíte verde antes do próximo)

1. **[nesta branch] Passo 4.2-4.4** — Feature Store vira histórico oficial (independe da V3).
2. **Auditoria do HMM na `v3-quant-wip`** (passo 5.1) — teste de truncamento + doc; independe do merge.
3. **Merge mecânico** `v3-quant-wip` → branch de integração (`claude/reconcile-v3`): resolver R1-R4, suíte combinada verde (~190 testes).
4. **Re-enxertos** (R2: Semaphore/cota/logging na análise; commits pequenos).
5. **Fase 2 (R5)** — collectors V3 → providers DPL; `backtest_v3` lê da Feature Store; custos (passo 5.2) entram AQUI, sobre a V3 já reconciliada.
6. **Promoção a `main`** — só após 1-5 verdes; `main` recebe o resultado reconciliado (hoje segue intacta em `a78580c`).

## 4. O que NÃO se perde (contabilidade de preservação)

- Histórico CSV: migrado à Feature Store com Fonte backfill (passo 4.2) **antes** do merge.
- 113 testes da principal + 81 da V3: critério de aceite do passo 3 é a soma verde.
- `data/` 130MB: fora do git (regenerável); `binance_vision.py` é o gerador.
- Nenhuma branch é apagada; `v3-quant-wip` permanece como registro do resgate.

## 5. Decisões tomadas (ADR informal)

1. Unificação em `core/` (com Fonte); `store/` aposentado por repontamento de imports.
2. `main.py`: base principal, melhorias V3 re-enxertadas separadamente.
3. Vendor: adota-se o da V3 (mais novo), com re-validação da suíte principal.
4. Coleta V3 → DPL é fase própria (R5), com funding/OI como `SignalPoint` bitemporal (`published_at` = fim da janela).
5. Custos de transação (passo 5.2) implementados sobre a V3 **pós**-reconciliação, não antes.
6. `main` só é promovida após reconciliação completa e suíte combinada verde.
