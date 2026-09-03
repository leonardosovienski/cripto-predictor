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
  # CR_PRESERVATION = PASS. Fechado em 2026-09-03 pelo dono do projeto na
  # máquina de produção real (Windows), com orientação desta sessão de
  # auditoria — a sessão de auditoria (sandbox Linux efêmero) não tem acesso
  # a essa máquina; os comandos abaixo foram executados e o output colado
  # de volta, não fabricados.
  #
  # 1. Caminho real confirmado: DATA_DIR = C:\predictor\data;
  #    FEATURE_STORE_DB = C:\predictor\data\output\feature_store.db,
  #    .exists() == True (6 291 456 bytes em 2026-09-03).
  # 2. Nenhum backup existia antes desta rodada (pasta DATA_DIR/backups
  #    estava vazia/ausente) — CR_PRESERVATION teria sido FAIL até este
  #    passo, não apenas UNKNOWN.
  # 3. Dois backups criados via `scripts/feature_store_backup.py create`,
  #    destino OneDrive (offsite real — sobrevive a perda física da máquina,
  #    diferente do disco C: ou de um segundo disco local como E:):
  #      C:\Users\Superleo13\OneDrive\cripto-predictor-backups\fs-2026-09-03-030150
  #      C:\Users\Superleo13\OneDrive\cripto-predictor-backups\fs-2026-09-03-000154
  # 4. Integridade verificada via `scripts/feature_store_backup.py verify`
  #    contra o primeiro backup — resultado real:
  #      sha256: 101303bc4d6f0b7140d4f8f01b2100ebabfa2c92eb3b2dee4d8e19e1923d2f3b
  #      size_bytes: 6291456
  #      verified: true
  # 5. Achado colateral: existiam backups locais antigos (mesmo disco C:,
  #    não offsite) em C:\predictor\data\output\feature_store_backup_antes_limpeza.db
  #    (1.28GB, 2026-08-09) e em C:\predictor\data\failed-runs\*.db — não
  #    apagados, preservados como histórico, mas não contam como cópia
  #    offsite.
  # 6. Achado colateral #2: a mesma máquina tinha uma branch git local
  #    (claude/entender-3-projetos-cfvrck) com 3 commits nunca enviados ao
  #    GitHub (upstream deletado) — trabalho de migração do DXYProvider
  #    stooq.com->FRED. Preservada em
  #    claude/entender-3-projetos-cfvrck-backup-2026-09-03 antes de qualquer
  #    resolução. Comparação mostrou que o main já tinha uma versão mais
  #    recente e validada ao vivo do mesmo fix (2026-08-31) — o trabalho
  #    local ficou redundante, não foi perdido nem precisou de PR novo.
  #
  # Recorrência (fechada em 2026-09-03, mesma sessão): duas tarefas
  # registradas no Task Scheduler dessa máquina, ambas testadas com
  # `Start-ScheduledTask` (não apenas registradas — disparadas manualmente e
  # confirmadas antes de considerar OK):
  #   1. cripto-backup-featurestore (scripts/register_task_backup.ps1) —
  #      domingos 20:00, roda `python -m GarimpoInvestimentos.jobs backup`
  #      (create --output-root, destino DATA_DIR/backups, local). Testada:
  #      LastTaskResult=0.
  #   2. cripto-backup-mirror-onedrive (criada ad-hoc nesta sessão, robocopy
  #      /MIR de DATA_DIR/backups para OneDrive\cripto-predictor-backups) —
  #      domingos 20:30, 30 min depois da tarefa 1. Testada duas vezes:
  #      primeira rodada copiou (LastTaskResult=1, que no robocopy É sucesso
  #      — "arquivos copiados", não erro; só 0 = "nada novo" e >=8 seriam
  #      erro real), segunda rodada confirmou nada pendente (LastTaskResult=0).
  #      Confirmado por Get-ChildItem: as pastas fs-2026-09-03-034452 e
  #      fs-2026-09-03-034723 (geradas pela tarefa 1) já apareceram
  #      espelhadas no OneDrive depois da tarefa 2 rodar.
  # Backup agora é automático E offsite, não apenas um snapshot manual pontual.
  checked_at: "2026-09-03"
  resolved_production_path: "C:\\predictor\\data\\output\\feature_store.db"
  sandbox_has_real_db: false  # continua false no sandbox de auditoria; true na máquina real
  offsite_backup_verified: true
  offsite_backup_sha256: "101303bc4d6f0b7140d4f8f01b2100ebabfa2c92eb3b2dee4d8e19e1923d2f3b"
  offsite_backup_recurrence: automated  # cripto-backup-featurestore + cripto-backup-mirror-onedrive, testadas e Ready
  #
  # Investigação adicional (2026-09-03, mesmo dia): confirmado que a máquina
  # tem MÚLTIPLOS diretórios do projeto (checkout de auditoria em
  # C:\Users\Superleo13\cripto-predictor; deploy real de produção em
  # C:\predictor\prod\GarimpoInvestimentos, com seu próprio .venv e .env;
  # e um caminho legado C:\Claude-projetos\...\previsao-cripto referenciado
  # só pela tarefa `GarimpoInvestimentos-ColetaDiaria`, que está Disabled —
  # provavelmente superada por GarimpoFase1/GarimpoV3Daily, que estão Ready
  # e apontam para C:\predictor\prod). O .env de produção declara
  # `DATA_DIR=data` (relativo), o que levantou a hipótese de um segundo
  # feature_store.db em C:\predictor\prod\data. Investigado e descartado
  # com evidência, não suposição:
  #   1. C:\predictor\prod\data\output\feature_store.db NÃO existe
  #      (Get-Item retornou vazio).
  #   2. GarimpoInvestimentos/core/paths.py lê DATA_DIR via os.getenv()
  #      direto — não via o carregamento de .env do pydantic-settings usado
  #      em config.py — então o DATA_DIR=data do arquivo .env nunca chega a
  #      ser efetivamente lido por essa função; é configuração mortas/sem
  #      efeito, não um bug ativo.
  #   3. Confirmado que existe uma variável de ambiente real do Windows
  #      (User e Machine) DATA_DIR=C:\predictor\data — essa sim é a que
  #      core/paths.py de fato usa, e bate exatamente com o caminho já
  #      verificado, backupeado e testado nesta auditoria.
  # Conclusão: não existe banco de produção paralelo/escondido. O
  # feature_store.db verificado é o único real.
  operational_cost_h6_binance_collection:
    monetary_cost_usd_per_month: 0.00
    # Contagem real, não estimativa por cima, derivada de
    # observation_plans/binance_funding_oi_v1.yaml + collectors/*.py:
    #   funding_rate: cadence_seconds=28800 (8h) x 2 instrumentos = 6 req/dia
    #   open_interest: cadence_seconds=3600 (1h) x 2 instrumentos = 48 req/dia
    #   total: ~54 req/dia no endpoint público fapi.binance.com
    # GarimpoInvestimentos/v3/collectors/funding_collector.py:37 documenta
    # explicitamente: "Binance free tier (2400 req/min para dados públicos)"
    # — sem API key, sem tier pago. 54 req/dia é ~0.04% do limite gratuito
    # de 2400/min; não existe cobrança da Binance nesse volume.
    infra_cost: none_dedicated
    # A máquina onde roda (C:\predictor\prod) é PC pessoal do dono (Windows,
    # apps pessoais instalados — não é VPS/cloud dedicada). Nenhum custo de
    # hospedagem é atribuível especificamente a esta coleta.
    unquantified: [eletricidade marginal, uptime real do PC]
    # Não verificável sem dados que só o dono tem (fatura de energia,
    # disponibilidade real da máquina) — não fabricado.
    non_monetary_risk: >
      Custo real não é financeiro, é de disponibilidade: se o PC estiver
      desligado no horário agendado, a coleta simplesmente não roda naquele
      ciclo (mesmo risco já documentado para os backups do feature_store.db).
    fully_automatic: true
    financial_cost: negligible
    security_risk: low
    maintenance_burden: negligible
    conclusion: satisfaz a regra do bloco 17 (custo ≈ zero) — mantido como coleta passiva

sweep_count_audit:
  # Red-team pass (bloco 29, "Trials — algum sweep não foi contado?").
  # docs/ARQUITETURA_CONSOLIDADA.md documenta um kelly-sweep de 4 avaliações
  # (gate de drawdown) por trás do GO histórico de 27/06 (PSR 0.909) da
  # família H1 — esse sweep NÃO tem entrada própria em trials.json (7
  # entradas totais, nenhuma nomeada "kelly-sweep").
  # Risco avaliado: BAIXO. O GO de 27/06 já foi invalidado pelo veredito
  # oficial NO-GO de 02/07 (com custos completos) — viés de seleção infla
  # resultado aparentemente POSITIVO, e o resultado que sobreviveu é
  # negativo. Não contar o sweep não gera falso-positivo aqui.
  # Ação: NÃO foi criada entrada nova em trials.json para o sweep — isso
  # exigiria reconstruir os 4 valores de kelly testados sem registro formal
  # original, o que seria inventar proveniência, não preservá-la. Registrado
  # aqui como lacuna de contagem conhecida, não corrigido retroativamente.
  kelly_sweep_evaluations_undocumented_as_trial: 4
  associated_result: "GO 27/06 pré-custos, já superado por NO-GO oficial 02/07"
  false_positive_risk: low
  correction_applied: none  # decisão deliberada — ver nota acima

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
    status: COLLECTION_ONLY_IMMATURE (charters/scientific_state.json — NÃO alterado; ver nota)
    gate: "n >= 30 (H6_MIN_N), IC95 do Spearman invertido não cruzando zero"
    last_recorded_state: "GarimpoInvestimentos/h6_status.json — observed_at 2026-09-03T05:55:26Z, n=84, rho=-0.057, IC95%[-0.231, +0.129], gate_atingido=true, veredito 'RUIDO (IC cruza 0)'"
    frozen_definition_hash: 5582ec23370e58ae0fe961d41a3127674c136027b28ec511034efb0bd99b9f0a (docs/H6_REFREEZE_2026-08-27.md)
    evidence_update_2026-09-03: >
      Rodada real de quality_snapshot.py na máquina de produção (C:\predictor\prod),
      após corrigir dois bugs de wiring de env var (DATA_DIR e COINGECKO_API_KEY
      lidos via os.getenv() direto, não pelo loader de .env — mesma classe de bug
      nos dois casos, corrigida via variável de ambiente real do Windows, não via
      alteração de código). n cruzou o gate de 30 pela primeira vez (n=84). Sob o
      esquema de 3 estados de docs/H6_REFREEZE_2026-08-27.md (VALIDATED se IC_lower>0,
      REFUTED se IC_upper<0, INCONCLUSIVE se IC cruza zero OU amostra insuficiente),
      este resultado é INCONCLUSIVE — o IC cruza zero. A tabela de poder do próprio
      h6_status.json mostra poder=23% para rho=0.2 em n=84: mesmo tendo passado do
      gate operacional de 30, a amostra segue subdimensionada para um efeito
      pequeno-a-moderado. Por isso NÃO foi promovido a CLOSED_NO_GO/REFUTED — isso
      seria o mesmo erro que o bloco 16 do congelamento científico pede para evitar
      (confundir NO-GO com UNDERPOWERED). H6 continua COLLECTION_ONLY (charter não
      alterado); isto é um evidence update dentro do protocolo já registrado, não
      reabertura nem novo ciclo de otimização (bloco 18).
    note: "n=0 na leitura anterior (24/08) era estado legítimo, não banco vazio — confirmado agora que o pipeline voltou a rodar."
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

component_inventory:
  # Bloco 21-22 do congelamento científico. Regra de promoção (bloco 22):
  # REUSE só quando second_real_consumer=yes ou justificativa arquitetural
  # concreta; caso contrário KEEP_DOMAIN_OWNED, mesmo que o componente seja
  # tecnicamente genérico o bastante para servir outro domínio.
  #
  # Correção 2026-09-03: um red-team pass (bloco 29) encontrou que DPL,
  # hash_chain, PBO e gate_power tinham sido rotulados REUSE em respostas de
  # chat anteriores desta sessão SEM nenhum segundo consumidor real
  # confirmado — violação direta da própria regra do bloco 22. Corrigido
  # para KEEP_DOMAIN_OWNED nos quatro; nenhum tem consumer_count > 1
  # verificado.
  - component: GarimpoInvestimentos/dpl/* (Data Provenance Layer bitemporal)
    tested: true
    domain_specific: false  # mecanismo é genérico, não amarrado a cripto
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
    note: candidato natural a REUSE se outro domínio adotar o mesmo mecanismo; não verificado
  - component: GarimpoInvestimentos/dpl/hash_chain.py
    tested: true
    domain_specific: false
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: GarimpoInvestimentos/analyzers/pbo.py (PBO/CSCV)
    tested: true
    domain_specific: false
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: GarimpoInvestimentos/analyzers/gate_power.py
    tested: true
    domain_specific: false
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: GarimpoInvestimentos/v3/costs.py (CostModel perp)
    tested: true
    domain_specific: true  # funding rate só existe em perp
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: GarimpoInvestimentos/trading/cost_policy.py
    tested: true
    domain_specific: false
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: scripts/attest_harness.py
    tested: true
    domain_specific: true  # juízes específicos (V3/Fase1), padrão é genérico
    consumer_count: 1
    second_real_consumer: false
    decision: KEEP_DOMAIN_OWNED
  - component: GarimpoInvestimentos/trials.json (schema legado)
    tested: false
    domain_specific: true
    consumer_count: 1
    second_real_consumer: false
    decision: ARCHIVE
  - component: GarimpoInvestimentos/trading/costs.py (walk-the-book spot)
    tested: true
    domain_specific: true
    consumer_count: 1
    second_real_consumer: false
    decision: ARCHIVE
    note: NAO CALIBRADO, bloqueado por UncalibratedCostModel

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
  - tests/test_permutation_placebo_control.py (bloco 11 — controle de permutação sobre o juiz da Fase 1, faltava)

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
