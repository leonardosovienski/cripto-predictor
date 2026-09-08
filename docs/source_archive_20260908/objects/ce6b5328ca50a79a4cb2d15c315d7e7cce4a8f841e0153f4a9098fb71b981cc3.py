"""Cobertura do CircuitBreaker do V3 (antes: zero testes tocavam v3/ — Red Team jun/2026).

Trava a máquina de estados CLOSED → OPEN → HALF_OPEN → CLOSED e o data_quality_score
que propaga a degradação para o contrato de dados downstream.
"""

from GarimpoInvestimentos.v3.circuit_breaker import CircuitBreaker


def test_inicia_fechado_e_saudavel():
    cb = CircuitBreaker("t")
    assert cb.state == CircuitBreaker.CLOSED
    assert cb.data_quality_score == 1.0
    assert cb.can_attempt() is True


def test_falhas_abaixo_do_limiar_seguem_fechado():
    cb = CircuitBreaker("t", failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitBreaker.CLOSED
    assert cb.can_attempt() is True


def test_atinge_limiar_abre_o_circuito():
    cb = CircuitBreaker("t", failure_threshold=3, reset_timeout=999)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitBreaker.OPEN
    assert cb.data_quality_score == 0.0
    assert cb.can_attempt() is False  # antes do reset_timeout, bloqueia


def test_apos_timeout_vai_para_half_open_e_sonda():
    cb = CircuitBreaker("t", failure_threshold=1, reset_timeout=0.0)
    cb.record_failure()  # abre
    assert cb.state == CircuitBreaker.OPEN
    # reset_timeout=0 → can_attempt transita OPEN → HALF_OPEN imediatamente
    assert cb.can_attempt() is True
    assert cb.state == CircuitBreaker.HALF_OPEN
    assert cb.data_quality_score == 0.5


def test_sucesso_em_half_open_fecha_e_zera_contador():
    cb = CircuitBreaker("t", failure_threshold=1, reset_timeout=0.0)
    cb.record_failure()
    cb.can_attempt()  # → HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitBreaker.CLOSED
    assert cb.data_quality_score == 1.0
    # contador zerado: uma nova falha não reabre na hora (limiar > 1 exigiria mais)
    cb2 = CircuitBreaker("t2", failure_threshold=2, reset_timeout=0.0)
    cb2.record_failure()
    cb2.record_success()  # zera
    cb2.record_failure()  # 1/2 de novo, não 2/2
    assert cb2.state == CircuitBreaker.CLOSED


def test_falha_em_half_open_reabre():
    cb = CircuitBreaker("t", failure_threshold=1, reset_timeout=0.0)
    cb.record_failure()  # OPEN
    cb.can_attempt()  # HALF_OPEN
    cb.record_failure()  # falhou a sonda → reabre (limiar=1)
    assert cb.state == CircuitBreaker.OPEN
    assert cb.data_quality_score == 0.0


def test_sucesso_em_closed_mantem_fechado():
    cb = CircuitBreaker("t")
    cb.record_success()
    assert cb.state == CircuitBreaker.CLOSED
    assert cb.data_quality_score == 1.0
