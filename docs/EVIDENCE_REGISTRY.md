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
- **Q:** média (pré-registrado, custos assumidos via CostModel testado, WFA com
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
  [IC95 −0.266; −0.057], n=440, DSR histórico 0.00 (recalibração exata pendente dos retornos
  originais; errata P0-A 2026-09-07), acurácia direcional
  45.2% (abaixo do acaso). H4 (v2-dpl-gemini-h7) CLOSED_INSUFFICIENT_SAMPLE —
  coleta interrompida em n=5 por risco de estouro de cota, sem veredito
  estatístico possível.
- **limitations:** H4 nunca teve poder suficiente para refutar nem confirmar
  nada — não deve ser lido como "LLM não funciona", só como "não foi possível
  testar".
- **new_evidence?:** não.
- **decision:** ambas encerradas. H5 tem evidência negativa na direção testada;
  n=440, isoladamente, não demonstra poder para todos os efeitos/regimes; H4 é inconclusivo por desenho interrompido, não por
  refutação.
- **reopen_conditions:** mesmas do CLAIM-CR-HMM (dossiê + atestado de poder).
  Para H4 especificamente, exigiria também resolver o risco operacional de
  cota da API que motivou a interrupção original.

---

## CLAIM-CR-TREND
**Descrição:** Trend-following / momentum / SMA200 tem edge sobre cripto
após custos.

- **state:** CLOSED_BY_SCOPE / INCONCLUSIVE — decisão de escopo não é refutação
  científica; não há trial dedicada com evidência equivalente a H1-H5.
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
**Descrição:** O modelo de custos assumido reduz o resultado simulado; a fricção
executável em conta real ainda não foi medida.

- **state:** SUPPORTED_UNDER_ASSUMED_COST_MODEL
- **L:** forte para a identidade contábil; fraco para atribuir a perda real a fees.
- **Q:** baixa para calibração econômica; testes validam aritmética, não execução.
- **classification:** ASSUMED / UNCALIBRATED (fee 10bps e slippage 5bps por perna).
- **evidence:** H1 bruto +0,44bps/sinal, líquido −0,09bps sob o modelo congelado.
  Funding usa a taxa vigente na abertura repetida pelo horizonte; não equivale a
  pagamentos realizados. Sensibilidade e proveniência: `HYPOTHESES.md`, P0-B
  de 2026-09-07. O FAQ público ilustra 2bps maker e 5bps taker; sua própria
  ressalva diz que são taxas hipotéticas. Fee efetiva da conta: UNKNOWN.
- **limitations:** posição média absoluta e decomposição de funding de H1-H3 não
  foram preservadas em um artefato identificado; o agregado não permite calcular
  PSR/MaxDD sob nova fee. Spot segue `UncalibratedCostModel`.
- **new_evidence?:** correção de proveniência, sem reexecução científica.
- **decision:** retirados Q alta e MEASURED/CALIBRATED; valores em `v3/costs.py`
  preservados integralmente. H1-H3 e a família permanecem fechadas.
- **reopen_conditions:** mudar parâmetros exige proposta pré-registrada,
  dossiê e evidência independente; a proposta P0-B não autoriza a execução.

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
  0)". `charters/scientific_state.json` era `CLOSED_NO_GO` na base auditada;
  a afirmação anterior de que continuava COLLECTION_ONLY_IMMATURE era falsa.
  Errata 2026-09-07: `CLOSED_INSUFFICIENT_SAMPLE`, sem reativação.
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
- **decision:** manter a não promoção operacional registrada em 2026-09-04,
  corrigindo sua causa para `CLOSED_INSUFFICIENT_SAMPLE` / UNDERPOWERED. O
  fechamento existe em `HYPOTHESES.md` e na reconciliação de 2026-09-05; não há
  ali justificativa de poder que permita chamar o IC cruzando zero de refutação.
  A coleta Binance é um plano independente e continua intocada. A disponibilidade
  desse feed não significa que H6 esteja aberta para maturação automática.
- **reopen_conditions:** H6 está encerrada; a afirmação anterior de “N/A, não é
  hipótese fechada” foi retirada. Qualquer nova inferência exige novidade material,
  poder dimensionado, protocolo e evidência independente. Nenhuma reabertura aqui.

---

## Nota sobre completude

Este registro cobre as seis claims nomeadas explicitamente no bloco 27. Não
foram criadas claims adicionais além dessas seis — expandir o registro além
do que foi pedido seria pesquisa nova disfarçada de documentação.
