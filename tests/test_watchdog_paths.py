"""watchdog.py apontava para o checkout, nao para onde os dados de fato vivem.

Ate 2026-08-24, tres checagens deste modulo liam caminhos que o resto do
projeto nunca escreve: o banco (ROOT/output/feature_store.db em vez de
core.paths.FEATURE_STORE_DB), o heartbeat do backtest (um path e uma chave
JSON de uma era pre-predictor_ops) e os defaults de log/alerta. O sintoma
seria silencioso: o watchdog "funcionando" (sem traceback) mas nunca
discriminando coleta boa de coleta quebrada, porque nunca via o dado real.

Este arquivo tambem cobre o check novo, _check_h6_bridge: a ponte
producao->git do n da H6 so atravessa por commit humano, e ate 2026-08-22
ela nunca tinha sido atravessada nenhuma vez porque nada avisava que estava
parada.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta

from predictor_ops import JobConfig, run_job

from GarimpoInvestimentos import watchdog


def test_db_path_bate_com_core_paths():
    from GarimpoInvestimentos.core.paths import FEATURE_STORE_DB

    assert watchdog.DB_PATH == FEATURE_STORE_DB


def test_log_e_alerta_nao_apontam_para_o_checkout():
    assert not str(watchdog.LOG).startswith(str(watchdog.ROOT))
    assert not str(watchdog.ALERTA).startswith(str(watchdog.ROOT))


def test_heartbeat_do_backtest_le_o_schema_real_do_predictor_ops(tmp_path, monkeypatch):
    """Roda um job de verdade (nao um mock) e confere que o watchdog encontra
    e aprova o heartbeat que o runner realmente escreveu — o path e a chave
    antigos (ROOT/logs/operations/GarimpoBacktest.heartbeat.json, chave
    'status') nunca teriam encontrado isto: nem o path nem a chave existem
    no schema do predictor_ops."""
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    ok = JobConfig(
        id="cripto-backtest",
        command=[sys.executable, "-c", "import sys; sys.exit(0)"],
        timeout_seconds=10,
        heartbeat_interval_seconds=0.05,
        runtime={"root": tmp_path, "lock_stale_after_seconds": 30},
    )
    resultado = run_job(ok)
    assert resultado.run_status.value == "SUCCEEDED"

    problemas: list[str] = []
    watchdog._check_backtest_heartbeat(problemas)
    assert problemas == [], f"heartbeat SUCCEEDED real nao foi reconhecido: {problemas}"


def test_heartbeat_ausente_ainda_e_relatado(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    problemas: list[str] = []
    watchdog._check_backtest_heartbeat(problemas)
    assert len(problemas) == 1
    assert "nunca rodou" in problemas[0]


def test_heartbeat_com_status_diferente_de_succeeded_e_relatado(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    falho = JobConfig(
        id="cripto-backtest",
        command=["python3", "-c", "import sys; sys.exit(1)"],
        timeout_seconds=10,
        heartbeat_interval_seconds=0.05,
        runtime={"root": tmp_path, "lock_stale_after_seconds": 30},
    )
    run_job(falho)
    problemas: list[str] = []
    watchdog._check_backtest_heartbeat(problemas)
    assert len(problemas) == 1
    assert "FAILED" in problemas[0]


def _historico(tmp_path, *linhas):
    caminho = tmp_path / "output" / "quality_snapshot_history.jsonl"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        for linha in linhas:
            f.write(json.dumps(linha) + "\n")
    return caminho


def _publica(tmp_path, *, n: int, observed_at: datetime) -> None:
    destino = tmp_path / "GarimpoInvestimentos" / "h6_status.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps({"n": n, "observed_at": observed_at.isoformat()}), encoding="utf-8"
    )


def test_bridge_sem_historico_local_nao_alarma(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert problemas == []


def test_bridge_nunca_publicada_com_n_local_positivo_alarma(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    _historico(tmp_path, {"h6_valid_n": 6})
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert len(problemas) == 1
    assert "nunca foi publicado" in problemas[0]


def test_bridge_estado_publicado_igual_ao_local_nao_alarma_mesmo_velho(tmp_path, monkeypatch):
    """Arquivo publicado antigo, mas com o MESMO n do local: nada mudou, nada
    para commitar. Idade sozinha nunca deve disparar o alarme."""
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    _historico(tmp_path, {"h6_valid_n": 6})
    _publica(tmp_path, n=6, observed_at=datetime.now(UTC) - timedelta(days=30))
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert problemas == []


def test_bridge_local_avancou_e_publicado_velho_alarma(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    _historico(tmp_path, {"h6_valid_n": 6}, {"h6_valid_n": 18})
    _publica(tmp_path, n=6, observed_at=datetime.now(UTC) - timedelta(days=5))
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert len(problemas) == 1
    assert "desatualizado" in problemas[0]
    assert "n=6" in problemas[0] and "n=18" in problemas[0]


def test_bridge_local_avancou_mas_ainda_recente_nao_alarma(tmp_path, monkeypatch):
    """Divergencia real, mas dentro da janela de tolerancia — nao e' incidente
    ainda, e' o dia a dia de uma coleta em andamento."""
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    _historico(tmp_path, {"h6_valid_n": 18})
    _publica(tmp_path, n=6, observed_at=datetime.now(UTC) - timedelta(hours=12))
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert problemas == []


def test_bridge_le_ultima_linha_do_historico_nao_a_primeira(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "DATA_DIR", tmp_path)
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    _historico(tmp_path, {"h6_valid_n": 30}, {"h6_valid_n": 6})
    _publica(tmp_path, n=6, observed_at=datetime.now(UTC) - timedelta(days=5))
    problemas: list[str] = []
    watchdog._check_h6_bridge(problemas)
    assert problemas == [], "deveria usar a ULTIMA linha (n=6), que bate com o publicado"
