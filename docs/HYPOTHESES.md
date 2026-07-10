# Pré-registro de Hipóteses — protocolo anti-data-snooping

> Regra do projeto (complementa o `trials.json`): **hipótese se registra ANTES de rodar.**
> O trials.json conta as tentativas (denominador do DSR); este arquivo registra o que
> cada tentativa esperava encontrar e qual era o critério de sucesso — para que um
> resultado positivo futuro não possa ser reescrito como "era o que sempre buscávamos".

## Formato

```
### H<N> — <nome curto>            (status: registrada | rodando | confirmada | refutada)
- Data do registro:
- Hipótese (mecanismo causal, 1-2 frases):
- Configuração (entra no trials.json como):
- Critério de sucesso (definido ANTES):
- Resultado (preenchido DEPOIS):
```

## Registro

### H1 — Funding/OI + regime HMM prevê retorno 24h (status: **refutada**)
- Data do registro: retroativo (V3, jun/2026 — pré-protocolo)
- Hipótese: desequilíbrio de alavancagem (funding z-score × ΔOI) condicionado ao regime
  do HMM prevê o retorno spot de 24h.
- Configuração: `v3-hmm-funding-oi-fr90`.
- Critério: PSR ≥ 0,80 ∧ IC_lo(Spearman) > 0 ∧ MaxDD < 20% — **líquido de custos**.
- Resultado (2026-07-02): **NO-GO.** Bruto +0,44bps/sinal morre em ~0,53bps de custo
  (BTC líquido −0,09bps, PSR 0,445; ETH PSR 0,051). Kelly-invariante.
- Confirmação independente (2026-07-09, auditoria cruzada): WFA re-rodado na base
  ESTENDIDA (2021→jul/2026) reproduz o NO-GO por caminho diferente — IC_lower do
  Spearman **−0,079 (cruza zero) mesmo com os custos da época da homologação**, e o
  PSR sem sobreposição de janelas (scripts/psr_nonoverlap.py) reprova 0/3 sub-séries.
  Além de os custos comerem o sinal, o edge bruto NÃO se sustentou no forward
  2025-26 — o "GO" de jun/2026 (pré-custos, dados até out/2024) está duplamente
  superado. O juiz tem poder comprovado (controle positivo oficial,
  scripts/attest_harness.py): o NO-GO é veredito, não cegueira. Implicação
  registrada no HANDOFF: **não promover a capital real em 28/07**.

### H2 — Janela curta de funding (fr21) melhora a sensibilidade (status: **refutada**)
- Data do registro: 2026-07-02 (antes do resultado com custos).
- Hipótese: z-score de 7 dias reage mais rápido a squeezes que o de 30 dias.
- Configuração: `v3-hmm-funding-oi-fr21`.
- Critério: idêntico ao H1, líquido de custos.
- Resultado (2026-07-02): **NO-GO.** PSR 0,215; bruto +0,07bps → líquido −0,37bps/sinal;
  MaxDD 25,8%. Janela curta piora vs fr90 — mais ruído, não mais sensibilidade.

### H3 — Horizonte maior amortiza a fricção (status: **refutada**)
- Data do registro: 2026-07-02 (antes do resultado).
- Hipótese: a fricção é fixa por trade (~30bps round-trip em posição cheia); com
  horizonte 48h o edge por sinal dobra de espaço enquanto o custo fica ~constante
  (funding ×2, fee/slip iguais) → o líquido pode cruzar para positivo.
- Configuração: `v3-hmm-funding-oi-fr90-h48` (registrada no trials).
- Critério: idêntico ao H1, líquido de custos.
- Resultado (2026-07-02): **NO-GO — e informativo.** Em 48h o edge bruto VIRA NEGATIVO
  (−0,35bps → líquido −0,75bps/sinal; PSR 0,192; MaxDD 50,3%). O sinal de funding/OI é
  de vida CURTA: esticar o horizonte destrói em vez de amortizar. Aprendizado real:
  qualquer variação futura desta família deve ir na direção OPOSTA (mais convicção e
  menos trades no MESMO horizonte, não horizontes maiores).

### H4 — Score do LLM prevê retorno D+7 (status: **encerrada sem veredicto — coleta interrompida**)
- Data do registro: formalização em 2026-07-02 (hipótese original do projeto).
- Hipótese: LLM sobre indicadores + notícias produz score com correlação positiva com
  o retorno de 7 dias, no universo do discovery (condicional à pré-seleção momentum).
- Configuração: `v2-dpl-gemini-h7`.
- Critério: Spearman IC95 não cruza zero ("validado") com n ≥ 30 previsões maduras,
  estratificado por Fonte; depois disso, Sharpe líquido por trade + DSR ≥ 0,95.
- Resultado: (coleta diária em andamento; n=5 previsões, D+7 imaturo)
- Parcial (2026-07-08, fechamento automático do backtest): primeiro Sharpe por-trade
  maduro da trial 1 = **−0,5734** (n pequeno, estrato único — NÃO é veredicto; o
  critério pede n ≥ 30). Registrado para que a decisão de continuidade da Fase 1
  (prazo 28/07, ver HANDOFF) seja tomada olhando o número, não a memória.
- Encerramento (2026-07-10, decisão do dono): coleta interrompida com **n=5**
  (imaturo — sem veredicto estatístico) para migrar ao modo multi-provedor
  (risco iminente de estouro da cota do Gemini: 22 ativos vs ~20/dia do free
  tier; estourar a cota = dias de coleta perdidos sem querer). Substituída pela
  H5/`v2-dpl-multi-h7`. As 5 previsões coletadas permanecem no histórico,
  carimbadas com o juiz gemini — não se misturam com a série nova.

### H5 — Score do LLM prevê retorno D+7, partição multi-provedor (status: **rodando — coleta**)
- Data do registro: 2026-07-10 (ANTES de qualquer resultado do modo multi).
- Hipótese: a mesma da H4 (LLM sobre indicadores + notícias produz score com
  correlação positiva com o retorno D+7), agora com os ativos particionados de
  forma FIXA e determinística entre 4 juízes (gemini/groq/cerebras/mistral,
  sha256 do nome mod 4) — cada ativo tem sempre o mesmo juiz, e o carimbo
  `judge` por previsão permite estratificar por juiz na análise.
- Configuração: `v2-dpl-multi-h7`.
- Critério de sucesso (definido ANTES): idêntico ao da H4 — Spearman IC95 não
  cruza zero com n ≥ 30 previsões maduras, estratificado por Fonte (e agora
  também reportado por juiz); depois, Sharpe líquido por trade + DSR ≥ 0,95.
  Um juiz individual só é julgado com n ≥ 30 no SEU estrato.
- Resultado: (coleta iniciada em 2026-07-10)

---

## Backlog condicional (ideias — NÃO são tentativas)

> Registrado em 2026-07-07 (triagem de propostas externas). Nada daqui entra no
> `trials.json` nem consome tentativa: são candidatos a hipótese futura, com
> critério de ATIVAÇÃO explícito. Promover um item = escrever um H<N> completo
> acima (com critério de sucesso ANTES de rodar) + registrar no trials.json.
> Ordenados por relação benefício/custo estimada na triagem.

### B1 — Calendário macro + DXY como features exógenas
- Sinal: dummies de evento (FOMC, CPI/PPI — datas conhecidas com antecedência) e
  série do DXY/juros como contexto de regime.
- Fonte: CSV estático de calendário (custo ~zero) + `BCBProvider` já existente como
  precedente de sinal macro com `published_at` correto; DXY via fonte gratuita.
- Ortogonalidade: choque exógeno — nenhum sinal atual quantifica agenda macro.
- Ativação: após veredicto da H4 (não misturar mudança de input com trial em curso).

### B2 — Derivativos derivados do que JÁ se coleta (OI/volume, funding contínuo)
- Sinal: razão OI/volume spot (especulação vs demanda real) e funding como custo de
  carregamento contínuo (não só extremos); funding consenso multi-exchange via ccxt.
- Fonte: dados de funding/OI da V3 já ingeridos — só recombinação.
- Ortogonalidade: parcial (mesma família da H1-H3 refutada) — o aprendizado da H3
  (sinal de vida curta) LIMITA o desenho: mesma janela, mais convicção, menos trades.
- Ativação: só com mecanismo causal novo por escrito (recombinar features da família
  refutada sem tese nova é convite a p-hacking).
- RESSALVA FACTUAL da triagem: liquidações históricas da Binance NÃO são endpoint
  público simples (forceOrders exige auth; histórico agregado é de provedores pagos)
  — o custo de coleta de liquidações é MAIOR que o proposto originalmente.

### B3 — Feature engineering sobre dados existentes (espectro de momentum/vol)
- Sinal: momentum 3/14/30d, vol EWMA, z-score de volume, correlação rolante com BTC.
- Fonte: OHLCV já na Feature Store; `feature_version` (migração 0007) permite
  backfill de versões novas SEM sobrescrever o que experimentos passados leram.
- Ortogonalidade: baixa-média (deriva de preço/volume) — o ganho é dar espectro ao
  modelo, não fenômeno novo.
- Ativação: após veredicto da H4; CADA conjunto de features testado = trial nova
  (features_used no registro — o schema já suporta).

### B4 — Meta-análise dos NO-GO ("o que as refutadas têm em comum?")
- Sinal: nenhum — é meta-pesquisa sobre trials.json/HYPOTHESES (não conta tentativa).
- Custo ~zero; pode rodar a qualquer momento, MAS com n=3 refutadas da MESMA família
  a resposta hoje é trivial ("custos comem sinais de microestrutura de 24h").
- Ativação: quando houver ≥2 famílias distintas fechadas (ex.: após veredicto da H4).

### B5 — Sentimento textual como série temporal (separar texto do viés do LLM)
- Sinal: série diária de sentimento das notícias (léxico/contagem), alinhada por
  `published_at`, testável como feature independente do score consolidado do LLM.
- Ortogonalidade: média — permite atribuir o (eventual) alpha da H4 ao texto ou ao LLM.
- Ativação: só se a H4 validar (se o score consolidado não prevê, decompor ele não
  tem urgência).

### B6 — Microestrutura de liquidez (spread, profundidade do book)
- Sinal: spread % médio e profundidade top-10 por snapshot horário → média diária.
- CORREÇÃO da triagem: o custo NÃO é baixo — exige coletor de alta frequência novo,
  storage e operação contínua; e sinais de prazo mais curto enfrentam custos de
  transação PIORES que os que já mataram o sinal de 24h (lição H1-H3).
- Ativação: só com tese explícita de uso em horizonte ≥ D+1 e orçamento de operação.

### B7 — On-chain (net flow p/ exchanges, Coin Days Destroyed)
- Ortogonalidade: alta (comportamento de rede, não deriva de preço).
- Custo: API paga (Glassnode/CoinMetrics) — decisão de ORÇAMENTO, não técnica.
- Ativação: decisão explícita do dono sobre custo recorrente + hipótese isolada.

### B8 — Modelagem de sobrevivência (tempo até evento de risco, não direção)
- Sinal: P(drawdown ≥ X% em ≤ T dias) para sizing/gestão de risco.
- Ativação: SOMENTE se existir edge direcional validado para proteger — gestão de
  risco de um sinal que não existe é polimento de motor desligado (mesma razão da
  rejeição do Regime Shift Detector na triagem de jul/2026).
