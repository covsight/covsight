"""covsight.Check: hold a coverage run to its ``expect.yaml``.

Three checks, each reported as one error marker per problem:

totals    covered/total per kind in the (merged) NCDB equals ``totals``
parity    covsight agrees with ``verilator_coverage --report summary`` on the
          run's ``coverage.dat`` files, except where ``parity`` explains why;
          an explanation for a kind that now agrees also fails, so notes do
          not outlive the difference
warnings  the Verilator build log's warnings are exactly those ``warnings``
          expects: each pattern matches at least one, and none is unmatched

Results go to ``check.json`` in the run directory.  Inputs: one
``covsightNCDB`` database; for parity, the runs (hdlsim results or
``simCovDb`` FileSets); for warnings, the image (``simDir``) whose
``build.log`` is read.
"""
import asyncio
import json
import os
import re
import shutil
from typing import Dict, List

from dv_flow.mgr import TaskDataResult
from dv_flow.mgr.task_data import SeverityE

from covsight.dvflow.cov_show import resolve
from covsight.dvflow.sources import COVSIGHT_NCDB, collect_sources, ncdb_paths

RESULT = "check.json"
_WARNING_RE = re.compile(r"^%Warning-[A-Z0-9_]+:.*$", re.M)


def _totals(db_path) -> Dict[str, tuple]:
    from covsight.analysis.totals import kind_totals
    from covsight.core.ncdb.ncdb_reader import NcdbReader
    db = NcdbReader().read(db_path)
    try:
        return {k: (v.covered, v.total) for k, v in kind_totals(db).items()}
    finally:
        db.close()


def check_totals(expected, actual) -> List[dict]:
    ret = []
    for kind, exp in expected.items():
        got = actual.get(kind, (0, 0))
        ret.append(dict(kind=kind, expected="%d/%d" % exp, actual="%d/%d" % got,
                        ok=tuple(got) == tuple(exp)))
    return ret


def check_warnings(patterns: List[str], log_text: str) -> dict:
    found = [m.group(0) for m in _WARNING_RE.finditer(log_text)]
    regs = [re.compile(p) for p in patterns]
    unmatched_patterns = [p for p, r in zip(patterns, regs)
                          if not any(r.search(w) for w in found)]
    unexpected = [w for w in found if not any(r.search(w) for r in regs)]
    return dict(found=found, unmatched_patterns=unmatched_patterns,
                unexpected=unexpected,
                ok=not unmatched_patterns and not unexpected)


def _build_logs(inputs) -> List[str]:
    ret = []
    for item in inputs or []:
        get = item.get if isinstance(item, dict) else lambda k, d=None: getattr(item, k, d)
        if get("filetype") == "simDir":
            p = os.path.join(get("basedir", "") or "", "build.log")
            if os.path.isfile(p) and p not in ret:
                ret.append(p)
    return ret


def _parity(db_totals, dats, expect, include_std):
    from covsight.analysis import parity as P
    summary = P.parse_vlt_summary(P.run_vlt_summary(dats))
    std = P.std_counts(dats)
    return P.compare(db_totals, summary, std, expect.parity, include_std)


async def Check(ctxt, input) -> TaskDataResult:
    from covsight.dvflow.expect import ExpectError, load_expect

    p = input.params
    expect_path = resolve(getattr(p, "expect", "") or "expect.yaml", input.srcdir)
    try:
        expect = load_expect(expect_path)
    except (OSError, ExpectError) as e:
        ctxt.error(str(e))
        return TaskDataResult(status=1)

    dbs = ncdb_paths(input.inputs)
    if len(dbs) != 1:
        ctxt.error("expected one %s database among the inputs, got %d" % (
            COVSIGHT_NCDB, len(dbs)))
        return TaskDataResult(status=1)
    (db,) = dbs

    errors: List[str] = []
    result = dict(expect=expect_path, database=db)

    actual = await asyncio.to_thread(_totals, db)
    result["totals"] = check_totals(expect.totals, actual)
    result["actual_totals"] = {k: "%d/%d" % v for k, v in actual.items()}
    for t in result["totals"]:
        if not t["ok"]:
            errors.append("totals.%s: expected %s, got %s" % (
                t["kind"], t["expected"], t["actual"]))

    dats = [s.path for s in collect_sources(input.inputs)
            if s.covsight_format == "vltcov" and os.path.isfile(s.path)]
    do_parity = bool(getattr(p, "parity", True))
    if do_parity and dats and shutil.which("verilator_coverage"):
        try:
            res = await asyncio.to_thread(
                _parity, actual, dats, expect, bool(getattr(p, "include_std", False)))
        except Exception as e:
            errors.append("parity: %s" % e)
            res = []
        result["parity"] = [dict(
            kind=r.kind, state=r.state, text=r.describe(),
            covsight="%d/%d" % tuple(r.covsight),
            verilator="%d/%d" % tuple(r.verilator),
            verilator_without_std="%d/%d" % tuple(r.expected),
            explanation=r.explanation or "") for r in res]
        for r in res:
            if r.state in ("mismatch", "stale"):
                errors.append("parity: " + r.describe())
            elif r.state == "explained":
                ctxt.info("parity: " + r.describe())
    elif do_parity and expect.parity:
        errors.append("parity: expect.yaml explains differences, but there is "
                      "nothing to compare (no coverage.dat inputs or no "
                      "verilator_coverage on PATH)")

    logs = _build_logs(input.inputs)
    if logs:
        text = "".join(open(l, encoding="utf-8", errors="replace").read() for l in logs)
        w = check_warnings(expect.warnings, text)
        result["warnings"] = dict(w, logs=logs)
        for pat in w["unmatched_patterns"]:
            errors.append("warnings: expected a build warning matching %r; none found" % pat)
        for line in w["unexpected"]:
            errors.append("warnings: unexpected build warning (add it to "
                          "expect.yaml if intended): %s" % line)
    elif expect.warnings:
        errors.append("warnings: expect.yaml lists build warnings, but no "
                      "image (simDir) build.log is among the inputs")

    result["errors"] = errors
    result["passed"] = not errors
    with open(os.path.join(input.rundir, RESULT), "w") as f:
        json.dump(result, f, indent=1)

    for e in errors:
        ctxt.marker(e, severity=SeverityE.Error)
    if not errors:
        ctxt.info("%s: %d totals, %d parity kinds, %d warnings as expected" % (
            os.path.basename(os.path.dirname(expect_path)) or expect_path,
            len(result["totals"]), len(result.get("parity", [])),
            len((result.get("warnings") or {}).get("found", []))))
    return TaskDataResult(status=1 if errors else 0, changed=True)
