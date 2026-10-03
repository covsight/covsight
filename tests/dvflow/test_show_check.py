"""covsight.Show and covsight.Check.

The helpers are tested directly; the flow test runs cov_top.sv through
Verilator (skipped without it), as an example's flow.yaml would.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# -- helpers (dv-flow-mgr installed; no Verilator) ----------------------------

def test_argv_and_slug():
    pytest.importorskip("dv_flow.mgr")
    from covsight.dvflow.cov_show import _argv, _display, _slug
    assert _argv("show summary -of text", "m.cdb") == ["show", "summary", "m.cdb", "-of", "text"]
    assert _argv("show bins {db} --covergroup cg", "m.cdb") == [
        "show", "bins", "m.cdb", "--covergroup", "cg"]
    assert _display("show hierarchy", "m.cdb") == "covsight show hierarchy m.cdb"
    assert _argv("show code-coverage -sr {srcdir}", "m.cdb", "/ex") == [
        "show", "code-coverage", "m.cdb", "-sr", "/ex"]
    assert _display("show code-coverage -sr {srcdir}", "m.cdb") == \
        "covsight show code-coverage m.cdb -sr ."
    assert _slug("show code-coverage -of text") == "show-code-coverage"
    assert _slug("report {db} -of json") == "report"


def test_check_warnings():
    pytest.importorskip("dv_flow.mgr")
    from covsight.dvflow.cov_check import check_warnings
    log = textwrap.dedent("""\
        %Warning-COVERIGN: t.sv:4:32: Unsupported: 'bins' explicit array size
                           ... For warning description see ...
        %Warning-WIDTHEXPAND: t.sv:9:3: Operator ADD expects 32 bits
        - V e r i l a t i o n   R e p o r t
        """)
    w = check_warnings(["COVERIGN", "WIDTH"], log)
    assert w["ok"] and len(w["found"]) == 2
    w = check_warnings(["COVERIGN"], log)
    assert not w["ok"] and w["unexpected"][0].startswith("%Warning-WIDTHEXPAND")
    w = check_warnings(["COVERIGN", "WIDTH", "CASEINCOMPLETE"], log)
    assert w["unmatched_patterns"] == ["CASEINCOMPLETE"]
    assert check_warnings([], "")["ok"]


def test_check_totals():
    pytest.importorskip("dv_flow.mgr")
    from covsight.dvflow.cov_check import check_totals
    res = check_totals({"line": (11, 11), "branch": (7, 8)}, {"line": (11, 11)})
    assert [(r["kind"], r["ok"], r["actual"]) for r in res] == [
        ("line", True, "11/11"), ("branch", False, "0/0")]


# -- flow ---------------------------------------------------------------------

FLOW = """\
package:
  name: t
  imports: [{name: hdlsim}, {name: covsight}]
  tasks:
  - name: src
    uses: std.FileSet
    with: {type: systemVerilogSource, base: "%(data)s", include: cov_top.sv}
  - name: img
    uses: hdlsim.vlt.SimImage
    needs: [src]
    with: {top: [cov_top], cov: full}
  - name: run0
    uses: hdlsim.vlt.SimRun
    needs: [img]
    with: {plusargs: ["verilator+seed+1"]}
  - name: cov
    uses: covsight.Import
    needs: [run0]
  - name: merged
    uses: covsight.Merge
    needs: [cov]
  - root: show
    uses: covsight.Show
    needs: [merged]
    with: {expect: expect.yaml}
  - root: check
    uses: covsight.Check
    needs: [merged, run0, img]
"""

EXPECT = """\
totals:
  line: 11/11
  branch: 7/8
  expression: 5/5
  toggle: 13/14
  fsm_state: 2/2
  covergroup: 3/4
  cover: 1/1
transcript:
  - show summary -of text
  - show code-coverage -of text
"""


@pytest.fixture
def flow_dir(tmp_path):
    pytest.importorskip("dv_flow.libhdlsim")
    if shutil.which("verilator") is None:
        pytest.skip("verilator not on PATH")
    (tmp_path / "flow.yaml").write_text(FLOW % {"data": DATA})
    (tmp_path / "expect.yaml").write_text(EXPECT)
    return tmp_path


def dfm(d, task):
    return subprocess.run([sys.executable, "-m", "dv_flow.mgr", "run", task],
                          cwd=d, capture_output=True, text=True)


def check_json(d):
    with open(d / "rundir" / "t.check" / "check.json") as f:
        return json.load(f)


def test_show_writes_transcripts(flow_dir):
    r = dfm(flow_dir, "show")
    assert r.returncode == 0, r.stdout + r.stderr
    out = flow_dir / "rundir" / "t.show"
    index = json.loads((out / "transcript.json").read_text())
    assert [e["command"] for e in index] == [
        "covsight show summary merged.cdb -of text",
        "covsight show code-coverage merged.cdb -of text"]
    assert all(e["status"] == 0 for e in index)
    text = (out / index[1]["file"]).read_text()
    assert text.startswith("Code coverage: merged.cdb")       # no absolute path
    assert "branch            7      8" in text


def test_check_passes_then_fails_on_changes(flow_dir):
    r = dfm(flow_dir, "check")
    assert r.returncode == 0, r.stdout + r.stderr
    res = check_json(flow_dir)
    assert res["passed"]
    assert {p["state"] for p in res["parity"]} == {"match"}
    assert res["warnings"]["logs"], "image build.log not found"

    # A total that moved, a stale parity note and a missing warning all fail,
    # each with its own message.
    (flow_dir / "expect.yaml").write_text(
        EXPECT.replace("branch: 7/8", "branch: 8/8")
        + "parity:\n  toggle: an old note\nwarnings:\n  - COVERIGN\n")
    r = dfm(flow_dir, "check")
    assert r.returncode != 0
    errs = check_json(flow_dir)["errors"]
    assert len(errs) == 3, errs
    assert errs[0] == "totals.branch: expected 8/8, got 7/8"
    assert errs[1].startswith("parity: toggle:") and "still explains" in errs[1]
    assert "COVERIGN" in errs[2]


def test_check_reports_bad_expect(flow_dir):
    (flow_dir / "expect.yaml").write_text("totals:\n  lines: 1/1\n")
    r = dfm(flow_dir, "check")
    assert r.returncode != 0
    # dfm wraps long markers; compare without whitespace or box drawing.
    flat = re.sub(r"[\s\u2500-\u257f]", "", r.stdout + r.stderr)
    assert "expect.yaml:2:unknowncoveragekind'lines'" in flat


def test_show_skips_unchanged(tmp_path):
    """A fixed database (no simulator): Show reruns only when the database
    or the commands change."""
    pytest.importorskip("dv_flow.mgr")
    fixture = os.path.join(DATA, "..", "..", "data", "vltcov", "cov_top.dat")
    r = subprocess.run([sys.executable, "-m", "covsight.cli", "convert",
                        fixture, "-o", str(tmp_path / "cov.cdb")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    flow = {"package": {"name": "t", "imports": [{"name": "covsight"}], "tasks": [
        {"name": "db", "uses": "std.FileSet",
         "with": {"type": "covsightNCDB", "base": str(tmp_path), "include": "cov.cdb"}},
        {"root": "show", "uses": "covsight.Show", "needs": ["db"],
         "with": {"commands": ["show hierarchy -of text"]}}]}}
    (tmp_path / "flow.yaml").write_text(json.dumps(flow))
    out = tmp_path / "rundir" / "t.show" / "01-show-hierarchy.txt"

    assert dfm(tmp_path, "show").returncode == 0
    stamp = out.stat().st_mtime_ns
    assert dfm(tmp_path, "show").returncode == 0
    assert out.stat().st_mtime_ns == stamp                   # skipped
    os.utime(tmp_path / "cov.cdb")
    assert dfm(tmp_path, "show").returncode == 0
    assert out.stat().st_mtime_ns != stamp                   # database changed



def test_tasks_are_discoverable(tmp_path):
    """`dfm show tasks` lists every exported covsight task."""
    pytest.importorskip("dv_flow.mgr")
    (tmp_path / "flow.yaml").write_text(json.dumps(
        {"package": {"name": "t", "imports": [{"name": "covsight"}], "tasks": []}}))
    r = subprocess.run([sys.executable, "-m", "dv_flow.mgr", "show", "tasks",
                        "--package", "covsight", "--json"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    names = {t["name"] for t in json.loads(r.stdout)["results"]}
    assert {"covsight.Import", "covsight.Merge", "covsight.Show",
            "covsight.Check"} <= names
