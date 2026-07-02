"""Migrações ADITIVAS da Feature Store, fora do schema base de feature_store.py.

Cada módulo `NNNN_*.py` expõe `NAME` (str) e `SQL` (str). São aplicadas em ordem
por `run_migrations` (idempotente por nome). Princípio (ADR-017 / auditoria C-04):
**nunca alterar uma migração já publicada in-place** — toda mudança de schema é uma
nova migração que transforma o estado anterior, garantindo idempotência para DBs em
qualquer versão.
"""
from GarimpoInvestimentos.dpl.migrations import _0005_fix_raw_signals as _m0005
from GarimpoInvestimentos.dpl.migrations import _0006_predictions as _m0006

# Lista ordenada de migrações aditivas (nome, sql), aplicadas após o schema base.
ADDITIVE_MIGRATIONS = [
    (_m0005.NAME, _m0005.SQL),
    (_m0006.NAME, _m0006.SQL),
]
