"""Operational entrypoints implemented with predictor_ops public APIs."""

from __future__ import annotations

import argparse
import os
import sys
import threading
from collections.abc import Sequence
from pathlib import Path

from platformdirs import user_state_path
from predictor_ops import JobConfig, RunResult, RunStatus, run_job

from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB


def _state_root() -> Path:
    configured = os.getenv("PREDICTOR_OPS_STATE_DIR")
    return (
        Path(configured).expanduser().resolve()
        if configured
        else user_state_path("cripto-predictor")
    )


#: Ponto de partida para `exit_statuses`, espelhando o default do predictor_ops
#: (`JobConfig.exit_statuses`). Existe como constante para deixar explícito que
#: qualquer mapeamento por job COMPLETA este dict em vez de substituí-lo.
_EXIT_STATUSES_PADRAO = {0: RunStatus.SUCCEEDED, 2: RunStatus.PARTIAL}


def job_config(name: str, *, timeout_seconds: float | None = None) -> JobConfig:
    commands = {
        "phase1": [sys.executable, "-m", "GarimpoInvestimentos.phase1"],
        "backtest": [sys.executable, "-m", "GarimpoInvestimentos.analyzers.backtest"],
        "watchdog": [sys.executable, "-m", "GarimpoInvestimentos.observation_watchdog"],
        "v3-daily": [sys.executable, "-m", "GarimpoInvestimentos.v3.daily"],
        "observation-daily": [sys.executable, "-m", "GarimpoInvestimentos.observation_quality"],
        # Renovacao condicional do atestado de poder. A validade e de 7 dias e a
        # renovacao era 100% manual — vencido, o Experiment Registry recusa
        # QUALQUER trial nova. Agendar este job diariamente renova sozinho perto
        # do vencimento, sem gravar todo dia. Nao afrouxa nada: o atestado so e
        # gravado se o controle positivo passar, como sempre.
        "attest-renew": [
            sys.executable,
            "-m",
            "scripts.attest_harness",
            "--if-expiring-within",
            "2",
        ],
        "observation-live": [
            sys.executable,
            "-m",
            "GarimpoInvestimentos.observation_collect",
            "--live",
        ],
        "microstructure-live": [
            sys.executable,
            "-m",
            "GarimpoInvestimentos.trading.binance_spot_collector",
            "--symbol",
            "BTCUSDT",
            "ETHUSDT",
        ],
    }
    if name not in commands:
        raise ValueError(f"unknown job: {name}")
    artifact = FEATURE_STORE_DB if name in {"phase1", "backtest"} else None
    return JobConfig(
        id=f"cripto-{name}",
        command=commands[name],
        timeout_seconds=timeout_seconds or (252_000 if name == "phase1" else 1_800),
        heartbeat_interval_seconds=5,
        expected_artifact=artifact,
        provenance={"domain": "crypto", "scientific_change": False},
        scientific_state=(
            "COLLECTION_ONLY"
            if name in {"v3-daily", "observation-daily", "observation-live", "microstructure-live"}
            else None
        ),
        # phase1.py sai com 1 (GarimpoInvestimentos/phase1.py:348) sempre que ALGUM
        # juiz falha isoladamente (ex.: um provider sem créditos), mesmo com os
        # demais gravando previsões reais normalmente. Sem este mapeamento,
        # predictor_ops.run_job trata qualquer exit code fora de exit_statuses como
        # FAILED (runner.py:242, `exit_statuses.get(exit_code, FAILED)`) — o job
        # nunca mais reportaria SUCCEEDED enquanto aquele provider ficar
        # indisponível, mesmo saudável pros outros. phase1_watchdog.py já aceita
        # SUCCEEDED/PARTIAL como não-violação; PARTIAL é a leitura correta de
        # "1 gravado, N falha(s) isolada(s)".
        #
        # SEMPRE partir de _EXIT_STATUSES_PADRAO, nunca de {}. O campo tem
        # default_factory no predictor_ops; passar um dict explícito SUBSTITUI esse
        # default em vez de completá-lo. Entre 2026-08-19 (#32) e 2026-08-21, este
        # ponto passava `{}` para todo job que não fosse phase1 e `{1: PARTIAL}`
        # para o phase1 — o que apagou o `0: SUCCEEDED` do default e fez TODO job
        # reportar FAILED ao sair com 0, phase1 incluído. Efeito medido: o
        # watchdog.py exige `status == "SUCCEEDED"` do backtest diário e o
        # observation_watchdog exige SUCCEEDED/PARTIAL — nenhum dos dois podia ser
        # satisfeito, então o alarme tocava toda noite e um problema real ficaria
        # indistinguível do ruído.
        exit_statuses=(
            {**_EXIT_STATUSES_PADRAO, 1: RunStatus.PARTIAL}
            if name == "phase1"
            else dict(_EXIT_STATUSES_PADRAO)
        ),
        runtime={"backend": "local", "root": _state_root(), "lock_stale_after_seconds": 86_400},
    )


def execute_job(
    name: str, *, timeout_seconds: float | None = None, shutdown: threading.Event | None = None
) -> RunResult:
    return run_job(job_config(name, timeout_seconds=timeout_seconds), shutdown=shutdown)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run cripto-predictor jobs via predictor_ops")
    parser.add_argument(
        "job",
        choices=(
            "phase1",
            "backtest",
            "watchdog",
            "v3-daily",
            "observation-daily",
            "observation-live",
            "microstructure-live",
            "attest-renew",
        ),
    )
    parser.add_argument("--timeout", type=float)
    args = parser.parse_args(argv)
    result = execute_job(args.job, timeout_seconds=args.timeout)
    return 0 if result.run_status in {RunStatus.SUCCEEDED, RunStatus.PARTIAL} else result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
