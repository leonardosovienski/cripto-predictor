"""Pacote GarimpoInvestimentos.

Configuração que vale para qualquer entry-point (`python -m GarimpoInvestimentos.*`):
no Windows o console em cp1252 levanta UnicodeEncodeError ao imprimir emojis,
então forçamos UTF-8 na saída logo na importação do pacote.
"""
import pathlib
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Consumidor do predictor_core via vendoring (linhagem idêntica ao stocks): a pasta
# vendor/ (irmã do pacote) entra no sys.path para `import predictor_core` funcionar.
_vendor = pathlib.Path(__file__).resolve().parent.parent / "vendor"
if _vendor.is_dir() and str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))
