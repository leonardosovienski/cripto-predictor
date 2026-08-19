"""h6_spearman_verdict() é o veredito científico da H6 — protege o gate
anti-data-snooping (pred_date > registered_at, fonte == H6_LIVE_FONTE).
Estes testes provam que linhas fora dessa janela nunca entram no n."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from GarimpoInvestimentos.analyzers.backtest import (
    H6_LIVE_FONTE,
    H6_MIN_N,
    H6_TRIAL_NAME,
    h6_spearman_verdict,
)

_HORIZON = 7
_KEY = f"var_d{_HORIZON}_pct"


def _trials_file(tmp_path, registered_at: str):
    path = tmp_path / "trials.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": H6_TRIAL_NAME,
                    "registered_at": registered_at,
                    "params": {"horizonte_dias": _HORIZON},
                    "sharpe": None,
                    "notes": "",
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


def _row(score: float, var_pct: float, fonte: str, pred_date: datetime) -> dict:
    return {"score": score, _KEY: var_pct, "fonte": fonte, "pred_date": pred_date}


def test_previsao_antes_do_registered_at_nao_entra_no_n(tmp_path):
    registered_at = datetime(2026, 7, 20, 7, 1, 59)
    trials_path = _trials_file(tmp_path, "2026-07-20T07:01:59Z")

    enriched = [
        _row(60, 0.01, H6_LIVE_FONTE, registered_at - timedelta(days=1)) for _ in range(H6_MIN_N)
    ]
    verdict = h6_spearman_verdict(enriched, _HORIZON, trials_path=trials_path)
    assert verdict["n"] == 0


def test_previsao_de_outra_fonte_nao_entra_no_n(tmp_path):
    registered_at = datetime(2026, 7, 20, 7, 1, 59)
    trials_path = _trials_file(tmp_path, "2026-07-20T07:01:59Z")

    enriched = [
        _row(60, 0.01, "direct", registered_at + timedelta(days=1)) for _ in range(H6_MIN_N)
    ]
    verdict = h6_spearman_verdict(enriched, _HORIZON, trials_path=trials_path)
    assert verdict["n"] == 0


def test_previsao_elegivel_entra_no_n(tmp_path):
    registered_at = datetime(2026, 7, 20, 7, 1, 59)
    trials_path = _trials_file(tmp_path, "2026-07-20T07:01:59Z")

    enriched = [
        _row(
            50 + (i % 5), 0.01 * ((i % 5) - 2), H6_LIVE_FONTE, registered_at + timedelta(days=i + 1)
        )
        for i in range(H6_MIN_N)
    ]
    verdict = h6_spearman_verdict(enriched, _HORIZON, trials_path=trials_path)
    assert verdict["n"] == H6_MIN_N
    assert "rho" in verdict


def test_mistura_de_elegiveis_e_nao_elegiveis_conta_so_os_elegiveis(tmp_path):
    registered_at = datetime(2026, 7, 20, 7, 1, 59)
    trials_path = _trials_file(tmp_path, "2026-07-20T07:01:59Z")

    eligible = [
        _row(
            50 + (i % 5), 0.01 * ((i % 5) - 2), H6_LIVE_FONTE, registered_at + timedelta(days=i + 1)
        )
        for i in range(5)
    ]
    pre_registration = [_row(60, 0.02, H6_LIVE_FONTE, registered_at - timedelta(days=10))]
    other_fonte = [_row(60, 0.02, "direct", registered_at + timedelta(days=1))]
    fallback_like = [_row(60, 0.02, "dpl:direct", registered_at + timedelta(days=1))]

    enriched = eligible + pre_registration + other_fonte + fallback_like
    verdict = h6_spearman_verdict(enriched, _HORIZON, trials_path=trials_path)
    assert verdict["n"] == len(eligible)


def test_sem_h6_registrada_retorna_none(tmp_path):
    path = tmp_path / "trials.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    verdict = h6_spearman_verdict([], _HORIZON, trials_path=path)
    assert verdict is None
