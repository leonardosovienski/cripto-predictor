# ADR-015 — Experiment Registry canônico no core + trava de poder (harness ↔ registry)

Data: 2026-07-09 · Status: **aceito e implementado** (core v1.1.0, commits
`9af9702` no predictor_core e `0ace288` aqui) · Precedente: ADR-014 (bitemporal).

## Contexto

O Experiment Registry nasceu neste domínio (`analyzers/trials.py`, jul/2026) como
candidato a promoção ao `predictor_core`. Uma versão inicial foi promovida ao core,
mas o consumidor **nunca migrou o import** — e a cópia local continuou evoluindo
(schema formal `validate_trials`, governança N+1). Resultado, pego pela
meta-auditoria de 2026-07-09: **duas réguas de governança anti-data-snooping na
mesma plataforma**, sendo a canônica a mais fraca e a não-usada. É exatamente o
drift que o `sync_core` existe para impedir — só que dentro de casa.

Segundo problema, correlato: o `testing/harness.py` do core (controle positivo —
o pipeline detecta edge plantado? rejeita ruído?) tinha **zero consumidores**. Um
registro de tentativas sem prova de poder governa vereditos de um juiz que pode
ser cego: NO-GO ininterpretável.

## Decisão

1. **A versão evoluída daqui virou a canônica** (`predictor_core/measurement/
   trials.py`, v1.1.0): `validate_trials` (schema com campos obrigatórios e
   opcionais tipados), `register_trial` com governança N+1 (mudar `params` de
   trial existente é `ValueError` — variação de configuração é tentativa nova),
   `TrialRegistry.validate()`. Direção da reconciliação: **consumidor → core**
   (a implementação testada em uso vence a especulativa).
2. **`analyzers/trials.py` virou compat shim** (mesmo padrão dos shims do
   circuit_breaker da Onda 3), preservando o default histórico do `TRIALS_PATH`
   (trials.json versionado dentro do pacote).
3. **`close_trial_sharpes` NÃO subiu ao core**: é lógica de domínio (estratos de
   Fonte, limiar de score, colunas `var_d*`). Permanece em `analyzers/backtest.py`
   consumindo o `register_trial` canônico. Regra reafirmada: o core fornece a
   régua, nunca a decisão de domínio.
4. **Trava de poder**: criar trial NOVA exige um ATESTADO de controle positivo —
   arquivo irmão `<trials>.harness_attestation.json`, emitido por
   `testing.harness.attest_pipeline_power` (roda o controle; reprovou → não
   grava). Atualizar `sharpe`/`notes` de trial existente NÃO exige (a maturação
   automática do backtest não pode depender de o harness ter rodado na mesma
   máquina). Bypass explícito `power_attestation=False` existe SOMENTE para
   testes de mecânica do registro.

## Alternativa rejeitada

Flag booleano em memória (proposta original do plano): o harness roda na suíte de
testes e o `register_trial` roda no pipeline diário — **processos distintos**; um
flag de módulo jamais estaria levantado em produção e quebraria o fluxo de
maturação. Atestado em arquivo é verificável entre processos, versionável e
auditável (quem emitiu, quando, com que braços).

## Implementação do atestado neste domínio

`scripts/attest_harness.py` certifica o **juiz real** do V3 — os critérios
PSR ≥ 0,80 ∧ IC_lower > 0 do `backtest_v3` — contra série com skill plantado
(exige GO) e ruído puro (exige NO-GO), determinístico por seed. Substitui a
validação ad-hoc de jun/2026 ("NO-GO correto em ruído"). O atestado emitido é
versionado ao lado do trials.json. Corolário registrado: o NO-GO da H1 na base
estendida (2026-07-09) é veredito de um juiz **com poder comprovado**, não
cegueira.

## Consequências

- Fim do drift: uma régua, no core, sob hash do sync (`--check` 3/3).
- Toda trial nova daqui em diante carrega, por construção, a prova de que o
  pipeline que a julgará tem sensibilidade e especificidade.
- O wc-predictor adotará o mesmo contrato (registry + harness com edge sintético
  de apostas) antes da próxima melhoria de modelo (pós-Copa) — a trava o obriga a
  construir o controle positivo ANTES da primeira tentativa registrada.
- Custo assumido: chamadas de criação em testes precisam do bypass explícito;
  o atestado precisa ser re-emitido se o juiz mudar (feature, não bug).
