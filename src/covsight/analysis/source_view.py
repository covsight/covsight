"""Annotated source: each source line with its code-coverage counts.

``annotate(cc, ...)`` turns a :class:`~covsight.analysis.code_coverage.CodeCoverage`
into one :class:`SourceFile` per source file: every line of the file with

* ``count`` -- the line's hits, as LCOV reports them
  (:meth:`CodeCoverage.line_hits`); None for a line with no statement;
* ``annotations`` -- the branch and expression points that start on the
  line, each with its rows (branch arms, expression term combinations) and
  their counts;
* ``status`` -- ``"missed"`` (the line never ran), ``"partial"`` (it ran,
  but one of its branch arms or expression rows did not), ``"covered"``, or
  None for a line with nothing to measure.

The same point in several instances of a module is one annotation with
summed counts, as for LCOV.  The text comes from the file on disk
(``source_root`` joined with the recorded path when that is relative); a
file that cannot be found is listed with its measured lines and no text.
"""
from __future__ import annotations

import dataclasses as dc
import os
from collections import OrderedDict
from typing import Dict, List, Optional, Sequence

from .code_coverage import CodeCoverage, kinds_dict

#: Kinds shown as annotations under the line they start on.
ANNOTATED_KINDS = ("branch", "expression")
#: Kinds counted in a file's totals.
FILE_KINDS = ("line", "branch", "expression")


@dc.dataclass
class Row:
    name: str
    count: int
    covered: bool


@dc.dataclass
class Annotation:
    kind: str           # "branch" or "expression"
    scope: str          # the point's scope name (e.g. "design.sv:20:28")
    col: int
    rows: List[Row]

    @property
    def covered(self) -> bool:
        return all(r.covered for r in self.rows)


@dc.dataclass
class SourceLine:
    line: int
    text: Optional[str]
    count: Optional[int] = None
    annotations: List[Annotation] = dc.field(default_factory=list)

    @property
    def status(self) -> Optional[str]:
        if self.count is None and not self.annotations:
            return None
        if self.count == 0:
            return "missed"
        if any(not a.covered for a in self.annotations):
            return "partial"
        return "covered"


@dc.dataclass
class SourceFile:
    file: str           # as recorded (relative to source_root after relocate)
    path: Optional[str]  # where its text was read from; None if not found
    by_kind: Dict
    lines: List[SourceLine]


def _find(fname: str, source_root: Optional[str]) -> Optional[str]:
    cands = []
    if os.path.isabs(fname):
        cands.append(fname)
    elif source_root:
        cands.append(os.path.join(source_root, fname))
    else:
        cands.append(fname)
    if source_root:
        # A database built elsewhere: the file under the source root by name.
        cands.append(os.path.join(source_root, os.path.basename(fname)))
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def _read(path: Optional[str]) -> Optional[List[str]]:
    if path is None:
        return None
    try:
        with open(path, errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return None


def annotate(cc: CodeCoverage, source_root: Optional[str] = None,
             files: Sequence[str] = ()) -> List[SourceFile]:
    """One :class:`SourceFile` per file with line, branch or expression
    coverage, sorted by name.  ``files`` keeps only files whose recorded
    name ends with one of the given names."""
    hits = cc.line_hits()
    by_file = cc.by_file(FILE_KINDS)

    # (file, kind, scope name) -> rows by name, in database order
    points: "OrderedDict[tuple, dict]" = OrderedDict()
    for it in cc.items:
        if it.kind not in ANNOTATED_KINDS or not it.file:
            continue
        key = (it.file, it.kind, it.scope_name)
        pt = points.get(key)
        if pt is None:
            pt = points[key] = {"line": it.line, "col": it.col, "rows": OrderedDict(),
                                "at_least": {}}
        rows = pt["rows"]
        rows[it.name] = rows.get(it.name, 0) + it.count
        pt["at_least"][it.name] = max(it.at_least, 1)

    def wanted(fname):
        return not files or any(fname == f or fname.endswith("/" + f) for f in files)

    ret = []
    for fname in sorted(by_file):
        if not fname or not wanted(fname):
            continue
        path = _find(fname, source_root)
        text = _read(path)
        lines: Dict[int, SourceLine] = OrderedDict()
        if text is not None:
            for n, t in enumerate(text, 1):
                lines[n] = SourceLine(n, t)

        def at(n):
            if n not in lines:
                lines[n] = SourceLine(n, None)
            return lines[n]

        for n, count in hits.get(fname, {}).items():
            at(n).count = count
        for (pf, kind, scope), pt in points.items():
            if pf != fname or pt["line"] <= 0:
                continue
            rows = [Row(name, n, n >= pt["at_least"][name])
                    for name, n in pt["rows"].items()]
            at(pt["line"]).annotations.append(Annotation(kind, scope, pt["col"], rows))
        for sl in lines.values():
            sl.annotations.sort(key=lambda a: (ANNOTATED_KINDS.index(a.kind), a.col))
        ret.append(SourceFile(
            file=fname, path=path,
            by_kind=kinds_dict(by_file[fname]),
            lines=[lines[n] for n in sorted(lines)]))
    return ret


def to_dict(sf: SourceFile) -> Dict:
    return {
        "file": sf.file,
        "found": sf.path is not None,
        "by_kind": sf.by_kind,
        "lines": [{
            "line": sl.line, "text": sl.text, "count": sl.count,
            "status": sl.status,
            "annotations": [{
                "kind": a.kind, "scope": a.scope, "col": a.col,
                "rows": [dc.asdict(r) for r in a.rows]} for a in sl.annotations],
        } for sl in sf.lines],
    }
