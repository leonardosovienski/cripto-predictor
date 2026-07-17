"""Migração 0011 — identidade da política de coleta da previsão."""

NAME = "0011_predictions_collection_policy"
SQL = "ALTER TABLE predictions ADD COLUMN collection_policy TEXT;"
