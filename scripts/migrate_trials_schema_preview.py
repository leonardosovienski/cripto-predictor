"""Migração NÃO-DESTRUTIVA de preview: GarimpoInvestimentos/trials.json (schema legado)
-> um novo arquivo trials_migrated_preview.json no schema alvo do relatório de
congelamento científico (CR_RESEARCH_FREEZE).

Este script:
  - NUNCA sobrescreve GarimpoInvestimentos/trials.json (fonte original preservada);
  - escreve um arquivo NOVO ao lado, com sufixo `_migrated_preview.json`;
  - preenche com "UNKNOWN" todo campo do schema alvo que não existe no legado
    (nunca inventa valor);
  - é idempotente e só de LEITURA sobre o arquivo original.

Uso:
    python scripts/migrate_trials_schema_preview.py

Campos do schema alvo (ver PASSO 7 da auditoria de congelamento):
    experiment_id, hypothesis_id, hypothesis_family, trial_id, registered_at,
    executed_at, seed, forecast_horizon, data_cutoff, label_start, label_end,
    dataset_hash, dataset_version, feature_version, model_version, code_version,
    params, selection_path, n_trials_family, n_trials_domain, n_trials_ecosystem,
    metric, result, status, notes
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "GarimpoInvestimentos" / "trials.json"
TARGET = REPO_ROOT / "GarimpoInvestimentos" / "trials_migrated_preview.json"

UNKNOWN = "UNKNOWN"

TARGET_FIELDS = [
    "experiment_id",
    "hypothesis_id",
    "hypothesis_family",
    "trial_id",
    "registered_at",
    "executed_at",
    "seed",
    "forecast_horizon",
    "data_cutoff",
    "label_start",
    "label_end",
    "dataset_hash",
    "dataset_version",
    "feature_version",
    "model_version",
    "code_version",
    "params",
    "selection_path",
    "n_trials_family",
    "n_trials_domain",
    "n_trials_ecosystem",
    "metric",
    "result",
    "status",
    "notes",
]


# Mapeamento explícito e conservador legado -> alvo. Só mapeia quando o campo
# legado responde inequivocamente à pergunta do campo alvo; tudo o mais fica
# UNKNOWN.
def migrate_record(legacy: dict) -> dict:
    rec = {field: UNKNOWN for field in TARGET_FIELDS}
    rec["trial_id"] = legacy.get("name", UNKNOWN)
    rec["registered_at"] = legacy.get("registered_at", UNKNOWN)
    rec["params"] = legacy.get("params", UNKNOWN)
    rec["notes"] = legacy.get("notes", UNKNOWN)
    # "sharpe" no legado é um resultado pontual, não o `metric`/`result` tipado
    # do schema alvo (que exige declarar QUAL métrica e seu valor/veredito
    # estruturado) — preservado em notes/result bruto, sem forjar o par
    # metric/result formal.
    if "sharpe" in legacy:
        rec["result"] = {"sharpe_raw_legacy_field": legacy["sharpe"]}
    return rec


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"fonte não encontrada: {SOURCE}")
    if TARGET.exists():
        raise SystemExit(
            f"recusando sobrescrever preview existente: {TARGET}. "
            "Apague-o manualmente se quiser regenerar."
        )
    legacy_trials = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(legacy_trials, list):
        raise SystemExit("formato inesperado: trials.json não é uma lista")

    migrated = [migrate_record(t) for t in legacy_trials]

    payload = {
        "schema_version": "cr-trial-schema-preview/1",
        "source_file": "GarimpoInvestimentos/trials.json",
        "source_record_count": len(legacy_trials),
        "note": (
            "Preview de migração NÃO-DESTRUTIVO gerado por auditoria de "
            "congelamento científico. O arquivo original permanece a fonte "
            "de verdade e não foi alterado. Campos ausentes no legado ficam "
            "explicitamente 'UNKNOWN' — nunca inferidos ou inventados."
        ),
        "trials": migrated,
    }
    TARGET.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )
    print(f"preview escrito em {TARGET} ({len(migrated)} registros)")


if __name__ == "__main__":
    main()
