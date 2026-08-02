"""Logging unificado — stdlib + predictor_core.obs.

Duas camadas:
  1. emit_event()  → JSONL estruturado (predictor_core.obs) — telemetria auditável
  2. logging.*     → propaga para os handlers do processo hospedeiro — depuração

Nenhum print() neste módulo. Nenhuma dependência de loguru.

NOTA (auditoria 2026-07-18): a antiga run_logging_setup() (handler de arquivo
rotativo logs/garimpo.log) foi REMOVIDA — não tinha nenhum call site desde a
refatoração de jul/2026 (logs/garimpo.log parado em 30/06 confirma), o docstring
que dizia "chamada em main.py" era falso, e reativá-la criaria um arquivo de log
SEM o filtro de redação de segredos (o caminho sancionado de produção,
scripts/garimpo_fase1.py, configura o próprio logging COM _RedactSecrets).
Quem precisar de log em arquivo num run manual deve rodar via
run_garimpo_fase1.bat (runner + redação) — nunca reintroduzir um handler de
arquivo aqui sem redação equivalente.
"""

import logging
import time

from predictor_core.obs import emit_event

_DOMAIN = "previsao_cripto"
_logger = logging.getLogger("previsao_cripto")

_LOG_STARTED: dict[str, float] = {}  # rastreia tempo de início por ativo (thread-local simples)


def log_start(ativo: str) -> None:
    """Marca início da análise de um ativo — evento estruturado + log local."""
    _LOG_STARTED[ativo] = time.monotonic()
    _logger.info("[inicio] %s", ativo.upper())
    emit_event(_DOMAIN, "pipeline_start", metrics={}, metadata={"ativo": ativo})


def log_success(ativo: str, score: float) -> None:
    """Conclusão com sucesso — inclui duração e score no evento."""
    duration_ms = int((time.monotonic() - _LOG_STARTED.pop(ativo, time.monotonic())) * 1000)
    _logger.info("[ok] %s — score %.1f (%.0f ms)", ativo.upper(), score, duration_ms)
    emit_event(
        _DOMAIN,
        "pipeline_success",
        metrics={"score": float(score), "duration_ms": float(duration_ms)},
        metadata={"ativo": ativo},
    )


def log_error(ativo: str, error: Exception) -> None:
    """Falha em qualquer etapa — tipo da exceção e mensagem no evento."""
    duration_ms = int((time.monotonic() - _LOG_STARTED.pop(ativo, time.monotonic())) * 1000)
    error_type = type(error).__name__
    _logger.error("[erro] %s — %s: %s", ativo.upper(), error_type, error)
    emit_event(
        _DOMAIN,
        "pipeline_error",
        metrics={"duration_ms": float(duration_ms)},
        metadata={"ativo": ativo, "error_type": error_type, "error_msg": str(error)[:200]},
    )
