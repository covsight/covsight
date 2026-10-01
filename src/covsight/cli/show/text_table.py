"""Plain-text tables for the show commands' text output.

Stats cells are the dicts produced by
``covsight.analysis.code_coverage.stats_dict``
(``{"covered", "total", "coverage"}``).
"""
from typing import Dict, List, Sequence, TextIO, Tuple


def _cell(st) -> str:
    if not st or not st.get("total"):
        return "-"
    return "%6.2f%% %d/%d" % (st["coverage"], st["covered"], st["total"])


def _write(fp: TextIO, header: Sequence[str], rows: List[Sequence[str]]):
    widths = [len(h) for h in header]
    for row in rows:
        widths = [max(w, len(c)) for w, c in zip(widths, row)]
    fmt = "  ".join("%%-%ds" % w if i == 0 else "%%%ds" % w
                    for i, w in enumerate(widths))
    fp.write((fmt % tuple(header)).rstrip() + "\n")
    fp.write("  ".join("-" * w for w in widths) + "\n")
    for row in rows:
        fp.write((fmt % tuple(row)).rstrip() + "\n")


def stats_table(fp: TextIO, label: str, rows: List[Tuple[str, Dict]]):
    """One row per (label, stats): covered, total and percentage columns."""
    _write(fp, (label, "Covered", "Total", "Coverage"),
           [(name, str(st["covered"]), str(st["total"]),
             "%.2f%%" % st["coverage"]) for name, st in rows])


def matrix_table(fp: TextIO, label: str, kinds: Sequence[str],
                 rows: List[Tuple[str, Dict[str, Dict]]]):
    """One row per (label, {kind: stats}), one column per kind."""
    _write(fp, [label] + list(kinds),
           [[name] + [_cell(by_kind.get(k)) for k in kinds]
            for name, by_kind in rows])
