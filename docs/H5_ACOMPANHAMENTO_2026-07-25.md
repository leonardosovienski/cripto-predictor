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

**Decisao desta rodada: CORRIGIDA, por decisao explicita do dono.** A primeira
leitura desta nota recomendava adiar a correcao para depois do gate, por
receio de alterar o input no meio da janela. Esse receio estava mal
calibrado e a nota foi corrigida: **nada coletado a partir de 25/07 amadurece
em D+7 antes de 28/07** (previsoes de hoje maturam em 02/08), entao a
correcao **nao muda nenhum numero do gate de 28/07**. O que ela afeta e a
cobertura de noticias das previsoes que maturam em agosto — que ja e
heterogenea por historico (serpapi ate 17/07, vazio ate 20/07, `curated_rss`
parcial desde 21/07) e ja e estratificada por `news_provider`,
`news_degraded_reason` e `input_degradado`.

O que a correcao **nao** faz: nao altera parametro, criterio, custo, data ou
manifest de H5; nao mexe em `trials.json`; nao reprocessa nem recarimba
observacao ja coletada; nao adiciona nem remove fonte do catalogo — apenas
restaura o acesso a uma fonte que ja pertencia a ele.

Verificacao real (read-only, sem credencial): a rota sem barra devolve 200 com
RSS valido (25 titulos). Dos 6 ativos que hasheiam para `coindesk`
(`arbitrum`, `bitcoin-cash`, `pepe`, `pump-fun`, `uniswap`, `whitebit`), 3
voltam a casar titulo. Os outros 3 seguem sem noticia por limitacao ja
documentada do desenho (1 feed geral por hash + filtro por substring), nao por
falha. Espera-se, portanto, que parte das previsoes continue
`input_degradado=1` mesmo apos a correcao.

## Pendencia diagnosticada, NAO corrigida — disjuntor por provider

Separado do feed acima, resta um efeito nao confirmado: `curated_rss:circuit_open`
aparece ~10 vezes por noite. O mecanismo esta identificado em
`collectors/news.py`: `_OPEN_CIRCUITS` e por **provider**, nao por feed, e abre
com 429 ou 5xx; alem disso o cache e por `(provider, ativo, limit)`, entao o
mesmo feed e rebaixado uma vez **por ativo** (28 downloads/noite sobre 5
feeds). A hipotese e que algum feed passe a responder 429 no meio da rodada e
derrube o `curated_rss` inteiro para os ativos restantes — incluindo os que
hasheiam para feeds saudaveis. **Nao corrigido**: falta evidencia de qual feed
e qual status (o log grava so o tipo da excecao). Corrigir exigiria cachear o
corpo do feed por rodada — mudanca de comportamento maior, sem causa provada.
Fica para decisao humana com evidencia melhor.

## Limites desta nota

Esta nota nao executa gate, nao recalcula ou persiste metricas, nao modifica
`trials.json`, nao estende H5 e nao ativa H6. A rotacao da credencial SerpAPI
continua `BLOCKED_PENDING_SECRET_ROTATION` e depende de evidencia humana.
