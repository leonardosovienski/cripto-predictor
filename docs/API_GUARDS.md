# Guardas antes de chamadas externas — Fase 1

As guardas operam antes das unidades de trabalho externas da Fase 1 e ficam
ligadas por padrão desde a auditoria 2026-08-28 (V-02) — antes disso,
`API_GUARD_ENABLED` tinha default `false` e nenhum orçamento era aplicado sem
configuração explícita. Elas não substituem os rate limits dos provedores e
não tocam V3, paper trading ou backtest.

```dotenv
API_GUARD_ENABLED=true
API_GUARD_MAX_INGEST_ASSETS=0
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER=0
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER=0
```

`0` significa sem teto — ou seja, com os limites acima a guarda está ligada
mas ainda não bloqueia nada. Defina os 3 limites com um valor > 0 para que o
orçamento seja de fato aplicado. Em uma nova trial forward, um exemplo
conservador seria:

```dotenv
API_GUARD_ENABLED=true
API_GUARD_MAX_INGEST_ASSETS=28
API_GUARD_MAX_NEWS_ATTEMPTS_PER_PROVIDER=8
API_GUARD_MAX_LLM_CALLS_PER_PROVIDER=6
```

Quando ativo, o consumo e persistido em `DATA_DIR/api_guard_budget.db`, por dia
UTC, stage e provider. O incremento usa transacao SQLite `BEGIN IMMEDIATE`, de
modo que processos concorrentes e reinicios compartilham o mesmo teto. Apagar
esse banco reinicia deliberadamente o orcamento e deve ser tratado como acao
operacional auditavel.

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
