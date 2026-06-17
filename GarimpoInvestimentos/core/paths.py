import os
from pathlib import Path

# Raiz do projeto = a pasta que contém o pacote GarimpoInvestimentos.
# Resolvido a partir deste arquivo (não do diretório de onde se executa),
# para que output/ e logs/ caiam sempre no mesmo lugar.
ROOT = Path(__file__).resolve().parents[2]

# Permite sobrescrever o diretório de saída (usado pela flag --output-dir,
# que seta GARIMPO_OUTPUT_DIR antes de importar este módulo).
OUTPUT_DIR = Path(os.getenv("GARIMPO_OUTPUT_DIR") or (ROOT / "output"))
LOGS_DIR = Path(os.getenv("GARIMPO_LOGS_DIR") or (ROOT / "logs"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
