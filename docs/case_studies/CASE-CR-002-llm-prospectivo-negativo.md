# CASE-CR-002 — Score de LLM prospectivo: correlação negativa e estatisticamente
significativa, replicada em quatro encarnações

**Fonte:** `docs/HYPOTHESES.md` (H4/H5/H6), `docs/H5_ACOMPANHAMENTO_2026-07-25.md`,
`GarimpoInvestimentos/h6_status.json`, `docs/H6_REFREEZE_2026-08-27.md`.

## Claim
Um score de LLM (indicadores + notícias) foi pré-registrado para prever retorno
D+7 em cripto. Quatro tentativas sucessivas da mesma família (v1 pré-protocolo,
H4, H5, H6-invertida) não encontraram edge positivo; a única com amostra
suficiente (H5, n=440) foi refutada com o sinal na direção OPOSTA à hipótese.

## Protocolo
- Critério pré-registrado (idêntico em H4/H5/H6): Spearman IC95 não cruzando
  zero com n ≥ 30 previsões maduras, estratificado por Fonte/juiz; depois,
  Sharpe líquido por trade + DSR ≥ 0.95.
- H5 particionou ativos deterministicamente entre 4 juízes LLM (sha256 do nome
  mod 4), permitindo estratificação por juiz sem viés de seleção.
- H6 pré-registrou a leitura invertida (score alto = queda) ANTES de rodar,
  com trava técnica (`params.fonte = "reserved:h6-inversao-sinal"`) para que
  a maturação nunca reaproveitasse previsões da coleta não invertida.

## Result
- H4: coleta interrompida em n=5 (risco de estouro de cota Gemini) — sem
  veredito estatístico (`CLOSED_INSUFFICIENT_SAMPLE`).
- H5 (veredito em 2026-07-28, gate na data pré-registrada):
  Spearman pooled **−0.166** [IC95 −0.266; −0.057], n=440 — IC não cruza zero,
  na direção OPOSTA à hipótese. Sharpe/trade −0.312 (n=134). DSR 0.00 contra
  corte 0.95. Acurácia direcional 45.2% (abaixo de cara-ou-coroa). Estratégia
  (score≥60) rendeu −6.80% vs buy&hold BTC +0.99%.
- H6 (leitura invertida, última leitura commitada `h6_status.json`,
  2026-08-24): **n=0**, "aguardando n≥30". Um Sharpe auxiliar +0.3479 com n=6
  foi observado antes disso mas é explicitamente marcado como não-veredito
  (amostra insuficiente para qualquer IC).

## Failure mode
Duas armadilhas foram documentadas e evitadas explicitamente pelo projeto:
1. **Leitura prematura de amostra pequena**: o Sharpe +0.3479 (n=6) da H6 foi
   o único número positivo do registro inteiro — e o próprio doc adverte que
   "citar esse +0.3479 como sinal de que a inversão funciona seria exatamente
   o erro que este documento existe para impedir".
2. **Escolha de estrato após ver o resultado**: nem o estrato de input
   completo nem o degradado, isoladamente, atingem significância na H5 — só o
   pooled (pré-registrado) é julgado; escolher o estrato favorável depois é o
   p-hacking que o pré-registro existe para impedir.

## Lesson
Correlação negativa replicada em 3 das 4 tentativas com amostra madura é um
padrão, não ruído. A resposta correta do projeto não foi "tentar mais uma
variação até achar sinal" — foi registrar a inversão como hipótese nova,
formal, com trava técnica anti-reaproveitamento de dados, e aceitar que ela
segue imatura (n=0 na última leitura) em vez de forçar um veredito.
