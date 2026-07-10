"""Migração 0009 — carimbo estrutural de fallback do LLM nas previsões.

Quando o LLM falha (timeout, cota, parse), `analyze_asset` devolve o fallback
neutro (score 50) e a previsão ENTRA no histórico. O backtest já a excluía, mas
por string mágica no resumo ("fallback aplicado") — frágil: uma mudança de
texto quebraria o filtro em silêncio. Com 4 provedores (modo multi), a
superfície de falha quadruplicou; o carimbo vira coluna estrutural.

Coluna NULLABLE de propósito (sem DEFAULT), mesmo princípio da 0008: linhas
pré-0009 leem NULL = "não medido na época" (o filtro legado por marcador no
resumo continua cobrindo essas). Nunca reinterpretar o passado em silêncio.
"""

NAME = "0009_predictions_llm_fallback"

SQL = """
    ALTER TABLE predictions ADD COLUMN llm_fallback INTEGER;
"""
