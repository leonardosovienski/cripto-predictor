"""Prompt 3c: foundation model zero-shot (Chronos) contra baselines ingênuos, sob pré-registro.

O pré-registro (`docs/evidence/2026-09-24-prompt3c/preregistro.json`) fixa dados, corte de
contaminação, período, horizonte, quantis, baselines, métricas, regra de estratégia, custos e
critérios de amostra ANTES de qualquer previsão. Este módulo não escolhe nada: lê o pré-registro.

Duas etapas, as duas no ledger de execuções (`run_ledger.recorded_run`):
  1. previsão: script de evidência num venv separado com chronos/torch, que ficam fora das
     dependências do projeto. Grava os quantis de PREÇO por dia-alvo;
  2. avaliação (este módulo, só stdlib + core): perda quantílica/CRPS/WQL, Diebold-Mariano,
     poder (MDE), estratégia com custos, PSR/DSR/PBO e decisão pela política versionada.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

from predictor_core.measurement.metrics import diebold_mariano
from predictor_core.measurement.trials import DeflationNotEstimableError

from GarimpoInvestimentos.analyzers.trials import TRIALS_PATH, load_trials
from GarimpoInvestimentos.research import strategy_metrics as sm
from GarimpoInvestimentos.research.decision_policy import (
    CandidateEvidence,
    SeedResult,
    decide,
    load_policy,
)
from GarimpoInvestimentos.research.forecast_metrics import (
    crps_from_quantiles,
    mean_quantile_loss,
    weighted_quantile_loss,
)
from GarimpoInvestimentos.run_ledger import RunLedger, canonical_sha256, recorded_run
from GarimpoInvestimentos.v3.cost_spec import CostSpec

DAY_MS = 86_400_000
_REPO_ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION_PATH = _REPO_ROOT / "docs/evidence/2026-09-24-prompt3c/preregistro.json"
FORECAST_BASELINES = ("historical_quantiles_365", "gaussian_random_walk_365")
# Transcritos do texto do pré-registro (testados contra ele); não são parâmetros livres.
_BASELINE_WINDOW = 365  # nome dos baselines: "..._365"
_ALPHA = 0.05  # forecast_metrics.test: "alpha 0,05"
_RELEVANT_FORECAST_EFFECT = 0.05  # forecast_metrics.relevant_effect: "redução relativa de 5%"


class DataIntegrityError(ValueError):
    """Dado local não confere com o pré-registro: nenhuma avaliação sai dele."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def load_preregistration(path: Path | str = PREREGISTRATION_PATH) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    return json.loads(raw), sha256_bytes(raw)


@dataclass(frozen=True)
class DailySeries:
    open_ms: tuple[int, ...]
    close: tuple[float, ...]
    member_sha256: str


def load_daily_series(data: Mapping[str, Any], *, root: Path = _REPO_ROOT) -> DailySeries:
    archive = root / data["archive"]
    archive_bytes = archive.read_bytes()
    if sha256_bytes(archive_bytes) != data["archive_sha256"]:
        raise DataIntegrityError(f"sha256 do arquivo não confere: {data['archive']}")
    with zipfile.ZipFile(archive) as zf:
        member = zf.read(data["member"])
    if sha256_bytes(member) != data["member_sha256"]:
        raise DataIntegrityError("sha256 do membro não confere")
    document = json.loads(gzip.decompress(member))
    columns = document["columns"]
    i_open, i_close = columns.index("open_ms"), columns.index(data["field"])
    rows = document["rows"]
    open_ms = tuple(int(r[i_open]) for r in rows)
    close = tuple(float(r[i_close]) for r in rows)
    return validate_series(open_ms, close, data, member_sha256=data["member_sha256"])


def validate_series(
    open_ms: Sequence[int], close: Sequence[float], data: Mapping[str, Any], *, member_sha256: str
) -> DailySeries:
    if len(open_ms) != data["rows"] or len(close) != len(open_ms):
        raise DataIntegrityError("número de linhas difere do pré-registro")
    if open_ms[0] != parse_utc_ms(data["first_open_utc"]) or open_ms[-1] != parse_utc_ms(
        data["last_open_utc"]
    ):
        raise DataIntegrityError("período dos dados difere do pré-registro")
    if any(b - a != DAY_MS for a, b in zip(open_ms, open_ms[1:], strict=False)):
        raise DataIntegrityError("série diária com lacuna ou duplicata")
    if any(not (math.isfinite(c) and c > 0) for c in close):
        raise DataIntegrityError("close não finito ou <= 0")
    return DailySeries(tuple(open_ms), tuple(close), member_sha256)


def target_indices(series: DailySeries, *, first_ms: int, last_ms: int) -> list[int]:
    return [j for j in range(1, len(series.open_ms)) if first_ms <= series.open_ms[j] <= last_ms]


def contamination_status(series: DailySeries, indices: Sequence[int], cutoff_ms: int) -> str:
    if not indices:
        return "POTENTIALLY_CONTAMINATED"
    if any(series.open_ms[j] < cutoff_ms for j in indices):
        raise DataIntegrityError("alvo anterior ao corte de contaminação")
    return "POST_CUTOFF"


def log_returns(close: Sequence[float]) -> list[float]:
    """r[j] = ln(C_j / C_{j−1}): o retorno realizado no dia j (r[0] = nan)."""
    return [float("nan")] + [math.log(b / a) for a, b in zip(close, close[1:], strict=False)]


def empirical_quantile(sorted_values: Sequence[float], tau: float) -> float:
    """Tipo 7 (Hyndman & Fan, 1996): interpolação linear entre estatísticas de ordem."""
    h = (len(sorted_values) - 1) * tau
    lo = math.floor(h)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (h - lo) * (sorted_values[hi] - sorted_values[lo])


def historical_quantiles(past: Sequence[float], levels: Sequence[float]) -> dict[float, float]:
    ordered = sorted(past)
    return {tau: empirical_quantile(ordered, tau) for tau in levels}


def gaussian_quantiles(past: Sequence[float], levels: Sequence[float]) -> dict[float, float]:
    s = statistics.stdev(past)
    nd = NormalDist()
    return {tau: s * nd.inv_cdf(tau) for tau in levels}


def baseline_forecasts(
    returns: Sequence[float], indices: Sequence[int], levels: Sequence[float]
) -> dict[str, list[dict[float, float]]]:
    """Só retornos realizados até a origem (dia j−1) entram na previsão do dia j."""
    out: dict[str, list[dict[float, float]]] = {name: [] for name in FORECAST_BASELINES}
    for j in indices:
        past = returns[j - _BASELINE_WINDOW : j]
        if j - _BASELINE_WINDOW < 1 or any(math.isnan(x) for x in past):
            raise DataIntegrityError("histórico insuficiente para o baseline de 365 dias")
        out["historical_quantiles_365"].append(historical_quantiles(past, levels))
        out["gaussian_random_walk_365"].append(gaussian_quantiles(past, levels))
    return out


def price_to_log_return_quantiles(
    price_quantiles: Sequence[float], levels: Sequence[float], origin_close: float
) -> dict[float, float]:
    if len(price_quantiles) != len(levels) or any(q <= 0 for q in price_quantiles):
        raise DataIntegrityError("quantis de preço inválidos")
    return {tau: math.log(q / origin_close) for tau, q in zip(levels, price_quantiles, strict=True)}


def candidate_forecasts(
    forecast_doc: Mapping[str, Any],
    prereg: Mapping[str, Any],
    series: DailySeries,
    indices: Sequence[int],
) -> list[dict[float, float]]:
    candidate = prereg["candidate"]
    model = forecast_doc["model"]
    for key in ("model_id", "revision", "weights_sha256"):
        if model.get(key) != candidate[key]:
            raise DataIntegrityError(f"previsão feita com {key} diferente do pré-registro")
    levels = prereg["forecast"]["quantile_levels"]
    if forecast_doc["quantile_levels"] != levels:
        raise DataIntegrityError("níveis de quantil diferentes do pré-registro")
    by_target = forecast_doc["forecasts"]
    out = []
    for j in indices:
        key = str(series.open_ms[j])
        if key not in by_target:
            raise DataIntegrityError(f"previsão ausente para o alvo {key}")
        out.append(price_to_log_return_quantiles(by_target[key], levels, series.close[j - 1]))
    return out


def mde_relative(
    diffs: Sequence[float], baseline_mean_loss: float, *, alpha: float, power: float
) -> float:
    nd = NormalDist()
    z = nd.inv_cdf(1 - alpha / 2) + nd.inv_cdf(power)
    return z * statistics.stdev(diffs) / math.sqrt(len(diffs)) / baseline_mean_loss


def mde_sharpe_annual(n: int, *, periods_per_year: int, alpha: float, power: float) -> float:
    nd = NormalDist()
    return (nd.inv_cdf(1 - alpha / 2) + nd.inv_cdf(power)) * math.sqrt(periods_per_year / n)


def long_flat_positions(signals: Sequence[float]) -> list[float]:
    return [1.0 if s > 0 else 0.0 for s in signals]


def strategy_net_returns(
    positions: Sequence[float], simple_returns: Sequence[float], per_leg_cost: float
) -> list[float]:
    """P&L_j = pos_j·r_j − custo·|pos_j − pos_{j−1}|, pos antes = 0, liquidação final cobrada."""
    net, previous = [], 0.0
    for p, r in zip(positions, simple_returns, strict=True):
        net.append(p * r - per_leg_cost * abs(p - previous))
        previous = p
    if net:
        net[-1] -= per_leg_cost * abs(previous)
    return net


def _forecast_summary(ys: Sequence[float], forecasts: Sequence[Mapping[float, float]]) -> dict:
    losses = [mean_quantile_loss(y, f) for y, f in zip(ys, forecasts, strict=True)]
    return {
        "losses": losses,
        "mean_quantile_loss": statistics.fmean(losses),
        "crps_q9": statistics.fmean(
            crps_from_quantiles(y, f) for y, f in zip(ys, forecasts, strict=True)
        ),
        "wql": weighted_quantile_loss(ys, forecasts),
    }


def _strategy_summary(net: Sequence[float], positions: Sequence[float], periods: int) -> dict:
    metrics = sm.strategy_metrics(net, positions, round_trip=False)
    sharpe = metrics["net_sharpe"]
    metrics["net_sharpe_annualized"] = (
        sharpe * math.sqrt(periods) if math.isfinite(sharpe) else None
    )
    metrics["total_net_return"] = math.prod(1 + x for x in net) - 1
    return {
        k: (None if isinstance(v, float) and not math.isfinite(v) else v)
        for k, v in metrics.items()
    }


def evaluate(
    prereg: Mapping[str, Any], series: DailySeries, forecast_doc: Mapping[str, Any]
) -> dict[str, Any]:
    fc, st = prereg["forecast_metrics"], prereg["strategy"]
    levels = prereg["forecast"]["quantile_levels"]
    alpha, power = _ALPHA, fc["power"]
    cutoff_ms = parse_utc_ms(prereg["contamination"]["cutoff_utc"])
    period = prereg["evaluation_period"]
    indices = target_indices(
        series,
        first_ms=parse_utc_ms(period["first_target_open_utc"]),
        last_ms=parse_utc_ms(period["last_target_open_utc"]),
    )
    contamination = contamination_status(series, indices, cutoff_ms)
    report: dict[str, Any] = {"contamination_status": contamination, "n_targets": len(indices)}
    if contamination != "POST_CUTOFF":
        return report

    returns = log_returns(series.close)
    ys = [returns[j] for j in indices]
    forecasts = {"chronos_bolt_small": candidate_forecasts(forecast_doc, prereg, series, indices)}
    forecasts.update(baseline_forecasts(returns, indices, levels))
    summary = {name: _forecast_summary(ys, f) for name, f in forecasts.items()}
    best = min(FORECAST_BASELINES, key=lambda b: summary[b]["mean_quantile_loss"])
    candidate_losses = summary["chronos_bolt_small"]["losses"]
    tests = {}
    for b in FORECAST_BASELINES:
        dm, p = diebold_mariano(candidate_losses, summary[b]["losses"], h=1)
        tests[b] = {"dm_hln": dm, "p_value": p}
    diffs = [a - b for a, b in zip(candidate_losses, summary[best]["losses"], strict=True)]
    mde = mde_relative(diffs, summary[best]["mean_quantile_loss"], alpha=alpha, power=power)
    if mde > _RELEVANT_FORECAST_EFFECT:
        forecast_status = "INSUFFICIENT_SAMPLE"
    elif all(t["p_value"] < alpha and t["dm_hln"] < 0 for t in tests.values()):
        forecast_status = "CANDIDATE_BETTER"
    elif any(t["p_value"] < alpha and t["dm_hln"] > 0 for t in tests.values()):
        forecast_status = "CANDIDATE_WORSE"
    else:
        forecast_status = "NO_SIGNIFICANT_DIFFERENCE"

    simple = [series.close[j] / series.close[j - 1] - 1 for j in indices]
    per_leg = CostSpec().per_leg_bps / 10_000
    medians = [f[0.5] for f in forecasts["chronos_bolt_small"]]
    positions = {
        "chronos_bolt_small": long_flat_positions(medians),
        "random_walk": [0.0] * len(indices),
        "naive_persistence": long_flat_positions([returns[j - 1] for j in indices]),
        "always_long": [1.0] * len(indices),
    }
    periods = st["periods_per_year"]
    strategies = {
        name: _strategy_summary(strategy_net_returns(pos, simple, per_leg), pos, periods)
        for name, pos in positions.items()
    }
    # Diário e spot: sempre comprado com uma entrada e uma saída É o buy-and-hold.
    strategies["buy_and_hold"] = dict(strategies["always_long"])
    mde_sr = mde_sharpe_annual(len(indices), periods_per_year=periods, alpha=alpha, power=power)
    strategy_status = "INSUFFICIENT_SAMPLE" if mde_sr > st["relevant_sharpe_annual"] else "ADEQUATE"

    try:
        var_sr = sm.trial_sharpe_variance(load_trials(TRIALS_PATH))
        dsr = {"status": "ESTIMABLE", "var_trials_sr": var_sr}
    except DeflationNotEstimableError as exc:
        dsr = {"status": "NOT_ESTIMABLE", "reason": str(exc)}

    policy = load_policy()
    baseline_sharpes = {
        b: strategies[b]["net_sharpe"] for b in ("naive_persistence", "always_long", "buy_and_hold")
    }
    # Sempre fora: P&L identicamente zero, Sharpe 0/0. Convenção declarada: sem risco e sem
    # retorno, Sharpe 0.
    baseline_sharpes["random_walk"] = 0.0
    candidate_sharpe = strategies["chronos_bolt_small"]["net_sharpe"]
    decision = decide(
        CandidateEvidence(
            hypothesis_id=prereg["id"],
            registered_at_utc=prereg["registered_at_utc"],
            by_seed={
                0: SeedResult(
                    net_sharpe=candidate_sharpe if candidate_sharpe is not None else float("nan"),
                    dsr_by_n={},
                )
            },
            pbo=None,
            baselines_net_sharpe=baseline_sharpes,
            dataset_sha256=series.member_sha256,
            missing_fraction=0.0,
            n_oos_observations=len(indices),
        ),
        policy,
    )
    for name in summary:
        summary[name].pop("losses")
    report.update(
        {
            "first_target_utc": _iso(series.open_ms[indices[0]]),
            "last_target_utc": _iso(series.open_ms[indices[-1]]),
            "forecast": summary,
            "best_forecast_baseline": best,
            "diebold_mariano": tests,
            "mde_relative": mde,
            "forecast_status": forecast_status,
            "strategy": strategies,
            "mde_sharpe_annual": mde_sr,
            "strategy_status": strategy_status,
            "dsr": dsr,
            "pbo": {"status": "N/A", "reason": prereg["pbo"]},
            "decision": decision,
        }
    )
    return report


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_evaluation(
    *, prereg_path: Path, forecasts_path: Path, out_path: Path, ledger_path: Path
) -> dict[str, Any]:
    prereg, prereg_sha = load_preregistration(prereg_path)
    forecast_raw = forecasts_path.read_bytes()
    forecast_doc = json.loads(forecast_raw)
    policy = load_policy()
    with recorded_run(
        RunLedger(ledger_path),
        kind="fm_zero_shot_evaluation",
        config={
            "preregistration_id": prereg["id"],
            "preregistration_sha256": prereg_sha,
            "forecasts_sha256": sha256_bytes(forecast_raw),
            "forecast_run_id": forecast_doc.get("run_id"),
        },
        costs={**CostSpec().as_dict(), "funding": "não se aplica (spot)"},
        validation_protocol={
            "contamination": prereg["contamination"],
            "evaluation_period": prereg["evaluation_period"],
            "forecast": prereg["forecast"],
        },
        model=prereg["candidate"],
        seeds=[0],
        policy=policy.reference(),
    ) as run:
        series = load_daily_series(prereg["data"])
        run.dataset = {
            "archive_sha256": prereg["data"]["archive_sha256"],
            "member_sha256": series.member_sha256,
            "interval": [_iso(series.open_ms[0]), _iso(series.open_ms[-1])],
        }
        report = evaluate(prereg, series, forecast_doc)
        report["run_id"] = run.run_id
        out_path.write_text(
            json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        run.metrics = {
            "contamination_status": report["contamination_status"],
            "n_targets": report["n_targets"],
            "forecast_status": report.get("forecast_status"),
            "strategy_status": report.get("strategy_status"),
            "decision": report.get("decision", {}).get("decision"),
        }
        run.baselines = {
            "forecast": list(FORECAST_BASELINES),
            "strategy": ["random_walk", "naive_persistence", "always_long", "buy_and_hold"],
        }
        run.artifacts = {"report": str(out_path), "report_sha256": canonical_sha256(report)}
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Avaliação pré-registrada do Chronos zero-shot")
    parser.add_argument("--prereg", type=Path, default=PREREGISTRATION_PATH)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_evaluation(
        prereg_path=args.prereg,
        forecasts_path=args.forecasts,
        out_path=args.out,
        ledger_path=args.ledger,
    )
    print(
        json.dumps(
            {
                k: report.get(k)
                for k in (
                    "run_id",
                    "contamination_status",
                    "n_targets",
                    "forecast_status",
                    "strategy_status",
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
