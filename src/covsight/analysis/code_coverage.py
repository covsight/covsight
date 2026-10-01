"""Code coverage (line, branch, expression, toggle, FSM, ...) from any UCIS db.

``CodeCoverage`` walks the instance tree once and records one
:class:`CodeItem` per code-coverage bin, with its kind, instance, hit count
and source location.  The show commands and the LCOV exporter all read from
it, so every view agrees on what counts as covered.

Conventions
-----------
* A bin is covered when ``count >= max(at_least, 1)``.  Some producers leave
  ``at_least`` at 0 for code coverage, which would count a never-hit
  statement as covered.
* Coverage under design-unit scopes is skipped when the database has
  instances, since it duplicates the instance coverage.
* An item's location is its own source info, else its scope's (toggle bins
  and FSM states are located by their signal / state variable).
* Toggle bins are named ``<from>-><to>`` or ``<bit>:<from>-><to>``;
  :func:`parse_toggle_bin` also accepts NCDB's ``0 -> 1`` and ``0to1``.
"""
from __future__ import annotations

import dataclasses as dc
import re
from collections import OrderedDict
from typing import Dict, Iterator, List, Optional, Tuple

from covsight.core.api import CoverTypeT, ScopeTypeT

from .metrics import BinStats

#: Code-coverage kinds, in display order.
KINDS = ("line", "branch", "expression", "condition", "toggle",
         "fsm_state", "fsm_transition", "block")

#: Assertion-style kinds (cover directives and assertions).
DIRECTIVE_KINDS = ("cover", "assertion")

_KIND_OF_TYPE = {
    CoverTypeT.STMTBIN: "line",
    CoverTypeT.BRANCHBIN: "branch",
    CoverTypeT.EXPRBIN: "expression",
    CoverTypeT.CONDBIN: "condition",
    CoverTypeT.TOGGLEBIN: "toggle",
    CoverTypeT.BLOCKBIN: "block",
}

#: Item attribute listing every line of a multi-line statement / basic block,
#: or the body of a branch arm ("12,14-16"); set by the Verilator importer.
LINES_ATTR = "lines"


@dc.dataclass
class CodeItem:
    kind: str
    instance: str           # dotted instance path ("" outside any instance)
    scope: object           # the scope holding the bin
    name: str               # bin name
    count: int
    at_least: int
    file: Optional[str] = None
    line: int = 0
    col: int = 0
    lines: Optional[List[int]] = None   # all lines of a statement / branch arm

    @property
    def covered(self) -> bool:
        return self.count >= max(self.at_least, 1)

    @property
    def scope_name(self) -> str:
        return self.scope.getScopeName()


def walk_scopes(db, skip_du: Optional[bool] = None
                ) -> Iterator[Tuple[str, object]]:
    """Yield ``(instance_path, scope)`` for every scope, depth first.

    ``instance_path`` is the dotted path of the INSTANCE scopes enclosing
    (and including) ``scope``.  Design-unit subtrees are skipped when
    ``skip_du`` is true; by default, whenever the database has instances.
    """
    tops = list(db.scopes(ScopeTypeT.ALL))
    if skip_du is None:
        skip_du = any(s.getScopeType() == ScopeTypeT.INSTANCE for s in tops)

    def visit(scope, inst):
        st = scope.getScopeType()
        if skip_du and ScopeTypeT.DU_ANY(st):
            return
        if st == ScopeTypeT.INSTANCE:
            inst = scope.getScopeName() if not inst else inst + "." + scope.getScopeName()
        yield inst, scope
        for child in scope.scopes(ScopeTypeT.ALL):
            yield from visit(child, inst)

    for top in tops:
        yield from visit(top, "")


def _kind(scope_type, cover_type, name) -> Optional[str]:
    kind = _KIND_OF_TYPE.get(cover_type)
    if kind is not None:
        return kind
    if cover_type == CoverTypeT.FSMBIN:
        if scope_type == ScopeTypeT.FSM_TRANS or "->" in name:
            return "fsm_transition"
        return "fsm_state"
    if cover_type == CoverTypeT.COVERBIN:
        return "cover"
    if cover_type in (CoverTypeT.ASSERTBIN, CoverTypeT.PASSBIN,
                      CoverTypeT.FAILBIN, CoverTypeT.VACUOUSBIN,
                      CoverTypeT.DISABLEDBIN, CoverTypeT.ATTEMPTBIN,
                      CoverTypeT.ACTIVEBIN, CoverTypeT.PEAKACTIVEBIN):
        return "assertion"
    return None


def parse_line_set(text: str) -> List[int]:
    """``"12,14-16"`` -> ``[12, 14, 15, 16]``; malformed parts are skipped."""
    ret = []
    for part in str(text).split(","):
        lo, sep, hi = part.strip().partition("-")
        try:
            if sep:
                ret.extend(range(int(lo), int(hi) + 1))
            elif lo:
                ret.append(int(lo))
        except ValueError:
            continue
    return ret


_TOGGLE_RE = re.compile(
    r"^(?:(?P<bit>.+?):)?\s*(?P<frm>[01xXzZ])\s*(?:->|to)\s*(?P<to>[01xXzZ])\s*$")


def parse_toggle_bin(name: str) -> Optional[Tuple[Optional[str], str, str]]:
    """``"3:0->1"`` -> ``("3", "0", "1")``; ``"1 -> 0"`` -> ``(None, "1", "0")``.

    Returns None for names that are not toggle transitions.
    """
    m = _TOGGLE_RE.match(name)
    if m is None:
        return None
    return m.group("bit"), m.group("frm").lower(), m.group("to").lower()


def _location(src) -> Tuple[Optional[str], int, int]:
    if src is None or getattr(src, "file", None) is None:
        return None, 0, 0
    try:
        fname = src.file.getFileName()
    except Exception:
        return None, 0, 0
    return fname or None, max(src.line or 0, 0), max(src.token or 0, 0)


class CodeCoverage:
    """All code-coverage and directive bins of a database, with roll-ups."""

    def __init__(self, db):
        self.items: List[CodeItem] = []
        for inst, scope in walk_scopes(db):
            items = list(scope.coverItems(CoverTypeT.ALL))
            if not items:
                continue
            st = scope.getScopeType()
            scope_loc = _location(scope.getSourceInfo())
            for ci in items:
                cd = ci.getCoverData()
                name = ci.getName()
                kind = _kind(st, cd.type, name)
                if kind is None:
                    continue
                fname, line, col = _location(ci.getSourceInfo())
                if fname is None:
                    fname, line, col = scope_loc
                lines = None
                if kind in ("line", "branch") and hasattr(ci, "getAttribute"):
                    attr = ci.getAttribute(LINES_ATTR)
                    if attr:
                        lines = parse_line_set(attr) or None
                self.items.append(CodeItem(
                    kind=kind, instance=inst, scope=scope, name=name,
                    count=int(cd.data or 0), at_least=int(cd.at_least or 0),
                    file=fname, line=line, col=col, lines=lines))

    def relocate(self, root: str):
        """Make file names under ``root`` relative to it (others unchanged),
        so exported reports match a repository checkout."""
        import os
        root = os.path.abspath(root)
        for it in self.items:
            if it.file and os.path.isabs(it.file):
                rel = os.path.relpath(it.file, root)
                if not rel.startswith(".."):
                    it.file = rel

    # ------------------------------------------------------------ roll-ups
    @staticmethod
    def _tally(items, kinds) -> "OrderedDict[str, BinStats]":
        ret = OrderedDict((k, BinStats()) for k in kinds)
        for it in items:
            st = ret.get(it.kind)
            if st is not None:
                st.total += 1
                st.covered += 1 if it.covered else 0
        return ret

    def by_kind(self, kinds=KINDS) -> "OrderedDict[str, BinStats]":
        """Totals per kind (every kind listed, present or not)."""
        return self._tally(self.items, kinds)

    def kinds_present(self, kinds=KINDS) -> List[str]:
        return [k for k, st in self.by_kind(kinds).items() if st.total]

    def overall(self, kinds=KINDS) -> BinStats:
        ret = BinStats()
        for st in self.by_kind(kinds).values():
            ret = ret + st
        return ret

    def _group(self, key, kinds) -> "OrderedDict[str, OrderedDict[str, BinStats]]":
        groups: "OrderedDict[str, list]" = OrderedDict()
        for it in self.items:
            if it.kind in kinds:
                groups.setdefault(key(it), []).append(it)
        return OrderedDict((k, self._tally(v, kinds)) for k, v in groups.items())

    def by_instance(self, kinds=KINDS):
        """``{instance path: {kind: BinStats}}`` in database order."""
        return self._group(lambda it: it.instance, kinds)

    def by_file(self, kinds=KINDS):
        """``{file: {kind: BinStats}}`` sorted by file; unlocated items are
        grouped under ``""``."""
        groups = self._group(lambda it: it.file or "", kinds)
        return OrderedDict(sorted(groups.items()))

    # ----------------------------------------------------------- line level
    def line_hits(self) -> Dict[str, Dict[int, int]]:
        """``{file: {line: hits}}`` -- executable lines, for LCOV/Cobertura.

        Executable lines are the lines of statements, the body lines of
        branch arms, and each branch's decision line.  A decision line is
        hit as often as its arms in total; any other line shared by several
        items reports the largest count, as gcov-style tools do.
        """
        ret: Dict[str, Dict[int, int]] = {}

        def hit(fname, line, n):
            per_file = ret.setdefault(fname, {})
            per_file[line] = max(per_file.get(line, 0), n)

        decisions: "OrderedDict[int, list]" = OrderedDict()
        for it in self.items:
            if it.kind not in ("line", "branch") or not it.file:
                continue
            if it.kind == "line":
                for ln in it.lines or ([it.line] if it.line > 0 else []):
                    hit(it.file, ln, it.count)
            else:
                for ln in it.lines or []:
                    hit(it.file, ln, it.count)
                decisions.setdefault(id(it.scope), []).append(it)
        for arms in decisions.values():
            if arms[0].line > 0:
                hit(arms[0].file, arms[0].line, sum(a.count for a in arms))
        return ret

    def branches(self) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """``{file: [(line, block, branch, hits), ...]}`` for LCOV ``BRDA``.

        Each branch scope is one block; its arms are numbered in order.
        Blocks on the same line are numbered from 0 per line.  The same
        source branch in several instances is one record, with summed hits.
        """
        scopes: "OrderedDict[int, list]" = OrderedDict()
        for it in self.items:
            if it.kind == "branch" and it.file:
                scopes.setdefault(id(it.scope), []).append(it)
        next_block: Dict[Tuple[str, str, int], int] = {}
        hits: "OrderedDict[Tuple[str, int, int, int], int]" = OrderedDict()
        for arms in scopes.values():
            inst, fname, line = arms[0].instance, arms[0].file, arms[0].line
            block = next_block.get((inst, fname, line), 0)
            next_block[(inst, fname, line)] = block + 1
            for i, arm in enumerate(arms):
                key = (fname, line, block, i)
                hits[key] = hits.get(key, 0) + arm.count
        ret: Dict[str, List[Tuple[int, int, int, int]]] = {}
        for (fname, line, block, i), n in hits.items():
            ret.setdefault(fname, []).append((line, block, i, n))
        for recs in ret.values():
            recs.sort()
        return ret


def stats_dict(st: BinStats) -> Dict:
    return {"covered": st.covered, "total": st.total,
            "coverage": round(st.coverage_pct, 2)}


def kinds_dict(stats, present_only: bool = True) -> Dict:
    return OrderedDict((k, stats_dict(v)) for k, v in stats.items()
                       if v.total or not present_only)
