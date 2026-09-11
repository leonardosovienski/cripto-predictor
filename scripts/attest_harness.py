"""Compatibility entrypoint; implementation ships in the domain wheel."""

import sys

from GarimpoInvestimentos.operational import attest_harness as _implementation

if __name__ == "__main__":
    raise SystemExit(_implementation.main())
else:
    sys.modules[__name__] = _implementation
