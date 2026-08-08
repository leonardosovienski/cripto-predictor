"""Migrações ADITIVAS da Feature Store, fora do schema base de feature_store.py.

Cada módulo `NNNN_*.py` expõe `NAME` (str) e `SQL` (str). São aplicadas em ordem
por `run_migrations` (idempotente por nome). Princípio (ADR-017 / auditoria C-04):
**nunca alterar uma migração já publicada in-place** — toda mudança de schema é uma
nova migração que transforma o estado anterior, garantindo idempotência para DBs em
qualquer versão.
"""

from GarimpoInvestimentos.dpl.migrations import _0005_fix_raw_signals as _m0005
from GarimpoInvestimentos.dpl.migrations import _0006_predictions as _m0006
from GarimpoInvestimentos.dpl.migrations import _0007_feature_version as _m0007
from GarimpoInvestimentos.dpl.migrations import _0008_predictions_degraded as _m0008
from GarimpoInvestimentos.dpl.migrations import _0009_predictions_llm_fallback as _m0009
from GarimpoInvestimentos.dpl.migrations import _0010_predictions_news_provenance as _m0010
from GarimpoInvestimentos.dpl.migrations import _0011_predictions_collection_policy as _m0011
from GarimpoInvestimentos.dpl.migrations import _0012_provenance_content_hash as _m0012
from GarimpoInvestimentos.dpl.migrations import _0013_enriched_signals as _m0013
from GarimpoInvestimentos.dpl.migrations import _0014_source_quality_scorecards as _m0014

# Lista ordenada de migrações aditivas (nome, sql), aplicadas após o schema base.
ADDITIVE_MIGRATIONS = [
    (_m0005.NAME, _m0005.SQL),
    (_m0006.NAME, _m0006.SQL),
    (_m0007.NAME, _m0007.SQL),
    (_m0008.NAME, _m0008.SQL),
    (_m0009.NAME, _m0009.SQL),
    (_m0010.NAME, _m0010.SQL),
    (_m0011.NAME, _m0011.SQL),
    (_m0012.NAME, _m0012.SQL),
    (_m0013.NAME, _m0013.SQL),
    (_m0014.NAME, _m0014.SQL),
]
