"""Etapa 1 do Prompt 3c: previsões zero-shot do Chronos-Bolt-Small em CPU, sem rede.

Uso (venv separado com chronos-forecasting/torch e o projeto instalado; rede desligada):
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python chronos_forecast.py \
      --weights-dir <dir com model.safetensors e config.json> --out forecasts.json --ledger runs.jsonl

Nada é escolhido aqui: dados, corte, período, horizonte, contexto e quantis vêm do pré-registro.
O script confere os hashes dos pesos e dos dados, monta os contextos causais (só closes até a
origem) e grava os quantis de PREÇO do dia-alvo. A execução vai para o ledger (STARTED e depois
COMPLETED ou CRASHED).
"""

import argparse
import hashlib
import importlib.metadata as md
import json
from pathlib import Path

import torch
from chronos import BaseChronosPipeline

from GarimpoInvestimentos.research import fm_zero_shot as fz
from GarimpoInvestimentos.run_ledger import RunLedger, recorded_run

CONTEXT_MAX = 2048  # pré-registro: forecast.context = últimos 2048 (context_length do checkpoint)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--batch", type=int, default=64)
    args = parser.parse_args()

    prereg, prereg_sha = fz.load_preregistration()
    candidate, forecast = prereg["candidate"], prereg["forecast"]
    versions = {p: md.version(p) for p in ("chronos-forecasting", "torch", "transformers")}
    with recorded_run(
        RunLedger(args.ledger),
        kind="fm_zero_shot_forecast",
        config={"preregistration_id": prereg["id"], "preregistration_sha256": prereg_sha},
        costs=None,
        validation_protocol={
            "contamination": prereg["contamination"],
            "evaluation_period": prereg["evaluation_period"],
            "forecast": forecast,
        },
        model={**candidate, "runtime_versions": versions},
        seeds=[0],
    ) as run:
        if sha256_file(args.weights_dir / "model.safetensors") != candidate["weights_sha256"]:
            raise fz.DataIntegrityError("pesos diferentes do pré-registro")
        if sha256_file(args.weights_dir / "config.json") != candidate["config_sha256"]:
            raise fz.DataIntegrityError("config diferente do pré-registro")
        series = fz.load_daily_series(prereg["data"])
        run.dataset = {
            "archive_sha256": prereg["data"]["archive_sha256"],
            "member_sha256": series.member_sha256,
        }
        period = prereg["evaluation_period"]
        indices = fz.target_indices(
            series,
            first_ms=fz.parse_utc_ms(period["first_target_open_utc"]),
            last_ms=fz.parse_utc_ms(period["last_target_open_utc"]),
        )
        levels = forecast["quantile_levels"]
        torch.manual_seed(0)
        pipeline = BaseChronosPipeline.from_pretrained(str(args.weights_dir), device_map="cpu")
        forecasts: dict[str, list[float]] = {}
        for start in range(0, len(indices), args.batch):
            chunk = indices[start : start + args.batch]
            contexts = [
                torch.tensor(series.close[max(0, j - CONTEXT_MAX) : j], dtype=torch.float32)
                for j in chunk
            ]
            quantiles, _ = pipeline.predict_quantiles(
                contexts, prediction_length=forecast["horizon_days"], quantile_levels=levels
            )
            for k, j in enumerate(chunk):
                forecasts[str(series.open_ms[j])] = [float(x) for x in quantiles[k, 0, :].tolist()]
        document = {
            "model": {
                "model_id": candidate["model_id"],
                "revision": candidate["revision"],
                "weights_sha256": candidate["weights_sha256"],
                "runtime_versions": versions,
                "device": "cpu",
            },
            "preregistration_sha256": prereg_sha,
            "quantile_levels": levels,
            "context_max": CONTEXT_MAX,
            "run_id": run.run_id,
            "forecasts": forecasts,
        }
        args.out.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
        body = {k: v for k, v in document.items() if k != "run_id"}
        run.metrics = {"n_forecasts": len(forecasts)}
        run.artifacts = {
            "forecasts": str(args.out),
            "forecasts_sha256": sha256_file(args.out),
            "forecasts_body_sha256": hashlib.sha256(
                json.dumps(body, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }
    print(json.dumps({"run_id": run.run_id, **run.metrics, **run.artifacts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
