# Binance Spot microstructure — COLLECTION_ONLY

Coleta prospectiva pública e contínua de `BTCUSDT` e `ETHUSDT`. O processo usa
somente `GET /api/v3/depth?limit=1000` e os streams Spot públicos `trade`,
`bookTicker` e `depth@100ms`. Não lê chaves, não cria `TradeIntent`, não importa o
paper trader e não contém adapter de ordens.

## Operação

```powershell
python -m GarimpoInvestimentos.trading.binance_spot_collector `
  --symbol BTCUSDT ETHUSDT `
  --db data/binance_spot_microstructure.sqlite3
```

O equivalente supervisionado é:

```powershell
python -m GarimpoInvestimentos.jobs microstructure-live
```

Falhas permanentes retornam exit code não zero. `Ctrl+C` solicita shutdown limpo.
Cada conexão recebe novo session ID; a conexão é renovada preventivamente antes de
24 horas. Reconnect usa backoff exponencial com jitter e possui limite explícito.
Após restart ou reconnect, os dois books são obrigatoriamente ressincronizados.

## Sequência e persistência

O diff-depth começa a ser consumido enquanto o snapshot REST é solicitado. Eventos
com `u <= lastUpdateId` são descartados. O primeiro aplicável deve satisfazer
`U <= lastUpdateId + 1 <= u`; qualquer gap, book vazio ou cruzado invalida o estado
local e exige novo snapshot. O buffer tem limites de idade e quantidade.

SQLite usa migração aditiva, transações e tabelas append-only. IDs repetidos com o
mesmo hash são idempotentes; o mesmo ID com conteúdo diferente falha. Trades, BBO,
depth e snapshots mantêm proveniência live separada, tempos disponíveis, session ID,
hash, flags de qualidade e `COLLECTION_ONLY`. Snapshot REST registra explicitamente
que não possui exchange event time.

## Qualidade e limites científicos

`microstructure_quality.watchdog()` verifica presença/staleness por ativo e stream,
estado científico e books vazios/cruzados. `daily_scorecards()` produz oito cartões
separados (quatro streams × dois ativos), incluindo cobertura, disponibilidade,
sequência/gaps, latências p50/p95/p99, duplicatas, conflitos, integridade temporal,
books cruzados e períodos degradados.

O baseline continua `DEGRADED` quando falta evidência e nunca é promovido
automaticamente. Backfill não faz parte deste coletor, não mede latência e não pode
ser interpretado como histórico de book ou OOS. O observation plan permanece DRAFT.

Critérios de parada operacional: falha de sincronização, buffer excedido, gap de
sequência, book vazio/cruzado, estado diferente de `COLLECTION_ONLY`, persistência
indisponível ou limite de reconnects excedido. O operador deve preservar o banco e
investigar; nunca completar lacunas artificialmente.
