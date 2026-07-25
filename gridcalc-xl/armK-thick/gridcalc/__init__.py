"""gridcalc — in-memory multi-sheet spreadsheet engine."""

# R12: Raise recursion limit to support 256-cell dependency chains and
# deeply nested expressions without RecursionError. This is the sole
# exception to R24's global-state hygiene, sanctioned by the spec.
import sys
sys.setrecursionlimit(10000)

from gridcalc.workbook import Workbook

__all__ = ["Workbook"]
