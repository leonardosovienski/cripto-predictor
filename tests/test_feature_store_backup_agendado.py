"""Backup agendado: nome unico por execucao e falha que se apresenta como falha.

Complementa os testes de backup/restore existentes cobrindo o que o AGENDAMENTO
exige, que e diferente do que o uso manual exige.
"""

from datetime import UTC, datetime

from predictor_ops import RunStatus

from GarimpoInvestimentos import jobs
from scripts.feature_store_backup import (
    DEFAULT_BACKUP_ROOT,
    timestamped_output,
)


def test_raiz_padrao_fica_fora_do_checkout(tmp_path):
    """Backup ao lado dos dados, nunca dentro do repositorio."""
    from GarimpoInvestimentos.core.paths import DATA_DIR

    assert DEFAULT_BACKUP_ROOT == DATA_DIR / "backups"


def test_nome_carrega_carimbo_de_tempo(tmp_path):
    quando = datetime(2026, 8, 24, 3, 54, 23, tzinfo=UTC)
    assert timestamped_output(tmp_path, now=quando).name == "fs-2026-08-24-035423"


def test_duas_execucoes_no_mesmo_segundo_nao_colidem(tmp_path):
    """create_backup recusa destino existente — corretamente. Sem nome novo, a
    tarefa agendada falharia da segunda vez em diante."""
    quando = datetime(2026, 8, 24, 3, 54, 23, tzinfo=UTC)
    primeiro = timestamped_output(tmp_path, now=quando)
    primeiro.mkdir(parents=True)
    segundo = timestamped_output(tmp_path, now=quando)
    assert segundo != primeiro
    assert not segundo.exists()


def test_backup_falho_reporta_FAILED_nunca_PARTIAL(tmp_path, monkeypatch):
    """O script sai com 2 em qualquer falha, e 2 -> PARTIAL no mapa padrao. Como
    os watchdogs aceitam SUCCEEDED/PARTIAL como saudavel, um backup que NAO
    aconteceu passaria despercebido. Nao existe backup parcial."""
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    mapa = jobs.job_config("backup").exit_statuses
    assert mapa[0] is RunStatus.SUCCEEDED
    assert 2 not in mapa, "exit 2 (falha do backup) nao pode virar PARTIAL"
    assert 1 not in mapa


def test_backup_e_um_job_declarado(tmp_path, monkeypatch):
    monkeypatch.setenv("PREDICTOR_OPS_STATE_DIR", str(tmp_path))
    comando = jobs.job_config("backup").command
    assert comando[-3:] == ["create", "--output-root"] or "--output-root" in comando
    assert "scripts.feature_store_backup" in comando
