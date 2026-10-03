"""Covered/total counts per coverage kind, for checks and parity.

One flat table across code coverage, covergroups and cover directives::

    {"line": BinStats(total=11, covered=11), "covergroup": ..., ...}

Kinds use covsight's names (see :data:`KINDS`); a kind with no points is
left out.  Covergroup counts are over type-level coverpoint and cross bins.
Ignore, illegal and default bins are excluded.
"""
from __future__ import annotations

from typing import Dict

from .code_coverage import DIRECTIVE_KINDS, KINDS as CODE_KINDS, CodeCoverage
from .metrics import BinStats

#: Every kind :func:`kind_totals` can report, in display order.
KINDS = CODE_KINDS + ("covergroup",) + DIRECTIVE_KINDS


def _bin_hit(b) -> bool:
    return b.count >= max(getattr(b, "at_least", 1) or 0, 1)


def covergroup_totals(db) -> BinStats:
    from .coverage_report_builder import CoverageReportBuilder
    stats = BinStats()
    for cg in CoverageReportBuilder.build(db).covergroups:
        for item in list(cg.coverpoints) + list(cg.crosses):
            for b in item.bins:
                stats = stats + BinStats(1, int(_bin_hit(b)))
    return stats


def kind_totals(db) -> Dict[str, BinStats]:
    """``{kind: BinStats}`` for every kind with at least one point."""
    code = CodeCoverage(db)
    ret: Dict[str, BinStats] = {}
    for kind, st in code.by_kind(CODE_KINDS).items():
        if st.total:
            ret[kind] = st
    cg = covergroup_totals(db)
    if cg.total:
        ret["covergroup"] = cg
    for kind, st in code.by_kind(DIRECTIVE_KINDS).items():
        if st.total:
            ret[kind] = st
    return {k: ret[k] for k in KINDS if k in ret}


def format_ratio(st: BinStats) -> str:
    """``"covered/total"``, the form ``expect.yaml`` uses."""
    return "%d/%d" % (st.covered, st.total)
