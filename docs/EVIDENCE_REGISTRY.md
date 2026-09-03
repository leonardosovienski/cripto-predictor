# Evidence Registry — claims científicas do `cripto-predictor`

> Registro formal (bloco 27 do congelamento científico). Cada claim é derivada
> exclusivamente de artefatos já existentes no repositório (trials.json,
> charters/scientific_state.json, docs/HYPOTHESES.md, resultados de teste
> executados nesta auditoria). Nenhum valor foi inventado; onde a evidência é
> insuficiente, o campo diz `UNKNOWN`.
>
> Campos: `state` (estado do claim), `L` (força do link causal alegado —
> qualitativo: fraco/moderado/forte), `Q` (qualidade da evidência —
> qualitativo: baixa/média/alta, baseada em: pré-registro? custos reais
> incluídos? reprodução independente?), `evidence`, `limitations`,
> `new_evidence?`, `decision`, `reopen_conditions`.

---

## CLAIM-CR-HMM
**Descrição:** HMM de regime + funding rate/Open Interest tem edge econômico
preditivo sobre BTC/ETH perp após custos.

- **state:** REFUTED
- **L:** fraco (nenhuma sub-série sobreviveu à reanálise independente)
- **Q:** alta (pré-registrado, custos reais via CostModel calibrado, WFA com
  purge, reanálise independente em base estendida)
- **evidence:** H1 (v3-hmm-funding-oi-fr90) CLOSED_NO_GO — líquido −0.09bps/sinal
  BTC, PSR 0.445; ETH PSR 0.051. H2 (fr21) CLOSED_NO_GO — PSR 0.215, líquido
  −0.37bps. H3 (fr90-h48) CLOSED_NO_GO — sinal bruto inverte para negativo no
  horizonte 48h, líquido −0.75bps, MaxDD 50.3%. Reanálise independente
  (2026-07-09, base 2021→jul/2026): IC_lo Spearman −0.079, PSR reprova 0/3
  sub-séries.
- **limitations:** universo testado é só BTC/ETH perp; não testado em altcoins
  nem em outros venues.
- **new_evidence?:** não, desde o fechamento.
- **decision:** família `funding_oi_hmm_v3` permanece `frozen_families`
  (charters/scientific_state.json). Tecnicamente bloqueada contra reabertura
  silenciosa por `scripts/check_reopen_dossier.py`.
- **reopen_conditions:** dossiê completo via `check_reopen_dossier.py`
  (previous_result, closure_reason, new_information, causal_reason,
  why_old_test_no_longer_answers_question, new_protocol) + atestado de poder
  válido (`scripts/attest_harness.py`).

---

## CLAIM-CR-LLM
**Descrição:** Previsão via LLM (Gemini/multi-judge) tem acurácia direcional
prospectiva acima do acaso.

- **state:** REFUTED (H5), INCONCLUSIVE_DUE_TO_POWER (H4)
- **L:** fraco
- **Q:** alta para H5 (n=440, prospectivo real, não retrospectivo); baixa para
  H4 (n=5, amostra insuficiente por decisão operacional, não por desenho)
- **evidence:** H5 (v2-dpl-multi-h7) CLOSED_NO_GO — Spearman pooled −0.166
  [IC95 −0.266; −0.057], n=440, DSR 0.00 vs corte 0.95, acurácia direcional
  45.2% (abaixo do acaso). H4 (v2-dpl-gemini-h7) CLOSED_INSUFFICIENT_SAMPLE —
  coleta interrompida em n=5 por risco de estouro de cota, sem veredito
  estatístico possível.
- **limitations:** H4 nunca teve poder suficiente para refutar nem confirmar
  nada — não deve ser lido como "LLM não funciona", só como "não foi possível
  testar".
- **new_evidence?:** não.
- **decision:** ambas encerradas. H5 é o resultado forte (negativo,
  bem-poderizado); H4 é inconclusivo por desenho interrompido, não por
  refutação.
- **reopen_conditions:** mesmas do CLAIM-CR-HMM (dossiê + atestado de poder).
  Para H4 especificamente, exigiria também resolver o risco operacional de
  cota da API que motivou a interrupção original.

---

## CLAIM-CR-TREND
**Descrição:** Trend-following / momentum / SMA200 tem edge sobre cripto
após custos.

- **state:** REFUTED (por decisão de escopo do dono, ver docs/HYPOTHESES.md —
  não há trial numerada dedicada em trials.json com o mesmo rigor de H1-H5)
- **L:** UNKNOWN — não há trial formal registrada com PSR/DSR para esta
  família especificamente nesta auditoria; a decisão de não promoção está
  documentada em `docs/HYPOTHESES.md`, não em `trials.json`.
- **Q:** UNKNOWN por falta de registro formal equivalente ao das famílias
  HMM/LLM.
- **evidence:** listada em `docs/HYPOTHESES.md` como família NO-GO / não
  promovida, junto com sweeps de sizing.
- **limitations:** esta auditoria não conseguiu localizar um registro de
  trial dedicado (metric/PSR/custo) para trend-following/momentum/SMA200 no
  mesmo formato de H1-H7 — a evidência é qualitativa (nota em docs), não
  quantitativa registrada em `trials.json`.
- **new_evidence?:** não.
- **decision:** mantida fechada por precaução (nenhuma promoção sem
  dossiê), mesmo com evidência formal mais fraca que HMM/LLM.
- **reopen_conditions:** mesmas do CLAIM-CR-HMM. Se a intenção for reabrir,
  o primeiro passo correto é REGISTRAR a trial retroativa com `UNKNOWN` nos
  campos não documentados (mesmo padrão do migrador de `trials.json`), não
  pular direto para uma trial nova.

---

## CLAIM-CR-DPL
**Descrição:** A Data Provenance Layer bitemporal previne lookahead bias por
construção (não apenas por convenção).

- **state:** SUPPORTED
- **L:** forte (invariante estrutural, não best-effort)
- **Q:** alta — testado com execução real nesta auditoria (não só leitura de
  código)
- **evidence:** ADR-014 (Aceita). Invariante `published_at >= timestamp`
  testado e passando (`test_marketdatapoint_rejeita_published_antes_do_timestamp`).
  Suíte completa de DPL executada nesta auditoria: 42 testes passando,
  incluindo hash chain (tamper/append), agregação por consenso, migrações
  idempotentes, revisões coexistindo sem sobrescrita.
- **limitations:** os testes cobrem o mecanismo em dados controlados/sintéticos
  de teste; não há, nesta auditoria, uma prova de que TODO consumidor real de
  dados (ex.: pipelines de coleta em produção) de fato só lê via o caminho que
  respeita `published_at`. Isso exigiria auditoria de cada call site, fora de
  escopo aqui.
- **new_evidence?:** sim — esta auditoria (2026-09-03) é a primeira a rodar
  os testes de verdade em vez de só ler o código.
- **decision:** classificado `KEEP_DOMAIN_OWNED` no inventário de componentes
  (ver `component_inventory` em `CR_RESEARCH_FREEZE.md`) — nenhum segundo
  consumidor real foi confirmado fora deste repositório, então a regra de
  promoção do bloco 22 não está satisfeita ainda. Candidato natural a `REUSE`
  se/quando um segundo domínio adotar o mesmo mecanismo — mas isso não foi
  verificado, só é plausível dado o desenho genérico do componente.
- **reopen_conditions:** N/A (claim de suporte, não hipótese fechada).

---

## CLAIM-CR-COSTS
**Descrição:** Ganhos brutos aparentes em backtests desaparecem quando custos
reais são aplicados (CostModel calibrado).

- **state:** SUPPORTED
- **L:** forte
- **Q:** alta — CostModel classificado `MEASURED/CALIBRATED` para perp (taker
  10bps + slippage 5bps/perna + funding real), testado nesta auditoria
  (`test_v3_costs.py`, 5/5 passando)
- **evidence:** H1 é o caso mais direto: sinal bruto existia, mas líquido de
  custos ficou negativo (−0.09bps BTC). `test_costs_turn_small_predictive_edge_into_no_trade`
  e `test_edge_menor_que_custo_vira_prejuizo_liquido` provam isso por código,
  não só por resultado histórico.
- **limitations:** modelo de custo para spot (`trading/costs.py`,
  walk-the-book) segue explicitamente NÃO CALIBRADO e bloqueado
  (`UncalibratedCostModel`) — não pode sustentar veredito algum.
- **new_evidence?:** não desde o fechamento de H1-H3.
- **decision:** CostModel perp preservado como ativo central do case
  científico (CASE-CR-001).
- **reopen_conditions:** N/A (claim de suporte).

---

## CLAIM-CR-H6
**Descrição:** Sinal invertido D+7 (H6) tem edge preditivo.

- **state:** INCONCLUSIVE_DUE_TO_POWER (gate operacional de n>=30 atingido em
  2026-09-03 com n=84, mas poder=23% para rho=0.2 na mesma amostra — não é
  REFUTED nem VALIDATED sob o esquema de 3 estados de
  `docs/H6_REFREEZE_2026-08-27.md`)
- **L:** fraco (rho=-0.057, IC95%[-0.231, +0.129] cruza zero)
- **Q:** média — n=84 real, prospectivo, mas subdimensionado para efeitos
  pequenos-a-moderados (tabela de poder do próprio `h6_status.json`)
- **evidence:** `GarimpoInvestimentos/h6_status.json` — rodada real de
  `quality_snapshot.py` em 2026-09-03T05:55:26Z na máquina de produção
  (`C:\predictor\prod`), n=84, gate_atingido=true, veredito "RUIDO (IC cruza
  0)". `charters/scientific_state.json` continua `COLLECTION_ONLY_IMMATURE`
  — não alterado, ver decision abaixo.
- **limitations:** poder de 23% (rho=0.2) e 47% (rho=0.3) em n=84 — mesmo
  cruzando o gate de 30, a amostra não é adequada para descartar um efeito
  real pequeno-a-moderado. Distinguir isso de refutação é exatamente o que o
  bloco 16 do congelamento científico pede. Custo operacional da coleta
  Binance funding/OI (relacionada, não da própria H6) foi quantificado
  (`CR_RESEARCH_FREEZE.md`, `operational_cost_h6_binance_collection`):
  ~54 req/dia no endpoint gratuito da Binance (0.04% do limite de
  2400/min), sem tier pago, sem infra dedicada — custo monetário $0/mês.
  Ainda não quantificado: eletricidade marginal e uptime real do PC do
  dono (fora de alcance sem dados que só ele tem).
- **new_evidence?:** sim — primeira leitura real com n>=30 desde o início da
  coleta. Bloqueio anterior (rate limit não-autenticado do CoinGecko em
  `analyzers/backtest.py:_fetch_price`) resolvido nesta sessão via
  `COINGECKO_API_KEY` como variável de ambiente real do Windows (mesma classe
  de bug do `DATA_DIR` — lida via `os.getenv()` direto, não pelo `.env`).
- **decision:** `CR_PASSIVE_COLLECTION = ENABLED` para H6 — continua
  `COLLECTION_ONLY`, charter não alterado, não autoriza capital/shadow/GO.
  Resultado INCONCLUSIVE não é motivo para engenharia nova de poder (bloco
  18) — é só registro do estado real observado.
- **reopen_conditions:** N/A — não é uma hipótese fechada, é observação
  passiva em curso. Este resultado é um evidence update dentro do protocolo
  já registrado, não reabertura nem fechamento.

---

## Nota sobre completude

Este registro cobre as seis claims nomeadas explicitamente no bloco 27. Não
foram criadas claims adicionais além dessas seis — expandir o registro além
do que foi pedido seria pesquisa nova disfarçada de documentação.
