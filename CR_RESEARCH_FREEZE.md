# CR_RESEARCH_FREEZE — Manifesto de Congelamento Científico

> Gerado por auditoria de preservação (não é nova pesquisa). Baseado exclusivamente
> em artefatos reais do repositório `cripto-predictor` no commit corrente. Onde não
> há evidência no repo, o campo diz `UNKNOWN` em vez de supor.

```yaml
schema_version: cr-research-freeze/1
generated_at: 2026-09-02
updated_at: 2026-09-03  # segunda camada: verificação executável (não apenas leitura de código)
based_on_charter: charters/scientific_state.json (as_of_commit 9949b510586cafe08c11a4733c19ebf30edf253c)
core_version_pinned: predictor-core==3.0.0 (pyproject.toml + uv.lock, consistentes)

preservation_verification:
  # CR_PRESERVATION = UNKNOWN permanece UNKNOWN por desenho, não por falta de
  # tentativa. Resolvido nesta rodada (2026-09-03): o caminho real do único
  # ativo irreversível é resolvido via GarimpoInvestimentos/core/paths.py
  # (FEATURE_STORE_DB = DATA_DIR/output/feature_store.db, DATA_DIR via
  # platformdirs/env var). Neste sandbox (checkout git efêmero, sem vínculo
  # com a máquina de produção): DATA_DIR resolveu para
  # /root/.local/share/cripto-predictor e FEATURE_STORE_DB.exists() == False —
  # ou seja, este ambiente nunca teve o banco real, só bancos de teste
  # descartáveis em /tmp/pytest-of-root/*. Nenhuma variável de ambiente
  # presente aponta para storage externo. Isto é isolamento por desenho do
  # sandbox, não evidência de ausência de backup em produção.
  #
  # AÇÃO PENDENTE (só executável por quem tem acesso à máquina real de
  # produção, não por uma sessão de auditoria como esta):
  #   1. Na máquina onde GarimpoInvestimentos roda de verdade, confirmar o
  #      valor real de DATA_DIR (ou da env var que o platformdirs resolve).
  #   2. Rodar: python scripts/feature_store_backup.py --verify
  #      (o script já existe e tem lógica de integrity_check — só falta
  #      alguém com acesso ao ambiente real executá-lo).
  #   3. Confirmar se existe alguma cópia offsite (S3/disco separado/outra
  #      máquina) do backup gerado, ou configurar uma se não existir.
  #   4. Atualizar este campo com o resultado real (PASS + evidência, ou
  #      FAIL + plano de remediação).
  checked_at: "2026-09-03"
  resolved_production_path: "DATA_DIR/output/feature_store.db (via platformdirs — valor real depende da máquina de produção)"
  sandbox_has_real_db: false
  operational_cost_h6_binance_collection: UNKNOWN  # mesma limitação — requer acesso a billing/infra reais, não verificável do sandbox

harness_attestation:
  # scripts/attest_harness.py rodado de verdade em 2026-09-03 (não editado manualmente).
  # O atestado anterior (core_version=2.3.0, passed_at=2026-08-21) estava expirado
  # (expires_at=2026-08-28) e contra Core desatualizado — trocado por reemissão real.
  v3_judge:
    metric: psr
    core_version: "3.0.0"
    passed_at: "2026-09-03T00:45:53Z"
    expires_at: "2026-09-10T00:45:53Z"
    positive_control: GO (sinal plantado detectado — sensibilidade OK)
    negative_control: NO-GO em ruído puro (especificidade OK)
  phase1_judge:
    metric: spearman_ic
    core_version: "3.0.0"
    passed_at: "2026-09-03T00:45:43Z"
    expires_at: "2026-09-10T00:45:43Z"
    positive_control: VALIDADO (sinal plantado detectado)
    negative_control: RUIDO rejeitado (IC95 cruza zero)
  test_suite: "853 passed, 0 failed (uv run pytest tests/, all-extras, 2026-09-03)"
  # inclui: hash chain (tamper/append), DPL bitemporal (published_at>=timestamp,
  # rejeição de leitura antes do cutoff), PBO/CSCV (ruído->PBO alto, skill real->PBO baixo),
  # gate_power (UNDERPOWERED vs REFUTED distintos), no-lookahead do HMM V3.
  secret_scan: "scripts/scan_secrets.py — 0 findings (2026-09-03)"

active_hypotheses: []
# Nenhuma hipótese está ACTIVE/PENDING_SAMPLE para capital ou shadow.
# capital_authorized=false, leverage_authorized=false, llm_direct_trading_authorized=false
# (charters/scientific_state.json).

passive_observations:
  - id: H6
    trial: h6-sinal-invertido-d7
    status: COLLECTION_ONLY_IMMATURE (charters/scientific_state.json)
    gate: "n >= 30 (H6_MIN_N), IC95 do Spearman invertido não cruzando zero"
    last_recorded_state: "GarimpoInvestimentos/h6_status.json — observed_at 2026-08-24T07:01:23Z, n=0, veredito 'aguardando n>=30 (n=0)'"
    frozen_definition_hash: 5582ec23370e58ae0fe961d41a3127674c136027b28ec511034efb0bd99b9f0a (docs/H6_REFREEZE_2026-08-27.md)
    note: "n=0 na última leitura commitada é estado legítimo (nenhuma previsão maturou em D+7 até aquele ponto), não banco vazio. Estado atual real não verificável sem rodar o pipeline (fora de escopo desta auditoria)."
  - id: H6_binance_collection
    plan: observation_plans/binance_funding_oi_v1.yaml
    status: COLLECTION_ONLY (docs/COLLECTION_ONLY_OBSERVATION.md)
    authorizes: "nada — não autoriza capital, hipóteses, backtests, PENDING_SAMPLE, SHADOW ou GO"
    operational_cost: UNKNOWN (custo de operação contínua — infra/API — não quantificado em nenhum doc lido nesta auditoria)
  - id: H7
    status: REGISTERED_NOT_ACTIVATED (charters/scientific_state.json)
    note: "infraestrutura parcial implementada (DXYProvider/FRED, calendário FOMC); CPI/PPI vazios; nenhuma coleta real iniciada."

stopped_hypotheses:
  - id: H1
    trial: v3-hmm-funding-oi-fr90
    status: CLOSED_NO_GO
    result: "líquido de custos −0.09bps/sinal (BTC), PSR 0.445; ETH PSR 0.051; kelly-invariante"
    reanalysis: "confirmação independente 2026-07-09 (base estendida 2021→jul/2026): IC_lo Spearman −0.079, PSR sem sobreposição reprova 0/3 sub-séries"
  - id: H2
    trial: v3-hmm-funding-oi-fr21
    status: CLOSED_NO_GO
    result: "PSR 0.215, líquido −0.37bps/sinal, IC_lo −0.218"
  - id: H3
    trial: v3-hmm-funding-oi-fr90-h48
    status: CLOSED_NO_GO
    result: "horizonte 48h inverte o sinal bruto para negativo; líquido −0.75bps/sinal, PSR 0.192, MaxDD 50.3%"
  - id: H4
    trial: v2-dpl-gemini-h7
    status: CLOSED_INSUFFICIENT_SAMPLE
    result: "coleta interrompida em n=5 por decisão do dono (risco de estouro de cota Gemini); sem veredito estatístico"
  - id: H5
    trial: v2-dpl-multi-h7
    status: CLOSED_NO_GO
    result: "Spearman pooled −0.166 [IC95 −0.266; −0.057], n=440; DSR 0.00 vs corte 0.95; acurácia direcional 45.2%"
  - id: v1-direct-gemini-h7
    status: CLOSED (ancestral pré-protocolo, contabilizada em trials.json)
    result: "Sharpe −0.5733"
  frozen_families: [funding_oi_hmm_v3]

preserved_components:
  - GarimpoInvestimentos/dpl/* (Data Provenance Layer bitemporal — ADR-014)
  - GarimpoInvestimentos/dpl/hash_chain.py (cadeia SHA-256 tamper-evident do predictions_archive)
  - GarimpoInvestimentos/analyzers/pbo.py (PBO/CSCV — Bailey/Borwein/López de Prado/Zhu)
  - GarimpoInvestimentos/analyzers/gate_power.py (trava de poder estatístico do gate)
  - GarimpoInvestimentos/v3/costs.py (CostModel canônico para veredito científico — perp)
  - GarimpoInvestimentos/trading/cost_policy.py (roteamento canônico de modelo de custo por asset_class)
  - scripts/attest_harness.py (controle positivo/negativo do juiz V3 — ADR-015)
  - charters/*.json, observation_plans/*.yaml (charters de governança de coleta)
  - docs/ADR-014_modelo_bitemporal.md, docs/ADR-015_experiment_registry_e_trava_de_poder.md
  - docs/HYPOTHESES.md, docs/H5_ACOMPANHAMENTO_2026-07-25.md, docs/H6_REFREEZE_2026-08-27.md (trilha de pré-registro/veredito)
  - docs/EVIDENCE_REGISTRY.md (claims formais: CLAIM-CR-HMM/LLM/TREND/DPL/COSTS/H6)
  - docs/TRADING_LAYER_INVENTORY.md (classificação módulo a módulo de trading/)
  - scripts/check_reopen_dossier.py (gate técnico do bloco 19 — bloqueia reabertura de frozen_families sem dossiê completo)
  - tests/test_v3_wfa_purge_contract.py (prova por código o gap IS->PURGE->OOS do WFA)

archived_components:
  - GarimpoInvestimentos/trials.json (schema legado; ver seção Trial Migration — proposta migração não-destrutiva)
  - GarimpoInvestimentos/trading/costs.py (walk-the-book spot — explicitamente NÃO CALIBRADO para veredito; mantido só para simulação/auditoria)

reopen_policy: >
  Nenhuma das hipóteses CLOSED_NO_GO / CLOSED_INSUFFICIENT_SAMPLE pode ser reaberta ou
  reparametrizada silenciosamente (docs/HYPOTHESES.md, nota do charter). Qualquer variação
  materialmente nova de uma família fechada exige: (1) trial nova registrada em
  trials.json/registry ANTES de rodar, com critério de sucesso pré-definido; (2) atestado
  de poder válido (scripts/attest_harness.py, ADR-015); (3) dados coletados DEPOIS do
  registro — nunca reaproveitar observações já vistas de tentativas anteriores. H6 tem
  hash de definição congelado (docs/H6_REFREEZE_2026-08-27.md) verificável via
  `python -m scripts.freeze_h6_definition --check`.
```
