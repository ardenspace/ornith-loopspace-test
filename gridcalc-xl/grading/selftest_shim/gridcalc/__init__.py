# Self-test shim: exposes the oracle's own naive reference as `gridcalc`
# so the oracle can be validated for internal consistency (counter-marked
# tests excluded — the naive reference does not model eval_count).
from gridcalc_xl_ref import RefWorkbook as Workbook

__all__ = ["Workbook"]
