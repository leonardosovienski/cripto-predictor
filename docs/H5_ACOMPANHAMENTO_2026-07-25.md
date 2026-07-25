# H5 — acompanhamento operacional de 2026-07-25

Esta nota registra qualidade de coleta e proveniencia sem alterar H5, seus
parametros, o Scheduler ou o criterio do gate de 28/07/2026.

## Estado observado

- H5 (`v2-dpl-multi-h7`) iniciou em 10/07/2026 e tem 15 lotes de previsoes
  registrados (410 previsoes reais).
- Houve 14 lotes completos de 28 previsoes e um lote parcial de 18 previsoes
  em 17/07; o lote parcial e `SUCCESS`, pois produziu previsoes reais, mas
  sua cobertura deve permanecer identificavel por provenance.
- Nao ha lote em 12/07: e uma `FAILURE` historica de Scheduler/energia, ja
  corrigida na configuracao da tarefa; nao e `NO_DATA`, `NO_SIGNAL` ou
  evidencia contra H5.
- Nao ha linhas de fallback de LLM na coorte H5 atual.
- 194 previsoes (47,3%) trazem input completo e 216 (52,7%) trazem
  `input_degradado=1`. O marcador representa cobertura reduzida de noticias,
  nao score, retorno ou falha da hipotese.

## Correcoes de leitura

1. Pipeline saudavel nao e evidencia de edge. Uma execucao `SUCCESS` so prova
   que a coleta e persistencia aconteceram.
2. `input_degradado=1` nao autoriza apagar observacoes, reclassificar datas ou
   escolher somente a parte completa depois de observar os retornos.
3. O lote parcial de 17/07 deve continuar no historico com seus carimbos reais;
   nao deve ser preenchido retroativamente.
4. A ausencia de 12/07 deve permanecer contabilizada como falha operacional
   historica, ja tratada, sem recriacao de observacoes.

## Melhorias operacionais registradas

- No gate, anexar as contagens por `input_degradado`, `news_provider`, fonte e
  juiz que ja existem no Feature Store. Sao estratificacoes de auditabilidade;
  nao sao novos criterios de aprovacao nem permitem trocar o veredito pooled.
- Enquanto H5 estiver aberta, monitorar diariamente: lote esperado, numero de
  previsoes reais, numero de juizes e marcadores de degradacao. Classificar a
  execucao somente como `SUCCESS`, `NO_SIGNAL`, `NO_DATA`, `INELIGIBLE` ou
  `FAILURE`; cobertura parcial cabe em `SUCCESS` com provenance preservada.
- Depois do gate, decidir separadamente se a cobertura RSS justifica uma nova
  hipotese/protocolo. Nao trocar fontes durante H5 para melhorar a amostra.

## Achado tecnico de 2026-07-25 — feed `coindesk` caido (NAO corrigido de proposito)

Diagnostico reproduzivel, sem alterar codigo nem producao:

- Desde 21/07 o motivo `curated_rss:HTTPStatusError` aparece em **exatamente 5
  previsoes por noite**, todas as noites — padrao deterministico, nao
  intermitente.
- Causa confirmada por requisicao real, read-only, aos 5 feeds do
  `CURATED_RSS_FEEDS` (`collectors/news.py`), com `follow_redirects=False`
  igual ao cliente do nucleo: `coindesk` responde **308** para
  `/arc/outboundfeeds/rss?outputType=xml` (sem a barra antes do `?`). Os
  outros quatro (`blockworks`, `decrypt`, `cointelegraph`, `cryptopotato`)
  respondem 200 com corpo valido.
- E o **mesmo modo de falha** do `blockworks.co` -> `blockworks.com`
  corrigido em 20/07: redirect permanente que o cliente do nucleo nao segue.
  Cada ativo que hasheia para `coindesk` perde a fonte em toda chamada.
- Efeito colateral observado: `curated_rss:circuit_open` (~10/noite) e em boa
  parte a cascata do disjuntor abrindo apos essas falhas repetidas.

**Decisao desta rodada: NAO corrigir a URL antes do gate.** Consertar o feed
aumentaria a cobertura de noticias nas ultimas noites da janela (25 a 27/07),
alterando a caracteristica do input no meio de H5 — exatamente o que a secao
acima proibe ("nao trocar fontes durante H5 para melhorar a amostra"). O
achado fica registrado com evidencia reproduzivel para decisao humana **depois
de 28/07**. Nao e regressao de codigo nova nem invalida observacoes ja
coletadas: as previsoes afetadas ja estao corretamente carimbadas com
`input_degradado=1` e `news_degraded_reason`, e o backtest ja estratifica por
esses campos.

## Limites desta nota

Esta nota nao executa gate, nao recalcula ou persiste metricas, nao modifica
`trials.json`, nao estende H5 e nao ativa H6. A rotacao da credencial SerpAPI
continua `BLOCKED_PENDING_SECRET_ROTATION` e depende de evidencia humana.
