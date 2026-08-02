# Template — nova trial com multi-news, filtros e guardas

Este arquivo e um **template**, nao um registro em `trials.json`. Preencha, revise
e registre uma trial nova somente depois da rotacao de credenciais, decisao sobre
logs e aprovacao humana do protocolo.

## Protocolo a congelar antes da primeira coleta

```text
Nome da trial:
Data/hora UTC de inicio:
Horizonte: 7 dias
Universo de ativos:
LLM_MULTI_PROVIDERS:
NEWS_PROVIDERS (ordem exata):
CRYPTOPANIC ativo? (sim/nao):
LLM_PREFILTER_ENABLED:
LLM_PREFILTER_MIN_VOLUME_USD:
LLM_PREFILTER_MIN_ABS_CHANGE_7D:
API_GUARD_ENABLED:
API_GUARD_MAX_INGEST_ASSETS:
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER:
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER:
```

## Registro sugerido

```json
{
  "name": "preencher-nome-imutavel",
  "registered_at": "YYYY-MM-DDTHH:MM:SSZ",
  "params": {
    "fonte": "dpl:fallback",
    "horizonte_dias": 7,
    "juiz": "descrever particao fixa",
    "input": "LLM + indicadores + noticias; ver collection_policy persistida por previsao",
    "news_router": "listar NEWS_PROVIDERS exatamente",
    "selection_policy": "copiar collection_policy do primeiro artefato controlado"
  },
  "sharpe": null,
  "notes": "Criterio: Spearman IC95 nao cruza zero com n>=30 maduro; depois Sharpe liquido por trade + DSR>=0.95. Nao misturar com H5."
}
```

## Gates antes da primeira chamada real

1. Credencial nova fora do Git e scan limpo.
2. Logs decididos e redigidos conforme a decisao humana.
3. Scheduler bloqueado ate o ciclo manual controlado.
4. Validar um ciclo manual: redaction, lock, timeout, heartbeat, JSONL, artefato,
   exit code e idempotencia.
5. Conferir no SQLite que `news_provider` e `collection_policy` foram gravados.


