"""covsight show source: annotated source from Verilator databases.

Counts are checked against the raw coverage.dat points (parsed
independently in test_code_coverage_views) and against the LCOV export, so
the annotated view agrees with both.
"""
import json
import re
from collections import defaultdict

from tests.test_code_coverage_views import cdb, covsight, raw_points  # noqa: F401


def source(db, *args):
    return json.loads(covsight("show", "source", "-of", "json", *args, db).stdout)


def test_counts_match_lcov_and_raw_points(cdb):
    for name, src in (("cov_top", "cov_top.sv"), ("hier_top_pi", "hier_top.sv")):
        (f,) = [f for f in source(cdb[name])["files"] if f["file"] == src]
        assert not f["found"]          # no source text in the fixtures
        counts = {ln["line"]: ln["count"] for ln in f["lines"] if ln["count"] is not None}
        assert counts == lcov_lines_for(cdb[name], src)

        # Each branch / expression point once, rows summed over instances.
        want = defaultdict(lambda: defaultdict(int))
        for attrs, n in raw_points(name):
            if attrs["kind"] in ("branch", "expr") and attrs["f"].endswith(src):
                want[(attrs["kind"], int(attrs["l"]), int(attrs["n"]) if attrs["kind"] == "expr"
                      else 0)][attrs["o"]] += n
        got = defaultdict(lambda: defaultdict(int))
        for ln in f["lines"]:
            for a in ln["annotations"]:
                kind = "expr" if a["kind"] == "expression" else "branch"
                for r in a["rows"]:
                    got[(kind, ln["line"], a["col"] if kind == "expr" else 0)][r["name"]] += r["count"]
        assert {k: dict(v) for k, v in got.items()} == {k: dict(v) for k, v in want.items()}


def lcov_lines_for(db, src):
    out = covsight("show", "code-coverage", "-of", "lcov", db).stdout
    ret, cur = {}, None
    for ln in out.splitlines():
        if ln.startswith("SF:"):
            cur = ln[3:]
        m = re.match(r"DA:(\d+),(\d+)$", ln)
        if m and cur and cur.endswith(src):
            ret[int(m.group(1))] = int(m.group(2))
    return ret


def test_status(cdb):
    (f,) = [f for f in source(cdb["cov_top"])["files"] if f["file"] == "cov_top.sv"]
    for ln in f["lines"]:
        rows_missed = any(not r["covered"] for a in ln["annotations"] for r in a["rows"])
        if ln["count"] == 0:
            assert ln["status"] == "missed"
        elif ln["count"] is None and not ln["annotations"]:
            assert ln["status"] is None
        else:
            assert ln["status"] == ("partial" if rows_missed else "covered"), ln
    assert {ln["status"] for ln in f["lines"]} >= {"missed", "covered"}


def test_source_text_from_source_root(cdb, tmp_path):
    (f,) = [f for f in source(cdb["cov_top"])["files"] if f["file"] == "cov_top.sv"]
    n = max(ln["line"] for ln in f["lines"]) + 3
    (tmp_path / "cov_top.sv").write_text("".join("L%d\n" % i for i in range(1, n + 1)))
    (g,) = [g for g in source(cdb["cov_top"], "-sr", str(tmp_path))["files"]
            if g["file"].endswith("cov_top.sv")]
    assert g["found"]
    assert [ln["line"] for ln in g["lines"]] == list(range(1, n + 1))
    assert all(ln["text"] == "L%d" % ln["line"] for ln in g["lines"])
    measured = {ln["line"]: ln["count"] for ln in f["lines"]}
    assert {ln["line"]: ln["count"] for ln in g["lines"] if ln["line"] in measured} == measured


def test_uncovered_and_text(cdb, tmp_path):
    db = cdb["cov_top"]
    (f,) = [f for f in source(db, "-u", "-f", "cov_top.sv")["files"]]
    assert f["lines"] and all(ln["status"] in ("missed", "partial") for ln in f["lines"])
    text = covsight("show", "source", "-u", "-f", "cov_top.sv", db).stdout
    assert text.startswith("Source coverage: ")
    assert "cov_top.sv  line " in text
    assert "(source not found; use --source-root)" in text
    missed = [ln for ln in f["lines"] if ln["status"] == "missed"][0]
    assert re.search(r"^\s*%d # +0 \|" % missed["line"], text, re.M)
    none = covsight("show", "source", "-f", "nosuch.sv", db).stdout
    assert "No line, branch or expression coverage in the selected files." in none
