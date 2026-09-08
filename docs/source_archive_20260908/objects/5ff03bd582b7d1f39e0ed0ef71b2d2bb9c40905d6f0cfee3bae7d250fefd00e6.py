"""Migração 0010 — proveniência da fonte de notícias da previsão."""

NAME = "0010_predictions_news_provenance"

SQL = """
    ALTER TABLE predictions ADD COLUMN news_provider TEXT;
    ALTER TABLE predictions ADD COLUMN news_degraded_reason TEXT;
"""
