# Self-test shim: exposes the oracle's own naive reference as `gridcalc`
# so the oracle can be validated for internal consistency (R10 excluded).
from gridcalc_ref import RefSheet as Sheet

__all__ = ["Sheet"]
