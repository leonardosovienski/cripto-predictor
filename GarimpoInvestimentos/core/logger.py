"""Logging unificado — stdlib + predictor_core.obs.

Duas camadas:
  1. emit_event()  → JSONL estruturado (predictor_core.obs) — telemetria auditável
  2. logging.*     → console stderr + arquivo rotativo — depuração e operação

Nenhum print() neste módulo. Nenhuma dependência de loguru.
O handler de arquivo e console é configurado UMA vez por run_logging_setup() em main.py.
"""
import logging
import time
from pathlib import Path

from predictor_core.obs import emit_event

_DOMAIN = "previsao_cripto"
_logger = logging.getLogger("previsao_cripto")

_LOG_STARTED: set[str] = {}  # rastreia tempo de início por ativo (thread-local simples)


def run_logging_setup(log_dir: Path, level: str = "INFO") -> None:
    """Configura handler de arquivo rotativo + console. Chamar UMA vez em main.py."""
    if _logger.handlers:
        return  # idempotente

    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s",
                            datefmt="%Y-%m-%dT%H:%M:%S")

    # Console
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    _logger.addHandler(sh)

    # Arquivo rotativo (5 MB, sem dependência externa)
    try:
        from logging.handlers import RotatingFileHandler
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "garimpo.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        _logger.addHandler(fh)
    except OSError as exc:
        _logger.warning("logger: nao foi possivel criar arquivo de log (%s)", exc)

    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False


def log_start(ativo: str) -> None:
    """Marca início da análise de um ativo — evento estruturado + log local."""
    _LOG_STARTED[ativo] = time.monotonic()
    _logger.info("[inicio] %s", ativo.upper())
    emit_event(_DOMAIN, "pipeline_start",
               metrics={},
               metadata={"ativo": ativo})


def log_success(ativo: str, score: float) -> None:
    """Conclusão com sucesso — inclui duração e score no evento."""
    duration_ms = int((time.monotonic() - _LOG_STARTED.pop(ativo, time.monotonic())) * 1000)
    _logger.info("[ok] %s — score %.1f (%.0f ms)", ativo.upper(), score, duration_ms)
    emit_event(_DOMAIN, "pipeline_success",
               metrics={"score": float(score), "duration_ms": float(duration_ms)},
               metadata={"ativo": ativo})


def log_error(ativo: str, error: Exception) -> None:
    """Falha em qualquer etapa — tipo da exceção e mensagem no evento."""
    duration_ms = int((time.monotonic() - _LOG_STARTED.pop(ativo, time.monotonic())) * 1000)
    error_type = type(error).__name__
    _logger.error("[erro] %s — %s: %s", ativo.upper(), error_type, error)
    emit_event(_DOMAIN, "pipeline_error",
               metrics={"duration_ms": float(duration_ms)},
               metadata={"ativo": ativo, "error_type": error_type,
                         "error_msg": str(error)[:200]})
