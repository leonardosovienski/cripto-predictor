from loguru import logger

from GarimpoInvestimentos.core.paths import LOGS_DIR

# Configuração do Loguru (rotaciona a cada 5 MB)
logger.add(
    str(LOGS_DIR / "garimpo.log"),
    rotation="5 MB",
    level="INFO",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}"
)

def log_start(ativo: str):
    logger.info(f"🔎 Iniciando análise de {ativo.upper()}...")

def log_success(ativo: str, score: float):
    logger.success(f"✅ {ativo.upper()} analisado com sucesso — Score final: {score}")

def log_error(ativo: str, error: Exception):
    logger.error(f"❌ Erro ao processar {ativo.upper()}: {error}")
