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
4. Menores: rotação de chaves (proprietário), ~~C-03 (consenso ao vivo)~~,
   ~~equivalência ETH/SOL~~ (ambos fechados em 2026-09-04, ver §10.2), ADR-015
   (proveniência com hash), CI.

## 8. Declaração de fechamento

O projeto está **pronto e resolvido no estado atual de pesquisa**: todas as
verificações passando (329 testes verdes no ecossistema), documentação fiel ao
código, histórico oficial na Feature Store com carimbos, veredito estatístico
registrado com governança completa. **Sem recomendação para capital real** — a
infraestrutura está pronta; o edge, comprovadamente, ainda não existe.

> Este relatório é um retrato histórico de 2026-07-02 e permanece intocado como
> registro. O fechamento da auditoria/remediação (2026-08-19) está na seção 9
> abaixo, e a reconciliação das pendências das seções 5 e 7 (2026-08-21) na
> seção 10 — nenhuma das duas substitui os itens acima; complementam.

## 9. Fechamento de auditoria e remediação — 2026-08-19

**Método:** mesma disciplina do relatório original — cada item conferido no
repositório (código, testes, `git log`/`git diff` pós-push), nunca na memória
da conversa. Rodada de fechamento após várias rodadas anteriores de auditoria
forense (H5, H6, V3/HMM, pipeline, segurança) documentadas nas conversas e nos
commits desde `acc9f2a`.

**Gaps reais encontrados e corrigidos nesta rodada** (nenhum era cosmético):
1. Migração `_0016_predictions_append_only` não tinha teste para (a) um banco
   criado ANTES de 0016 existir com `predictions` já populada, nem (b) uma
   migração interrompida no meio. Ambos os cenários agora têm teste dedicado
   em `tests/test_predictions_append_only.py` (7/7 passam).
2. `h6_spearman_verdict()` — o gate anti-data-snooping oficial da H6 — nunca
   teve teste direto provando que `pred_date > registered_at` e
   `fonte == H6_LIVE_FONTE` realmente excluem previsões pré-registro/de outra
   fonte do `n`. Adicionado em `tests/test_h6_spearman_verdict_eligibility.py`
   (5/5 passam): pré-registro não conta, fonte errada não conta, elegível
   conta, mistura conta só os elegíveis, ausência da H6 é no-op.
3. `docs/SECURITY_INCIDENT_SERPAPI.md` reconciliado: as 5 chaves expostas em
   texto puro durante depuração ao vivo desta auditoria foram rotacionadas
   (confirmado diretamente pelo dono do repositório em produção). Registrado
   como adendo, sem apagar o estado original `BLOCKED_PENDING_SECRET_ROTATION`.

**Mapeamento H1–H7 → trial real, verificado literalmente em `docs/HYPOTHESES.md`
(não por inferência):**

```
H1 -> v3-hmm-funding-oi-fr90        (HYPOTHESES.md:21, "Configuração:")
H2 -> v3-hmm-funding-oi-fr21        (HYPOTHESES.md:39)
H3 -> v3-hmm-funding-oi-fr90-h48    (HYPOTHESES.md:47)
H4 -> v2-dpl-gemini-h7              (HYPOTHESES.md:60)
H5 -> v2-dpl-multi-h7               (HYPOTHESES.md:79)
H6 -> h6-sinal-invertido-d7         (HYPOTHESES.md:132)
H7 -> não registrada em trials.json (HYPOTHESES.md:199 — infra pronta, coleta não iniciada)
```

`v1-direct-gemini-h7` não tem cabeçalho `### H<N>` em `HYPOTHESES.md` — é o
ancestral pré-protocolo da linha LLM, sem rótulo formal (só entra no
denominador de trials para o DSR). O mapeamento vive em
`charters/scientific_state.json` (`hypothesis_trials`) e é travado por
`tests/test_scientific_state_charter.py`.

**Estado canônico final:**

```
AUDIT_AND_REMEDIATION = CLOSED
KNOWN_BLOCKING_CODE_BUGS = NONE
TEST_SUITE = PASS (616/616, 0 skipped)
CURRENT_PROJECT_MODE = PROSPECTIVE_OBSERVATION

H1/H2/H3 (HMM): TEMPORAL_VALIDITY=PASS, LEAKAGE=NOT_FOUND,
                 ECONOMIC_EDGE=NO_GO, FAMILY_STATUS=FROZEN
H4 = CLOSED_INSUFFICIENT_SAMPLE
H5 = CLOSED_NO_GO
     H5_POSITIVE_EDGE=REJECTED, H5_NEGATIVE_RELATION=WEAK_HISTORICAL_EVIDENCE
     H5_RAW_DATA=LOST, H5_RETROSPECTIVE_REANALYSIS=NOT_REPRODUCIBLE
     H5_HISTORICAL_CI=METHODOLOGICALLY_LIMITED (bootstrap sem overlap-aware
     block_length na época; não reescrito, só qualificado)
H6 = ACTIVE_PROSPECTIVE / IMMATURE
     H6_SCIENTIFIC_INTEGRITY=PASS, H6_DEFINITION=FROZEN (hash verificável)
     SANDBOX_H6_VALID_N=0 (ambiente de auditoria sem banco de produção)
     PRODUCTION_H6_N=NOT_VERIFIED_IN_THIS_ENVIRONMENT — n real fica no
     feature_store.db de produção, não neste sandbox
H7 = REGISTERED_NOT_ACTIVATED

DATA_INTEGRITY=HIGH, ENGINEERING_QUALITY=HIGH, OBSERVABILITY=HIGH
CURRENT_RESEARCH_RIGOR=HIGH (pré-registro, hash, append-only, DELETE
     bloqueado, bootstrap overlap-aware, testes causais, watchdog,
     quality_snapshot, emendas históricas versionadas)
HISTORICAL_REPRODUCIBILITY=LIMITED (perda dos dados brutos da H5)
CURRENT_PREDICTIVE_QUALITY=NOT_YET_MEASURABLE (coorte H6 ainda imatura)
HISTORICAL_ECONOMIC_RESULTS=NO_GO (H1-H3, H5)
CURRENT_H6_ECONOMIC_EDGE=NOT_YET_MEASURABLE

OFFLINE_SMOKE=PASS (main.run() ingest→analysis→persistence via
     tests/test_run_redoma.py + 43 testes de integração por estágio)
LIVE_PRODUCTION_SMOKE=NOT_EXECUTED_IN_SANDBOX

SECURITY_CODE_BLOCKER=NONE
SECURITY_NEW_KEYS_ROTATED=YES (confirmado pelo dono)
SECURITY_OLD_KEYS_REVOKED=UNVERIFIED
SECURITY_EXTERNAL_ACTION=VERIFY_OLD_KEY_REVOCATION

LIVE_CAPITAL=FORBIDDEN
```

**Decisão:** `AUDIT_AND_REMEDIATION = CLOSED`. Nenhum blocker de código
restante. H6 segue congelada e protegida — sua maturação real depende do
`feature_store.db` de produção, não deste ambiente de auditoria. Próximo
passo é observação prospectiva (coleta → watchdog → `quality_snapshot`),
não nova auditoria.



## 10. Reconciliação de pendências — 2026-08-21

**Escopo desta seção.** As seções 1-8 são o retrato de 2026-07-02 e a seção 9 é o
fechamento de auditoria de 2026-08-19; ambas permanecem intocadas. A §9 tratou de
integridade científica e blockers de código — não passou pelas **listas de pendência**
da §5 (matriz de riscos) e da §7 (próximos passos), que continuaram descrevendo um
repositório de várias branches com CI inexistente. Esta seção fecha essa lacuna,
item a item, com a evidência de cada verificação. Índice geral das divergências dos
documentos datados: [ERRATA_2026-08-21.md](ERRATA_2026-08-21.md).

### 10.1 Itens da §5 e da §7 — estado verificado

| Item (onde aparece) | Estado em 2026-08-21 | Evidência |
|---|---|---|
| "falta CI" (§5, mitigado 2; §7.4) | **fechado** | `.github/workflows/ci.yml`: quality (ruff + pyright + scan de segredos + build + pytest com cobertura + contract test das wheels instaladas fora do checkout), python-314-experimental, all-extras, container (SBOM + Trivy) |
| "falta ADR-015" / proveniência sem hash (§5, mitigado 1; §7.4) | **fechado** | migração `_0012_provenance_content_hash` + `content_hash` calculado em `ingest.py`; o ADR-015 registra status "aceito e implementado" |
| "rotação das chaves antigas — pendente desde 14/06" (§5, aberto 2; §7.4) | **rotacionado** | `ROTATED_CONFIRMED_BY_OWNER_2026-08-19`; ver §9 e [SECURITY_INCIDENT_SERPAPI.md](SECURITY_INCIDENT_SERPAPI.md). Persiste apenas a verificação externa de revogação das chaves **antigas** |
| "aprovar a reconciliação V3 → promover a `main` (hoje intacta em `a78580c`)" (§7.1) | **executado** | `GarimpoInvestimentos/v3/` está na `main`; nenhuma das branches do plano existe ([RECONCILIACAO_V3.md](RECONCILIACAO_V3.md) traz errata) |
| "coleta diária até o backtest ter n (hoje: 4 previsões)" (§7.2) | **superado** | H5 fechou em 2026-07-28 com **n=440**: Spearman −0,166 [IC95 −0,266; −0,057], NO-GO. A coleta prospectiva atual serve à H6 |
| "pivot de pesquisa da V3" (§7.3) | **parcial** | a família `funding_oi_hmm_v3` está em `frozen_families` (charter); H6 e H7 nasceram registradas. Nenhuma hipótese nova validou edge |
| "C-03 — consenso ao vivo" (§7.4) | **fechado (2026-09-04)** | `python -m GarimpoInvestimentos.main --ingest --assets bitcoin --mode consensus` rodado na máquina de produção, com `ccxt` instalado (`uv sync --locked --extra v3`): "✅ BITCOIN — 199 candles alinhados e materializados" via consenso Binance+Kraken real, gravados em `feature_store.db`. Deixa de depender só de `test_dpl_aggregation.py` (sintético) — ver [AUDITORIA_DPL.md](AUDITORIA_DPL.md) C-03 |
| "equivalência ETH/SOL" (§7.4) | **fechado (2026-09-04)** | `python -m GarimpoInvestimentos.analyzers.equivalence --assets bitcoin,ethereum,solana` rodado na máquina de produção: "EQUIVALENTES em todos os ativos" (pior diff relativo 0.00e+00 nos três). Fecha a pendência aberta desde `6416a71` (bitcoin/kaspa/aave) |
| "regime shift em produção" (§5, aberto 1) | **aberto, irrelevante** | continua sem produção — nenhum capital autorizado |

### 10.2 Contagens de teste

A §2 tabula suítes por branch (118 / 87+2 / 85 / 39) e a §8 cita "329 testes verdes no
ecossistema". Todos esses números são de 2026-07-02 e das branches daquela data. A §9
já registra 616/616; verificado de novo em 2026-08-21:

| Comando | Resultado |
|---|---|
| `uv sync --locked --all-extras && uv build && uv run pytest -q` | **616 passed, 0 skipped** |
| `uv sync --locked --extra test && uv build && uv run pytest -q` | **601 passed, 2 skipped** (numpy e hmmlearn) |

### 10.3 O que a §6 e a §8 mantêm

O veredito estatístico da §6 (**NO-GO** com governança completa), a nota **6,0/10** e a
declaração da §8 — infraestrutura pronta, edge inexistente, **sem recomendação para
capital real** — continuam valendo integralmente. Nada nesta reconciliação altera
`trials.json`, gates, thresholds ou o estado científico das hipóteses; ver §9 para o
estado canônico de H1-H7 e [../README.md](../README.md) para o corrente.
