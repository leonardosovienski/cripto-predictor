from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest
from predictor_ops import JobConfig, RunStatus, run_job

from GarimpoInvestimentos import jobs
from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB
from GarimpoInvestimentos.v3 import daily


def _job(tmp_path: Path, code: str, *, timeout: float = 5, environment=None) -> JobConfig:
    return JobConfig(
        id="contract-job",
        command=[sys.executable, "-c", code],
        timeout_seconds=timeout,
        heartbeat_interval_seconds=0.05,
        environment=environment or {},
        runtime={"root": tmp_path, "lock_stale_after_seconds": 30},
    )


def test_public_job_config_uses_installed_module_and_no_checkout_cwd(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("watchdog", timeout_seconds=2)
    assert config.command[:2] == [sys.executable, "-m"]
    assert config.cwd is None
    assert config.runtime.root == tmp_path
    with pytest.raises(ValueError, match="unknown job"):
        jobs.job_config("invalid")


def test_v3_daily_is_supervised_and_propagates_collection_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    assert jobs.job_config("v3-daily").command[-1] == "GarimpoInvestimentos.v3.daily"
    assert jobs.job_config("v3-daily").scientific_state == "COLLECTION_ONLY"
    planned = daily.commands(("BTCUSDT",), start_date="2021-01-01", end_date="2026-01-01")
    assert planned[-1][-2:] == ["--date", "2026-01-01"]
    assert [command[2] for command in planned] == [
        "GarimpoInvestimentos.observation_collect",
    ]
    assert all("paper" not in part for command in planned for part in command)

    calls = []

    def fail_collection(command, check):
        calls.append((command, check))
        return type("Completed", (), {"returncode": 7})()

    monkeypatch.setattr(daily.subprocess, "run", fail_collection)
    assert daily.main() == 7
    assert len(calls) == 1


def test_phase1_exit_code_1_maps_to_partial_not_failed(tmp_path, monkeypatch):
    """phase1.py sai com 1 quando algum juiz falha isoladamente (ex.: provider sem
    creditos) mesmo gravando previsoes reais para os demais. Sem exit_statuses, o
    predictor_ops trataria isso como FAILED para sempre enquanto aquele provider
    ficar indisponivel — phase1_watchdog.py so aceita SUCCEEDED/PARTIAL."""
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("phase1")
    assert config.exit_statuses[1] is RunStatus.PARTIAL
    # E o mapeamento do 1 NAO pode custar o do 0: ver
    # test_saida_limpa_e_SUCCEEDED_em_todo_job abaixo.
    assert config.exit_statuses[0] is RunStatus.SUCCEEDED

    isolated_failure_job = _job(tmp_path, "import sys; sys.exit(1)")
    isolated_failure_job = JobConfig(
        **{**isolated_failure_job.model_dump(), "exit_statuses": {1: RunStatus.PARTIAL}}
    )
    result = run_job(isolated_failure_job)
    assert result.run_status == RunStatus.PARTIAL
    assert result.exit_code == 1


def test_other_jobs_do_not_get_the_partial_mapping(tmp_path, monkeypatch):
    """So o phase1 ganha o 1 -> PARTIAL. Os demais ficam com o default e nada mais.

    A versao anterior deste teste exigia `== {}` e, com isso, TRAVAVA um defeito:
    dict vazio substitui o default do predictor_ops em vez de completa-lo, entao
    exit 0 caia no fallback FAILED (runner.py:242).
    """
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    for name in ("backtest", "watchdog", "v3-daily", "observation-daily", "observation-live"):
        mapa = jobs.job_config(name).exit_statuses
        assert 1 not in mapa, f"{name} nao deve herdar o mapeamento do phase1"
        assert mapa[0] is RunStatus.SUCCEEDED


def test_saida_limpa_e_SUCCEEDED_em_todo_job(tmp_path, monkeypatch):
    """Contrato mais basico do runner: quem sai com 0 reportou sucesso.

    Nao basta inspecionar o dict — este teste RODA o runner, porque o defeito
    original vivia na interacao entre o dict e o fallback do predictor_ops, e
    nenhuma assercao sobre o dict sozinho o teria pego. Consequencia pratica de
    perder isso: watchdog.py exige `status == "SUCCEEDED"` do backtest diario e
    observation_watchdog exige SUCCEEDED/PARTIAL — com exit 0 virando FAILED,
    ambos alarmavam toda noite e afogavam qualquer problema real.
    """
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    for name in ("phase1", "backtest", "watchdog", "v3-daily", "observation-daily"):
        base = jobs.job_config(name)
        limpo = JobConfig(
            **{
                **base.model_dump(),
                "id": f"exit0-{name}",
                "command": [sys.executable, "-c", "import sys; sys.exit(0)"],
                "timeout_seconds": 30,
                "heartbeat_interval_seconds": 0.05,
                "expected_artifact": None,
                "runtime": {"root": tmp_path, "lock_stale_after_seconds": 30},
            }
        )
        resultado = run_job(limpo)
        assert resultado.exit_code == 0
        assert resultado.run_status is RunStatus.SUCCEEDED, (
            f"{name}: saida limpa reportada como {resultado.run_status.value}"
        )


def test_live_observation_job_is_collection_only(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("observation-live")
    assert config.scientific_state == "COLLECTION_ONLY"
    assert config.command[-2:] == ["GarimpoInvestimentos.observation_collect", "--live"]


def test_job_cli_maps_operational_status(monkeypatch):
    succeeded = type("Result", (), {"run_status": RunStatus.SUCCEEDED, "exit_code": 0})()
    failed = type("Result", (), {"run_status": RunStatus.FAILED, "exit_code": 9})()
    monkeypatch.setattr(jobs, "execute_job", lambda *args, **kwargs: succeeded)
    assert jobs.main(["watchdog", "--timeout", "1"]) == 0
    monkeypatch.setattr(jobs, "execute_job", lambda *args, **kwargs: failed)
    assert jobs.main(["watchdog"]) == 9


def test_timeout_shutdown_heartbeat_events_and_redaction(tmp_path):
    secret = "synthetic-serp-secret-123456"
    leaking = _job(
        tmp_path,
        "import os,sys,time; print(os.environ['SERP_API_KEY']); print(os.environ['SERP_API_KEY'], file=sys.stderr); time.sleep(5)",
        timeout=1.0,
        environment={"SERP_API_KEY": secret},
    )
    result = run_job(leaking)
    assert result.exit_code == 124 and result.run_status == RunStatus.FAILED
    serialized = json.dumps(result.record)
    assert secret not in serialized and "[REDACTED]" in serialized
    root = tmp_path / leaking.id
    assert json.loads((root / "heartbeat.json").read_text())["run_status"] == "FAILED"
    assert secret not in (root / "events.jsonl").read_text()

    stop = threading.Event()
    stop.set()
    shutdown = run_job(_job(tmp_path, "import time; time.sleep(5)"), shutdown=stop)
    assert shutdown.exit_code == 130
    assert shutdown.record["termination"]["reason"] == "shutdown"


def test_lock_prevents_concurrent_duplicate(tmp_path):
    job = _job(tmp_path, "import time; time.sleep(0.5)")
    first: list = []
    thread = threading.Thread(target=lambda: first.append(run_job(job)))
    thread.start()
    time.sleep(0.1)
    second = run_job(job)
    thread.join()
    assert second.run_status == RunStatus.SKIPPED
    assert first[0].run_status == RunStatus.SUCCEEDED


def test_job_attest_renew_existe_e_e_condicional():
    """A validade do atestado é de 7 dias e a renovação era 100% manual —
    vencido, o Experiment Registry recusa QUALQUER trial nova. O job renova
    perto do vencimento em vez de gravar todo dia."""
    from GarimpoInvestimentos.jobs import job_config

    cfg = job_config("attest-renew")
    assert "attest_harness" in " ".join(cfg.command)
    assert "--if-expiring-within" in cfg.command, "renovacao incondicional gravaria todo dia"


def test_expira_em_trata_ausente_ou_ilegivel_como_EXPIRADO(tmp_path, monkeypatch):
    """Na dúvida, renovar: o controle positivo roda de novo e custa segundos.
    Assumir validade de um arquivo que não dá para ler seria o erro caro."""
    import scripts.attest_harness as AH

    faltando = tmp_path / "nao_existe.json"
    monkeypatch.setattr(AH, "PHASE1_ATTESTATION_PATH", faltando)
    monkeypatch.setattr(AH, "attestation_path_for", lambda _p: faltando)
    assert AH._expira_em(1.0) is True

    corrompido = tmp_path / "corrompido.json"
    corrompido.write_text("{lixo", encoding="utf-8")
    monkeypatch.setattr(AH, "PHASE1_ATTESTATION_PATH", corrompido)
    monkeypatch.setattr(AH, "attestation_path_for", lambda _p: corrompido)
    assert AH._expira_em(1.0) is True


def test_expira_em_respeita_a_janela(tmp_path, monkeypatch):
    import json
    from datetime import UTC, datetime, timedelta

    import scripts.attest_harness as AH

    def _grava(dias):
        p = tmp_path / "att.json"
        expira = (datetime.now(UTC) + timedelta(days=dias)).isoformat()
        p.write_text(json.dumps({"expires_at": expira}), encoding="utf-8")
        monkeypatch.setattr(AH, "PHASE1_ATTESTATION_PATH", p)
        monkeypatch.setattr(AH, "attestation_path_for", lambda _p: p)

    _grava(10)
    assert AH._expira_em(2.0) is False  # folga grande -> nao renova
    _grava(1)
    assert AH._expira_em(2.0) is True  # dentro da janela -> renova
    _grava(-1)
    assert AH._expira_em(2.0) is True  # ja expirou -> renova


def test_quality_snapshot_e_um_job_declarado(tmp_path, monkeypatch):
    """Sem este job agendado, o historico local (quality_snapshot_history.jsonl)
    nunca existe fora de uma execucao manual — e watchdog._check_h6_bridge nao
    tem com o que comparar o que esta publicado em h6_status.json."""
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("quality-snapshot")
    assert config.command[-1] == "GarimpoInvestimentos.quality_snapshot"
    assert config.expected_artifact is None
    assert config.exit_statuses[0] is RunStatus.SUCCEEDED


def test_discover_e_um_job_declarado(tmp_path, monkeypatch):
    """Sem este job agendado, o unico caminho que amplia o universo era
    run_sinal_diario.bat, que nunca chegou a ser registrado no Task Scheduler —
    o universo ficava travado para sempre nos ativos originais. So ingestao
    (rede): main.py --ingest retorna antes de chamar qualquer LLM."""
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    config = jobs.job_config("discover")
    assert config.command[-2:] == ["--mode", "fallback"]
    assert "--discover" in config.command
    assert "--ingest" in config.command
    assert config.expected_artifact == FEATURE_STORE_DB
    assert config.exit_statuses[0] is RunStatus.SUCCEEDED
