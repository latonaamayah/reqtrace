"""Pivot records into a 2D frequency table by two categorical dimensions."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from reqtrace.storage import RequestRecord


@dataclass
class PivotTable:
    """A 2-D frequency table."""

    row_label: str
    col_label: str
    rows: List[str] = field(default_factory=list)
    cols: List[str] = field(default_factory=list)
    cells: Dict[Tuple[str, str], int] = field(default_factory=dict)

    def get(self, row: str, col: str) -> int:
        return self.cells.get((row, col), 0)

    def __str__(self) -> str:  # pragma: no cover
        if not self.rows or not self.cols:
            return f"PivotTable({self.row_label} x {self.col_label}): empty"
        col_w = max(len(c) for c in self.cols)
        row_w = max(len(r) for r in self.rows)
        header = " " * (row_w + 2) + "  ".join(c.rjust(col_w) for c in self.cols)
        lines = [f"[{self.row_label} x {self.col_label}]", header]
        for r in self.rows:
            vals = "  ".join(str(self.get(r, c)).rjust(col_w) for c in self.cols)
            lines.append(f"{r.ljust(row_w)}  {vals}")
        return "\n".join(lines)


def _method_key(r: RequestRecord) -> str:
    return r.method.upper()


def _status_class_key(r: RequestRecord) -> str:
    return f"{r.response_status // 100}xx"


def _status_exact_key(r: RequestRecord) -> str:
    return str(r.response_status)


KeyFn = Callable[[RequestRecord], str]

_BUILTIN_KEYS: Dict[str, KeyFn] = {
    "method": _method_key,
    "status_class": _status_class_key,
    "status": _status_exact_key,
}


def pivot(
    records: List[RequestRecord],
    row_by: str | KeyFn = "method",
    col_by: str | KeyFn = "status_class",
) -> PivotTable:
    """Build a PivotTable from *records* using two key functions.

    *row_by* and *col_by* may be the names of built-in keys
    (``"method"``, ``"status_class"``, ``"status"``) or arbitrary callables.
    """
    row_fn: KeyFn = _BUILTIN_KEYS[row_by] if isinstance(row_by, str) else row_by
    col_fn: KeyFn = _BUILTIN_KEYS[col_by] if isinstance(col_by, str) else col_by
    row_label = row_by if isinstance(row_by, str) else "custom_row"
    col_label = col_by if isinstance(col_by, str) else "custom_col"

    counts: Dict[Tuple[str, str], int] = defaultdict(int)
    row_set: dict[str, None] = {}
    col_set: dict[str, None] = {}

    for rec in records:
        r_key = row_fn(rec)
        c_key = col_fn(rec)
        counts[(r_key, c_key)] += 1
        row_set[r_key] = None
        col_set[c_key] = None

    return PivotTable(
        row_label=row_label,
        col_label=col_label,
        rows=sorted(row_set),
        cols=sorted(col_set),
        cells=dict(counts),
    )
