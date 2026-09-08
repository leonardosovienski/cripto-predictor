"""Pacote GarimpoInvestimentos.

Configuração que vale para qualquer entry-point (`python -m GarimpoInvestimentos.*`):
no Windows o console em cp1252 levanta UnicodeEncodeError ao imprimir emojis,
então forçamos UTF-8 na saída logo na importação do pacote.
"""

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue] — nem todo TextIO tem
    except (AttributeError, ValueError):
        # best-effort: stream redirecionado (pipe/arquivo) pode não ter reconfigure
        # ou já estar fechado. Só esses casos são toleráveis — não engolir o resto.
        pass

__version__ = "1.0.0"
