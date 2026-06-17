"""Paths comuns dos testes do cripto — adiciona vendor/ (predictor_core) ao sys.path,
para que `from predictor_core...` funcione mesmo sem importar o pacote antes."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
_vendor = ROOT / "vendor"
if str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))
