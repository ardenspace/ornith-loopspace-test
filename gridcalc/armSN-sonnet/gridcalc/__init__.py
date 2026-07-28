import sys

# R12 requires evaluating reference chains up to 256 formula cells deep
# without raising; each hop through the evaluator (Sheet._compute ->
# evaluator.evaluate -> Sheet.ref_value -> Sheet._compute -> ...) spends a
# handful of Python stack frames, so raise the interpreter's recursion
# ceiling once here rather than hand-rolling an iterative engine (SPEC.md
# Engineer Lens sanctions this as an alternative to a fully iterative
# evaluator).
sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))

from .sheet import Sheet

__all__ = ["Sheet"]
