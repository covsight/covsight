"""Code-coverage display: show code-coverage / toggle / assertions /
hierarchy / summary, and LCOV / Cobertura export, on Verilator databases.

The fixtures in data/vltcov are Verilator coverage.dat files.  Expected
numbers are derived from those files directly (a small independent parser
below) and cross-checked against ``verilator_coverage --report summary``, so
a view that drops, double counts or misclassifies a point fails.
"""
import json
import os
import re
import subprocess
import sys

import pytest

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "vltcov")

# Verilator point kind -> code-coverage kind reported by covsight
_KIND = {"line": "line", "branch": "branch", "expr": "expression",
         "toggle": "toggle", "fsm_state": "fsm_state", "fsm_arc": "fsm_transition"}


def raw_points(name):
    """[(attrs, count)] for every non-std point of data/vltcov/<name>.dat."""
    pts = []
    for line in open(os.path.join(DATA, name + ".dat")):
        m = re.match(r"C '(.*)' (\d+)$", line.rstrip("\n"))
        if not m:
            continue
        attrs = dict(kv.split("\x02", 1) for kv in m.group(1).split("\x01") if kv)
        h = attrs.get("h", "")
        if h == "std" or h.startswith("std::"):
            continue
        attrs["kind"] = attrs["page"].split("/")[0][2:]
        pts.append((attrs, int(m.group(2))))
    return pts


def summary(name):
    ret = {}
    for line in open(os.path.join(DATA, name + ".summary.txt")):
        m = re.match(r"\s*(\w+)\s*:\s*[\d.]+%\s*\(\s*(\d+)/\s*(\d+)\)", line)
        if m:
            ret[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return ret


def covsight(*args, check=True):
    r = subprocess.run([sys.executable, "-m", "covsight.cli"] + list(args),
                       capture_output=True, text=True)
    if check:
        assert r.returncode == 0, r.stdout + r.stderr
    return r


@pytest.fixture(scope="module")
def cdb(tmp_path_factory):
    """name -> NCDB converted from data/vltcov/<name>.dat with `covsight convert`."""
    d = tmp_path_factory.mktemp("vltcov")
    ret = {}
    for name in ("cov_top", "hier_top_pi"):
        out = str(d / (name + ".cdb"))
        covsight("convert", "--out", out, os.path.join(DATA, name + ".dat"))
        ret[name] = out
    return ret


def show(view, db, *args):
    return json.loads(covsight("show", view, *args, db).stdout)


def test_code_coverage_by_kind(cdb):
    data = show("code-coverage", cdb["cov_top"])
    expect = {}
    for attrs, count in raw_points("cov_top"):
        kind = _KIND.get(attrs["kind"])
        if kind:
            cov, tot = expect.get(kind, (0, 0))
            expect[kind] = (cov + (count > 0), tot + 1)
    got = {k: (v["covered"], v["total"]) for k, v in data["by_kind"].items()}
    assert got == expect
    # Covered counts agree with Verilator's own report (whose totals also
    # include the std package's never-hit points).
    vlt = summary("cov_top")
    for vkind, kind in _KIND.items():
        if kind in got:
            assert got[kind][0] == vlt[vkind][0], kind
    assert data["overall"]["total"] == sum(t for _, t in expect.values())


def test_code_coverage_instances_and_files(cdb):
    data = show("code-coverage", cdb["hier_top_pi"])
    insts = {i["instance"]: i["by_kind"] for i in data["instances"]}
    assert set(insts) == {"hier_top", "hier_top.u_a", "hier_top.u_b"}
    for kind, st in data["by_kind"].items():
        assert sum(i.get(kind, {}).get("total", 0) for i in insts.values()) == st["total"]
    assert [f["file"] for f in data["files"]] == ["hier_top.sv"]
    assert data["files"][0]["by_kind"] == data["by_kind"]
    # u_b's FSM never reaches one state (st only toggles bit 0).
    assert insts["hier_top.u_b"]["fsm_state"]["covered"] < insts["hier_top.u_b"]["fsm_state"]["total"]


def _expand(s):
    ret = []
    for part in s.split(","):
        lo, _, hi = part.partition("-")
        ret.extend(range(int(lo), int(hi or lo) + 1))
    return ret


def expected_lines(name):
    """{line: hits} for executable lines, from the raw points: statement and
    branch-arm line sets (max count), plus each branch's decision line (hit
    as often as its arms in total)."""
    lines, decisions = {}, {}
    for attrs, count in raw_points(name):
        if attrs["kind"] not in ("line", "branch"):
            continue
        body = attrs.get("S") or (attrs["l"] if attrs["kind"] == "line" else "")
        for ln in _expand(body) if body else []:
            lines[ln] = max(lines.get(ln, 0), count)
        if attrs["kind"] == "branch":
            ln = int(attrs["l"])
            decisions[ln] = decisions.get(ln, 0) + count
    for ln, n in decisions.items():
        lines[ln] = max(lines.get(ln, 0), n)
    return lines


def branch_arms(name):
    return sorted((int(a["l"]), n) for a, n in raw_points(name) if a["kind"] == "branch")


def test_lcov(cdb, tmp_path):
    out = str(tmp_path / "cov.info")
    covsight("show", "code-coverage", "-of", "lcov", "-o", out, cdb["cov_top"])
    recs = {}
    for line in open(out):
        key, _, val = line.strip().partition(":")
        recs.setdefault(key, []).append(val)
    assert recs["SF"] == ["cov_top.sv"]
    assert recs["end_of_record"] == [""]

    expect = expected_lines("cov_top")
    da = dict(tuple(map(int, v.split(","))) for v in recs["DA"])
    assert da == expect
    # The decision line of `if (count[0] && count[1])` runs every cycle.
    assert da[17] == da[18] + da[20] == 10
    assert int(recs["LF"][0]) == len(expect)
    assert int(recs["LH"][0]) == sum(1 for n in expect.values() if n)

    # BRDA: one record per branch arm.
    arms = branch_arms("cov_top")
    brda = [tuple(map(int, v.split(","))) for v in recs["BRDA"]]
    assert sorted((b[0], b[3]) for b in brda) == arms
    assert int(recs["BRF"][0]) == len(arms)
    assert int(recs["BRH"][0]) == sum(1 for _, n in arms if n)


def test_cobertura(cdb, tmp_path):
    import xml.etree.ElementTree as ET

    out = str(tmp_path / "coverage.xml")
    covsight("show", "code-coverage", "-of", "cobertura", "-o", out, cdb["cov_top"])
    text = open(out).read()
    assert "coverage-04.dtd" in text
    root = ET.fromstring(text.split("\n", 2)[2])
    required = {
        "coverage": ("line-rate", "branch-rate", "lines-covered", "lines-valid",
                     "branches-covered", "branches-valid", "complexity",
                     "version", "timestamp"),
        "package": ("name", "line-rate", "branch-rate", "complexity"),
        "class": ("name", "filename", "line-rate", "branch-rate", "complexity"),
        "line": ("number", "hits"),
    }
    for tag, attrs in required.items():
        elems = list(root.iter(tag))
        assert elems, tag
        for e in elems:
            assert all(a in e.attrib for a in attrs), (tag, e.attrib)
    assert [c.tag for c in root.find("packages/package/classes/class")] == ["methods", "lines"]

    (cls,) = root.iter("class")
    assert cls.get("filename") == "cov_top.sv"
    lines = {int(l.get("number")): l for l in cls.iter("line")}
    expect = expected_lines("cov_top")
    assert {n: int(l.get("hits")) for n, l in lines.items()} == expect

    arms = branch_arms("cov_top")
    per_line = {}
    for ln, n in arms:
        c, t = per_line.get(ln, (0, 0))
        per_line[ln] = (c + (n > 0), t + 1)
    for n, l in lines.items():
        if n in per_line:
            c, t = per_line[n]
            assert l.get("branch") == "true"
            assert l.get("condition-coverage") == "%d%% (%d/%d)" % (round(100 * c / t), c, t)
        else:
            assert l.get("branch") == "false"

    covered = sum(1 for n in expect.values() if n)
    assert (int(root.get("lines-valid")), int(root.get("lines-covered"))) == (len(expect), covered)
    assert (int(root.get("branches-valid")), int(root.get("branches-covered"))) == (
        len(arms), sum(1 for _, n in arms if n))
    assert float(root.get("line-rate")) == pytest.approx(covered / len(expect), abs=1e-4)
    assert float(root.get("branch-rate")) == pytest.approx(7 / 8)


def test_source_root(tmp_path):
    """Absolute paths under --source-root become relative to it, in both
    export formats; Cobertura lists the root as its source."""
    import xml.etree.ElementTree as ET

    src = tmp_path / "repo" / "rtl"
    src.mkdir(parents=True)
    dat = open(os.path.join(DATA, "cov_top.dat")).read()
    dat = dat.replace("\x01f\x02cov_top.sv", "\x01f\x02%s/cov_top.sv" % src)
    (tmp_path / "coverage.dat").write_text(dat)
    db = str(tmp_path / "abs.cdb")
    covsight("convert", "--out", db, str(tmp_path / "coverage.dat"))

    repo = str(tmp_path / "repo")
    lcov = covsight("show", "code-coverage", "-of", "lcov", "-sr", repo, db).stdout
    assert "SF:rtl/cov_top.sv" in lcov.splitlines()
    xml = covsight("show", "code-coverage", "-of", "cobertura", "-sr", repo, db).stdout
    root = ET.fromstring(xml.split("\n", 2)[2])
    assert [s.text for s in root.iter("source")] == [os.path.abspath(repo)]
    (cls,) = root.iter("class")
    assert cls.get("filename") == "rtl/cov_top.sv"
    (pkg,) = root.iter("package")
    assert pkg.get("name") == "rtl"
    # Without a root, the recorded absolute path is kept.
    lcov = covsight("show", "code-coverage", "-of", "lcov", db).stdout
    assert "SF:%s/cov_top.sv" % src in lcov.splitlines()


def test_toggle(cdb):
    data = show("toggle", cdb["cov_top"])
    s = data["summary"]
    assert (s["bins"]["covered"], s["bins"]["total"]) == (13, 14)
    assert s["bins"]["covered"] == summary("cov_top")["toggle"][0]
    sigs = {r["signal"]: r for r in data["signals"]}
    assert set(sigs) == {"cov_top.clk", "cov_top.count", "cov_top.flag", "cov_top.state"}
    count = sigs["cov_top.count"]
    assert (count["status"], count["width"], count["untoggled"]) == ("partial", 4, ["[3] 1->0"])
    assert count["bits"][3] == {"bit": "3", "rise": 1, "fall": 0, "toggled": False}
    assert sigs["cov_top.clk"]["status"] == "full"
    assert (s["fully_toggled"], s["partially_toggled"]) == (3, 1)

    only = show("toggle", cdb["cov_top"], "--uncovered")
    assert [r["signal"] for r in only["signals"]] == ["cov_top.count"]


def test_assertions(cdb):
    data = show("assertions", cdb["cov_top"])
    (a,) = data["assertions"]
    assert (a["kind"], a["status"], a["counts"], a["line"]) == (
        "cover", "covered", {"cover": 1}, 42)
    assert data["summary"]["cover"]["covered"] == summary("cov_top")["user"][0]


def test_hierarchy(cdb):
    data = show("hierarchy", cdb["cov_top"])
    (root,) = data["hierarchy"]
    types = set()

    def walk(n):
        types.add(n["type"])
        for c in n.get("children", []):
            walk(c)
    walk(root)
    assert {"instance", "block", "branch", "expr", "toggle", "fsm", "cover",
            "covergroup", "coverpoint"} <= types
    assert not any(t.startswith("unknown") for t in types)
    code = show("code-coverage", cdb["cov_top"])["overall"]["total"]
    assert root["total"] == code + 1 + 4      # + cover directive + cvg bins


def test_summary_and_metrics(cdb):
    data = show("summary", cdb["cov_top"])
    assert (data["overall_coverage"], data["overall_basis"]) == (75.0, "functional")
    code = data["coverage_by_type"]["code"]
    assert code["by_kind"] == show("code-coverage", cdb["cov_top"])["by_kind"]
    assert data["coverage_by_type"]["cover_directives"]["covered"] == 1

    m = show("metrics", cdb["cov_top"])["metrics"]["code"]
    assert m["by_kind"]["line"]["max_hits"] == max(
        n for a, n in raw_points("cov_top") if a["kind"] == "line")


def test_file_coverage_without_sqlite(cdb):
    from covsight.analysis.metrics import CoverageMetrics
    from covsight.core.ncdb.ncdb_reader import NcdbReader

    (fc,) = CoverageMetrics(NcdbReader().read(cdb["hier_top_pi"])).file_coverage()
    data = show("code-coverage", cdb["hier_top_pi"])["by_kind"]
    assert fc.file_path == "hier_top.sv"
    assert (fc.line.covered, fc.line.total) == (data["line"]["covered"], data["line"]["total"])
    assert fc.fsm.total == data["fsm_state"]["total"] + data["fsm_transition"]["total"]


@pytest.mark.parametrize("view", ["code-coverage", "toggle", "assertions",
                                  "hierarchy", "summary", "metrics"])
def test_text_output(cdb, view):
    r = covsight("show", view, "-of", "txt", cdb["hier_top_pi"])
    assert r.stdout.strip() and "Traceback" not in r.stderr
