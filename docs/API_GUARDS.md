# Guardas antes de chamadas externas — Fase 1

As guardas operam antes das unidades de trabalho externas da Fase 1 e ficam
desligadas por padrão. Elas não substituem os rate limits dos provedores e não
tocam V3, paper trading ou backtest.

```dotenv
API_GUARD_ENABLED=false
API_GUARD_MAX_INGEST_ASSETS=0
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER=0
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER=0
```

`0` significa sem teto. Em uma nova trial forward, um exemplo conservador seria:

```dotenv
API_GUARD_ENABLED=true
API_GUARD_MAX_INGEST_ASSETS=28
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER=8
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER=6
```

## Cobertura

1. Antes da ingestão de cada ativo, impede novas unidades de preço/sinais depois do
   teto global de ativos.
2. Antes de cada tentativa de provedor de notícias, aplica orçamento por provedor.
3. Antes da inferência, aplica orçamento por juiz LLM.
4. O Fear & Greed é cacheado por processo e limite: uma rodada não repete a mesma
   chamada por ativo.
5. Notícias bem-sucedidas são cacheadas por fonte, consulta e limite durante o
   processo.

Cada bloqueio emite `api_guard_skipped` no JSONL com etapa, ativo e razão. Como os
tetos reduzem a população observada, qualquer ativação altera a coleta e exige trial
forward nova; H5 permanece congelada.


