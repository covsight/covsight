"""Parity with Verilator's own coverage report.

Compares covsight's per-kind totals (:func:`covsight.analysis.totals.kind_totals`)
with ``verilator_coverage --report summary`` for the same ``coverage.dat``
files.  covsight drops points in Verilator's built-in ``std`` package by
default, so those are counted from the ``.dat`` files and subtracted from
Verilator's numbers before comparing.

Each kind ends up in one of four states:

``match``      the numbers agree
``explained``  they differ, and the caller gave a reason (``expect.yaml``)
``mismatch``   they differ with no reason -- a failure
``stale``      a reason was given but the numbers agree -- the note is out of
               date and should be removed
"""
from __future__ import annotations

import dataclasses as dc
import re
import shutil
import subprocess
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

#: Verilator summary kind -> covsight kind
VLT_KINDS = {
    "line": "line",
    "branch": "branch",
    "expr": "expression",
    "toggle": "toggle",
    "fsm_state": "fsm_state",
    "fsm_arc": "fsm_transition",
    "covergroup": "covergroup",
    "user": "cover",
}

Ratio = Tuple[int, int]     # (covered, total)

_SUMMARY_RE = re.compile(r"^\s*(\w+)\s*:\s*[\d.]+%\s*\(\s*(\d+)\s*/\s*(\d+)\s*\)")


def parse_vlt_summary(text: str) -> Dict[str, Ratio]:
    """``verilator_coverage --report summary`` output -> ``{vlt_kind: (cov, tot)}``."""
    ret = {}
    for line in text.splitlines():
        m = _SUMMARY_RE.match(line)
        if m:
            ret[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return ret


def run_vlt_summary(dat_paths: Iterable[str],
                    verilator_coverage: Optional[str] = None) -> str:
    """Run ``verilator_coverage --report summary`` over ``dat_paths``."""
    exe = verilator_coverage or shutil.which("verilator_coverage")
    if exe is None:
        raise FileNotFoundError("verilator_coverage not found on PATH")
    r = subprocess.run([exe, "--report", "summary"] + list(dat_paths),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("verilator_coverage failed: %s" % (r.stderr or r.stdout).strip())
    return r.stdout


def std_counts(dat_paths: Iterable[str]) -> Dict[str, Ratio]:
    """``{vlt_kind: (cov, tot)}`` for points in Verilator's ``std`` package.

    Points are keyed as ``verilator_coverage`` merges them (by their full key
    string), so a point present in several files counts once.
    """
    from covsight.core.vltcov.vlt_mapper import is_std_path
    from covsight.core.vltcov.vlt_parser import VltParser

    merged: Dict[Tuple[str, str], int] = {}
    for path in dat_paths:
        for it in VltParser().parse_file(path):
            if not is_std_path(it.hier):
                continue
            key = (it.kind, repr(sorted(it.attrs.items())))
            merged[key] = merged.get(key, 0) + it.count
    ret: Dict[str, Ratio] = {}
    for (kind, _), count in merged.items():
        cov, tot = ret.get(kind, (0, 0))
        ret[kind] = (cov + (count > 0), tot + 1)
    return ret


@dc.dataclass
class KindParity:
    kind: str                       # covsight kind name
    covsight: Ratio
    verilator: Ratio                # as verilator_coverage reports it
    std: Ratio = (0, 0)             # std-package points included in `verilator`
    explanation: Optional[str] = None

    @property
    def expected(self) -> Ratio:
        """Verilator's numbers without the std package."""
        return (self.verilator[0] - self.std[0], self.verilator[1] - self.std[1])

    @property
    def matches(self) -> bool:
        return self.covsight == self.expected

    @property
    def state(self) -> str:
        if self.matches:
            return "stale" if self.explanation else "match"
        return "explained" if self.explanation else "mismatch"

    def describe(self) -> str:
        s = "%s: covsight %d/%d, verilator_coverage %d/%d" % (
            self.kind, self.covsight[0], self.covsight[1],
            self.verilator[0], self.verilator[1])
        if self.std != (0, 0):
            s += " (%d/%d without std)" % self.expected
        if self.state == "explained":
            s += " -- " + self.explanation
        elif self.state == "stale":
            s += " -- agrees, but expect.yaml still explains a difference"
        return s


def compare(covsight: Mapping[str, Ratio],
            verilator: Mapping[str, Ratio],
            std: Optional[Mapping[str, Ratio]] = None,
            explanations: Optional[Mapping[str, str]] = None,
            include_std: bool = False) -> List[KindParity]:
    """Compare per kind.  ``verilator`` and ``std`` use Verilator kind names;
    ``covsight`` and ``explanations`` use covsight's.  Kinds that are 0/0 on
    both sides are left out."""
    std = std or {}
    explanations = explanations or {}
    ret = []
    for vkind, kind in VLT_KINDS.items():
        v = verilator.get(vkind, (0, 0))
        c = covsight.get(kind, (0, 0))
        if v == (0, 0) and c == (0, 0):
            continue
        ret.append(KindParity(
            kind=kind, covsight=c, verilator=v,
            std=(0, 0) if include_std else std.get(vkind, (0, 0)),
            explanation=explanations.get(kind)))
    return ret
