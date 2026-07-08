"""Migração 0008 — carimbo de input degradado nas previsões (aditiva, idempotente).

O pipeline já DETECTA quando o LLM pontuou com input empobrecido (indicadores ou
notícias faltando) e emite telemetria — mas o flag não era persistido na previsão,
então o backtest não conseguia estratificar (previsões degradadas contaminavam o
pool). Esta migração fecha o "futuro" prometido no comentário do main.py.

Coluna NULLABLE de propósito (sem DEFAULT): linhas pré-0008 leem NULL = "não
medido na época" — distinto de 0 = "medido e completo". Nunca reinterpretar o
passado em silêncio.
"""

NAME = "0008_predictions_degraded"

SQL = """
    ALTER TABLE predictions ADD COLUMN input_degradado INTEGER;
"""
