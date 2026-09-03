# Índice do Congelamento Científico — onde está cada coisa

> Ponto único de entrada para a auditoria de congelamento científico deste
> repositório. Escrito para sobreviver sem o histórico da conversa que o
> gerou — cada linha abaixo aponta para um arquivo real, commitado e
> mergeado no `main`, verificável por qualquer pessoa (ou sessão de IA
> futura) só com `git log` e `cat`.

## 1. Estado atual em uma frase

O `cripto-predictor` está **congelado cientificamente**: nenhuma hipótese
ativa busca alpha, todos os resultados negativos estão preservados como
ativo científico, e os componentes reutilizáveis estão classificados e
testados. Isto NÃO é um convite para reabrir pesquisa — ver `reopen_policy`
em `CR_RESEARCH_FREEZE.md` e o gate técnico em `scripts/check_reopen_dossier.py`.

## 2. O manifesto principal — comece por aqui

| Arquivo | O que contém |
|---|---|
| **`CR_RESEARCH_FREEZE.md`** (raiz) | O documento mestre. Hipóteses ativas (nenhuma), observações passivas (H6, H6_binance_collection, H7), hipóteses encerradas (H1-H5 + ancestral), componentes preservados/arquivados, inventário formal de componentes (REUSE/KEEP_DOMAIN_OWNED/ARCHIVE), atestado do harness, verificação de preservação (backup real, testado), auditoria de sweep, política de reabertura |

## 3. Governança e reabertura

| Arquivo | O que faz |
|---|---|
| `scripts/check_reopen_dossier.py` | Gate técnico executável — bloqueia reabertura de qualquer família em `frozen_families` (`charters/scientific_state.json`) sem um dossiê com os 6 campos exigidos. Testado contra a família HMM real (`funding_oi_hmm_v3`) — confirmado bloqueado sem dossiê |
| `tests/test_check_reopen_dossier.py` | 8 testes do gate acima |
| `charters/scientific_state.json` | Fonte de verdade sobre status de cada hipótese (H1-H7), `frozen_families`, autorizações de capital (todas `false`) |
| `docs/HYPOTHESES.md` | Histórico narrativo completo de cada hipótese |

## 4. Evidência formal (claims científicas)

| Arquivo | O que contém |
|---|---|
| `docs/EVIDENCE_REGISTRY.md` | 6 claims formais: `CLAIM-CR-HMM`, `CLAIM-CR-LLM`, `CLAIM-CR-TREND`, `CLAIM-CR-DPL`, `CLAIM-CR-COSTS`, `CLAIM-CR-H6` — cada uma com state/L/Q/evidence/limitations/reopen_conditions |
| `docs/case_studies/CASE-CR-001-custos-comem-sinal.md` | Caso: custos eliminam edge bruto aparente (família HMM) |
| `docs/case_studies/CASE-CR-002-llm-prospectivo-negativo.md` | Caso: LLM forecasting, resultado prospectivo negativo (H4/H5) |
| `docs/case_studies/CASE-CR-003-multiplas-hipoteses-sem-falso-vencedor.md` | Caso: 7 hipóteses testadas, nenhum falso vencedor promovido |
| `docs/case_studies/CASE-CR-004-bitemporalidade.md` | Caso: por que o modelo bitemporal previne lookahead bias |

## 5. Inventário de componentes reutilizáveis

| Arquivo | O que contém |
|---|---|
| `docs/TRADING_LAYER_INVENTORY.md` | Classificação módulo a módulo dos 12 arquivos de `GarimpoInvestimentos/trading/` |
| `CR_RESEARCH_FREEZE.md` (seção `component_inventory`) | DPL, hash chain, PBO, gate_power, CostModel, cost_policy, attest_harness — todos classificados `KEEP_DOMAIN_OWNED` (nenhum tem segundo consumidor real confirmado) |

## 6. Testes que provam os controles científicos por código (não por leitura)

| Arquivo | O que prova |
|---|---|
| `tests/test_hash_chain.py` | Hash chain detecta tamper e append legítimo |
| `tests/test_dpl*.py` | DPL bitemporal — `published_at >= timestamp`, rejeição pré-cutoff |
| `tests/test_pbo.py` | PBO/CSCV — ruído→PBO alto, skill real→PBO baixo |
| `tests/test_gate_power.py` | Distinção UNDERPOWERED vs REFUTED |
| `tests/test_v3_wfa_purge_contract.py` | Gap IS→PURGE→OOS do WFA nunca zera |
| `tests/test_permutation_placebo_control.py` | Controle de permutação sobre o juiz Fase1 (faltava, foi criado) |
| `tests/test_v3_hmm_no_lookahead.py` | HMM não vaza dado futuro |

**869 testes passam no total** (`uv run pytest tests/`), lint limpo (`ruff check . && ruff format --check .`), confirmado no `main` no momento em que este índice foi escrito.

## 7. Preservação de dados (o ativo irreversível)

| O quê | Onde / status |
|---|---|
| Banco real (produção) | `C:\predictor\data\output\feature_store.db` (máquina do dono, fora deste repo) |
| Backup offsite | OneDrive (`cripto-predictor-backups`), hash sha256 verificado |
| Recorrência automática | Task Scheduler do Windows: `cripto-backup-featurestore` (domingo 20h) + `cripto-backup-mirror-onedrive` (domingo 20h30), ambas testadas com disparo manual |
| Script de backup/verify | `scripts/feature_store_backup.py` (`create`/`verify`/`restore`) |
| Snapshot de estado H6 | `GarimpoInvestimentos/h6_status.json` — última leitura real: `n=84`, `INCONCLUSIVE` (IC cruza zero), 2026-09-03 |

## 8. Harness / atestado

| Arquivo | O que contém |
|---|---|
| `scripts/attest_harness.py` | Reemite o atestado de controle positivo/negativo dos 2 juízes (V3/PSR, Fase1/Spearman) |
| `GarimpoInvestimentos/trials.harness_attestation.json` | Atestado real, `core_version: 3.0.0`, reemitido nesta rodada (não editado manualmente) |
| `GarimpoInvestimentos/trials.phase1_harness_attestation.json` | Idem, juiz Fase1 |

## 9. Segurança

| O quê | Status |
|---|---|
| `scripts/scan_secrets.py` | 0 achados no working tree no momento da auditoria |
| Incidente SerpAPI (`docs/SECURITY_INCIDENT_SERPAPI.md`) | 5 chaves rotacionadas, confirmado pelo dono |
| `COINGECKO_API_KEY` | Bug de wiring corrigido (lida via `os.getenv()`, precisa ser variável de ambiente real do Windows, não só `.env`) — mesma classe de bug do `DATA_DIR` |

## 10. Histórico completo de PRs desta auditoria (todos mergeados)

| PR | Título |
|---|---|
| #67 | Manifesto inicial, migração de trials, 2 case studies |
| #68 | Segunda camada: harness real, 853 testes, secret scan |
| #69 | Evidence Registry, inventário trading/, prova WFA, gate de reabertura |
| #70 | Documentação honesta dos gaps restantes |
| #71 | `CR_PRESERVATION = PASS` verificado na máquina real |
| #72 | Backup automatizado e testado |
| #73 | Descartado banco de produção paralelo/oculto |
| #74 | Correção de gaps do red-team (reuse rule, sweep count, permutação) |
| #75 | H6 evidence update real (`n=84`, `INCONCLUSIVE`) |
| #76 | Custo operacional Binance quantificado ($0/mês) |

## 11. Se uma sessão futura (IA ou humana) reabrir este repo

**Leia `CR_RESEARCH_FREEZE.md` inteiro antes de fazer qualquer coisa.**
Não crie hipótese nova. Não adicione feature. Não "melhore" resultado.
Se quiser reabrir uma família fechada, rode
`python -m scripts.check_reopen_dossier --family <nome> --dossier <caminho>`
— sem dossiê completo, o script bloqueia com exit code 1.
