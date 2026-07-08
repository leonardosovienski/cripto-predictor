"""Registro de tentativas + Deflated Sharpe Ratio — governança estatística.

Nasce no DOMÍNIO como candidato a promoção ao predictor_core (mesmo padrão da DPL:
o vendor não se edita localmente; evolução por demanda, promoção por sync).

Por quê: cada configuração avaliada contra os dados (ativo novo, horizonte, prompt,
feature, fonte) é uma TENTATIVA. Avaliar N configurações e reportar a melhor infla
o Sharpe esperado por pura sorte — E[max SR] cresce com N mesmo sem skill nenhum.
O DSR (Bailey & López de Prado, 2014) desconta isso: é o PSR calculado contra o
benchmark E[max SR | H0, N tentativas] em vez de contra zero.

`trials.json` é VERSIONADO de propósito: o desconto só é honesto se o denominador
(quantas tentativas houve) sobreviver ao esquecimento seletivo. Registrar uma
tentativa é barato; não registrar fabrica significância.

Unidades: os `sharpe` registrados e o DSR operam em unidade POR-PERÍODO (a mesma
que o PSR observa internamente — ex.: por-trade), NÃO anualizada. Misturar unidades
invalida o benchmark.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist, variance

from predictor_core.stats import probabilistic_sharpe_ratio

# Versionado junto do código (dentro do pacote) — viaja com o repositório.
TRIALS_PATH = Path(__file__).resolve().parent.parent / "trials.json"

_EULER = 0.5772156649015329  # γ de Euler–Mascheroni


# ---------- registro ----------

def load_trials(path: Path | None = None) -> list[dict]:
    p = Path(path or TRIALS_PATH)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def validate_trials(trials: list[dict]) -> list[str]:
    """Schema formal do registro (Experiment Registry). Retorna a lista de
    violações (vazia = conforme). A suíte falha se trials.json não conformar —
    o registro só protege o DSR se todo campo for interpretável.

    Obrigatórios: name (str não-vazio, sem espaços — identidade), registered_at
    (ISO-8601 UTC 'Z'), params (dict NÃO-vazio — a configuração exata), sharpe
    (None ou número finito, unidade por-período), notes (str).
    Opcionais tipados: features_used (list[str]), train_period/test_period
    ([início, fim] ISO-8601).
    """
    errs: list[str] = []
    seen: set[str] = set()
    for i, t in enumerate(trials):
        tag = f"trial[{i}]"
        name = t.get("name")
        if not isinstance(name, str) or not name or " " in name:
            errs.append(f"{tag}: name inválido ({name!r}) — str não-vazia sem espaços")
        elif name in seen:
            errs.append(f"{tag}: name duplicado ({name!r}) — identidade precisa ser única")
        else:
            seen.add(name)
            tag = f"trial[{name}]"
        ra = t.get("registered_at", "")
        try:
            datetime.strptime(ra, "%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            errs.append(f"{tag}: registered_at inválido ({ra!r}) — use ISO-8601 UTC 'Z'")
        params = t.get("params")
        if not isinstance(params, dict) or not params:
            errs.append(f"{tag}: params precisa ser dict NÃO-vazio (a configuração exata "
                        "é o que permite ao DSR distinguir tentativas)")
        sharpe = t.get("sharpe")
        if sharpe is not None and not (isinstance(sharpe, (int, float))
                                       and math.isfinite(sharpe)):
            errs.append(f"{tag}: sharpe inválido ({sharpe!r}) — None ou número finito")
        if not isinstance(t.get("notes", ""), str):
            errs.append(f"{tag}: notes precisa ser str")
        for key in ("train_period", "test_period"):
            per = t.get(key)
            if per is not None and not (isinstance(per, list) and len(per) == 2
                                        and all(isinstance(x, str) for x in per)):
                errs.append(f"{tag}: {key} inválido — [início, fim] ISO-8601")
        fu = t.get("features_used")
        if fu is not None and not (isinstance(fu, list)
                                   and all(isinstance(x, str) for x in fu)):
            errs.append(f"{tag}: features_used inválido — list[str]")
    return errs


def register_trial(name: str, *, params: dict, sharpe: float | None = None,
                   notes: str = "", path: Path | None = None, **extra) -> list[dict]:
    """Registra (ou atualiza) uma tentativa. `name` é a identidade da CONFIGURAÇÃO.

    Governança de identidade (jul/2026): reexecutar a MESMA configuração atualiza
    a entrada (sharpe/notes); tentar "atualizar" uma trial existente com `params`
    DIFERENTES é erro — variação de hiperparâmetro é tentativa NOVA (N+1), e
    escondê-la num update fabricaria significância que o DSR não desconta.
    `extra` aceita os campos opcionais do schema (features_used, train_period,
    test_period). Valida o schema antes de gravar. Retorna a lista completa."""
    p = Path(path or TRIALS_PATH)
    trials = load_trials(p)
    entry = {
        "name": name,
        "registered_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": params,
        "sharpe": sharpe,
        "notes": notes,
        **extra,
    }
    for i, t in enumerate(trials):
        if t.get("name") == name:
            if t.get("params") != params:
                raise ValueError(
                    f"trial '{name}' já existe com params DIFERENTES — variação de "
                    "configuração é tentativa nova: registre com um name novo (N+1). "
                    f"registrado={t.get('params')!r} vs proposto={params!r}")
            entry["registered_at"] = t.get("registered_at", entry["registered_at"])
            trials[i] = entry
            break
    else:
        trials.append(entry)
    errs = validate_trials(trials)
    if errs:
        raise ValueError("registro violaria o schema de trials: " + "; ".join(errs))
    p.write_text(json.dumps(trials, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return trials


# ---------- Deflated Sharpe Ratio ----------

def expected_max_sharpe(n_trials: int, var_trials_sr: float) -> float:
    """E[max SR] sob H0 (nenhuma tentativa tem skill) para N tentativas.

    Aproximação de máximo de gaussianas (López de Prado 2014, eq. do E[max]):
    sqrt(V[SR]) * ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))). Com 1 tentativa ou
    variância nula entre tentativas, não há seleção → benchmark 0."""
    if n_trials <= 1 or var_trials_sr <= 0:
        return 0.0
    nd = NormalDist()
    z1 = nd.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = nd.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trials_sr) * ((1.0 - _EULER) * z1 + _EULER * z2)


def deflated_sharpe_ratio(returns: list, trial_sharpes: list) -> dict:
    """DSR = PSR(returns, SR0), SR0 = E[max SR] dado o nº de tentativas registradas.

    `trial_sharpes`: SRs por-período das tentativas (None/±inf são tolerados no
    registro — contam no N, ficam fora da variância). Retorna
    {dsr, sr0, n_trials}; dsr é P(SR verdadeiro > máximo esperado por sorte)."""
    n = len(trial_sharpes)
    finite = [s for s in trial_sharpes if s is not None and math.isfinite(s)]
    var = variance(finite) if len(finite) >= 2 else 0.0
    sr0 = expected_max_sharpe(n, var)
    return {
        "dsr": probabilistic_sharpe_ratio(returns, benchmark_sharpe=sr0),
        "sr0": sr0,
        "n_trials": n,
    }
