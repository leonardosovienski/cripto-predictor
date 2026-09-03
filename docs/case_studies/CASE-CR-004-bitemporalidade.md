# CASE-CR-004 — Modelo bitemporal como defesa estrutural contra lookahead bias

**Fonte:** `docs/ADR-014_modelo_bitemporal.md`, `charters/funding_oi_v3.json`,
`GarimpoInvestimentos/dpl/*`.

## Claim
A Data Provenance Layer (DPL) rastreia três instantes temporais distintos por
dado (`timestamp`, `published_at`, `vintage`) e usa exclusivamente
`published_at` para decidir o que estava disponível em cada ponto de decisão —
tornando lookahead bias uma classe de erro estruturalmente prevenida, não
apenas revisada manualmente.

## Protocolo
- `timestamp`: quando o fato ocorreu (candle, mês de referência, kickoff).
- `published_at`: quando o fato se tornou público — governa o anti-lookahead;
  invariante `published_at >= timestamp` validado em `MarketDataPoint` e
  `SignalPoint`.
- `vintage`: quando o dado foi coletado/gravado — permite representar revisões
  (ex.: IPCA revisado) como pontos separados, cada um com seu próprio
  `published_at`, sem lógica especial de "substituir" o valor antigo.
- Regra de alinhamento: `AlignmentEngine`/`EventAlignmentEngine` filtram
  **somente** por `published_at <= momento_da_decisão`, nunca por `timestamp`.
- `charters/funding_oi_v3.json` declara explicitamente os três papéis
  (`event_at_source`, `published_at_source`, `ingested_at_source`) como parte
  do contrato de coleta, não como detalhe de implementação.

## Result (o que foi de fato verificado nesta auditoria)
- O modelo está **documentado formalmente** (ADR-014, status "Aceita") e
  **presente em código** (`GarimpoInvestimentos/dpl/alignment.py`,
  `contracts.py`, `hash_chain.py`, migrações em `dpl/migrations/`).
- Existem testes nomeados para essa garantia especificamente
  (`test_alignment_point_in_time_*`, `test_event_align_*`, citados no próprio
  ADR; arquivos correspondentes presentes em `tests/` — `test_dpl.py`,
  `test_dpl_aggregation.py`, `test_dpl_features.py`, `test_dpl_migrations.py`).
- **Honestidade sobre o que esta auditoria NÃO fez**: esta rodada leu o código
  e os testes existentes, mas não executou a suíte nem re-verificou
  ao vivo que o alinhamento de fato rejeita `timestamp`-based leakage em dados
  reais — isso exigiria rodar harness/testes, fora do escopo desta auditoria
  de preservação (ver Blockers no relatório final).

## Failure mode que o desenho previne
Colapsar os três tempos em um único carimbo é descrito no próprio ADR como
"o pior tipo de bug num sistema de backtesting, porque não quebra nada: apenas
torna os resultados otimisticamente falsos." O exemplo documentado: usar o
IPCA revisado (v2, publicado em 15/mai) num backtest datado de 20/abr seria
lookahead invisível sem o modelo — o as-of por `published_at` impede isso por
construção, sem exigir lógica especial por tipo de revisão.

## Lesson
Separar "quando ficou público" de "quando ocorreu" e de "quando foi
coletado" é o ativo mais reutilizável do projeto para o ecossistema mais
amplo: qualquer domínio com dados revisáveis (macro, fundamentalista,
resultados esportivos) pode herdar a mesma garantia sem reimplementar a
lógica de as-of. É por isso que este componente está classificado como
REUSE/PRESERVE no inventário de componentes, e não como algo domain-owned do
cripto.
