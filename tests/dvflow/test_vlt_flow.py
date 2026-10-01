"""End to end: hdlsim.vlt SimImage/SimRun -> covsight.Import -> covsight.Merge.

Needs Verilator on PATH and dv-flow-libhdlsim installed; skipped otherwise.
The flow is written as a flow.yaml, as a user would.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys

import pytest

dfm = pytest.importorskip("dv_flow.mgr")
pytest.importorskip("dv_flow.libhdlsim")

from dv_flow.mgr import PackageLoader, TaskSetRunner          # noqa: E402
from dv_flow.mgr.task_graph_builder import TaskGraphBuilder    # noqa: E402

from covsight.core.api.enums import CoverTypeT, HistoryNodeKind, ScopeTypeT, TestStatusT  # noqa: E402
from covsight.core.ncdb.ncdb_reader import NcdbReader          # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("verilator") is None,
                                reason="verilator not on PATH")

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def write_flow(d, runs, cov="full", check=False, merge=True):
    """One image, a SimRun per entry of ``runs`` (a list of seeds), all
    feeding covsight.Import (and covsight.Merge)."""
    tasks = [
        {"name": "src", "uses": "std.FileSet",
         "with": {"type": "systemVerilogSource", "base": DATA,
                  "include": "cov_top.sv"}},
        {"name": "img", "uses": "hdlsim.vlt.SimImage", "needs": ["src"],
         "with": {"top": ["cov_top"], "cov": cov}},
    ]
    imp_needs = []
    for i, seed in enumerate(runs):
        run = "run%d" % i
        tasks.append({"name": run, "uses": "hdlsim.vlt.SimRun", "needs": ["img"],
                      "with": {"sim": "vlt", "mode": "test" if check else "run",
                               "plusargs": ["verilator+seed+%d" % seed]}})
        if check:
            tasks.append({"name": "c%d" % i, "uses": "hdlsim.SimCheck",
                          "needs": [run]})
            imp_needs.append("c%d" % i)
        else:
            imp_needs.append(run)
    tasks.append({"name": "cov", "uses": "covsight.Import", "needs": imp_needs})
    if merge:
        tasks.append({"name": "merged", "uses": "covsight.Merge", "needs": ["cov"]})
    flow = {"package": {"name": "t",
                        "imports": [{"name": "hdlsim"}, {"name": "covsight"}],
                        "tasks": tasks}}
    with open(os.path.join(d, "flow.yaml"), "w") as fp:
        json.dump(flow, fp, indent=1)       # JSON is YAML


def run_flow(d, target):
    loader = PackageLoader()
    pkg = loader.load(os.path.join(d, "flow.yaml"))
    rundir = os.path.join(d, "rundir")
    builder = TaskGraphBuilder(root_pkg=pkg, rundir=rundir, loader=loader)
    runner = TaskSetRunner(rundir)
    runner.builder = builder
    node = builder.mkTaskNode("t." + target)
    markers = []

    def listener(task, reason):
        if reason == "leave" and task.result is not None:
            markers.extend(task.result.markers)

    runner.add_listener(listener)
    asyncio.run(runner.run([node]))
    assert runner.status == 0, [str(m.msg) for m in markers]
    return [it for it in node.output.output
            if getattr(it, "filetype", None) == "covsightNCDB"], markers


def db_paths(filesets):
    return [os.path.join(fs.basedir, f) for fs in filesets for f in fs.files]


def bins_of(db, *path):
    scopes = db.scopes(ScopeTypeT.ALL)
    scope = None
    for name in path:
        scope = next(s for s in scopes if s.getScopeName() == name
                     and not ScopeTypeT.DU_ANY(s.getScopeType()))
        scopes = scope.scopes(ScopeTypeT.ALL)
    return {ci.getName(): ci.getCoverData().data
            for ci in scope.coverItems(CoverTypeT.ALL)}


def history_tests(db):
    return {n.getLogicalName(): n for n in db.historyNodes(HistoryNodeKind.TEST)}


def test_import_single_run(tmp_path):
    d = str(tmp_path)
    write_flow(d, runs=[11], merge=False)
    out, _ = run_flow(d, "cov")
    (path,) = db_paths(out)
    assert path.endswith(".cdb") and os.path.isfile(path)
    assert "format=ncdb" in out[0].attributes

    db = NcdbReader().read(path)
    assert bins_of(db, "cov_top", "cg", "cp_flag") == {"hit_low": 8, "hit_high": 2}
    assert bins_of(db, "cov_top", "cg", "cp_count")["never"] == 0
    assert bins_of(db, "cov_top", "cover@cov_top.sv:42") == {"coverBin": 1}
    (test,) = history_tests(db).values()
    assert test.getSeed() == "11"
    assert test.getTestStatus() == TestStatusT.OK


def test_import_is_incremental(tmp_path, monkeypatch):
    """A bare simCovDb FileSet; Import reconverts only when the source
    changes (SimRun itself is never up-to-date, so this uses a fixed file)."""
    d = str(tmp_path)
    write_flow(d, runs=[1], merge=False)
    run_flow(d, "cov")
    dat = os.path.join(d, "fixed")
    os.makedirs(dat)
    shutil.copy(_find(d, "coverage.dat"), dat)
    flow = {"package": {"name": "t", "imports": [{"name": "covsight"}], "tasks": [
        {"name": "dat", "uses": "std.FileSet",
         "with": {"type": "simCovDb", "base": dat, "include": "coverage.dat",
                  "attributes": ["format=vlt-dat"]}},
        {"name": "cov", "uses": "covsight.Import", "needs": ["dat"],
         "with": {"test_name": "fixed"}}]}}
    with open(os.path.join(d, "flow.yaml"), "w") as fp:
        json.dump(flow, fp)

    (path,) = db_paths(run_flow(d, "cov")[0])
    assert os.path.basename(path) == "fixed.cdb"
    stamp = os.stat(path).st_mtime_ns
    (path,) = db_paths(run_flow(d, "cov")[0])
    assert os.stat(path).st_mtime_ns == stamp          # not reconverted
    os.utime(os.path.join(dat, "coverage.dat"))         # source "changed"
    (path,) = db_paths(run_flow(d, "cov")[0])
    assert os.stat(path).st_mtime_ns != stamp
    # A new importer revision invalidates output from the old one.
    stamp = os.stat(path).st_mtime_ns
    import covsight.core.vltcov as vltcov
    monkeypatch.setattr(vltcov, "MAPPING_REVISION", vltcov.MAPPING_REVISION + 1)
    (path,) = db_paths(run_flow(d, "cov")[0])
    assert os.stat(path).st_mtime_ns != stamp


def _find(d, name):
    return next(os.path.join(r, f) for r, _, fs in os.walk(d) for f in fs if f == name)


def test_check_verdicts_and_merge(tmp_path):
    d = str(tmp_path)
    write_flow(d, runs=[3, 4], check=True)
    out, _ = run_flow(d, "merged")
    (merged,) = db_paths(out)
    db = NcdbReader().read(merged)
    # Both cases appear in the merged history, with their seeds ...
    tests = history_tests(db)
    assert len(tests) == 2
    assert sorted(t.getSeed() for t in tests.values()) == ["3", "4"]
    # ... and the counts are the sum of two identical runs.
    assert bins_of(db, "cov_top", "cg", "cp_flag") == {"hit_low": 16, "hit_high": 4}


def test_cli_run(tmp_path):
    """Same flow through `dfm run`, as a user (and CI) would invoke it."""
    d = str(tmp_path)
    write_flow(d, runs=[7])
    r = subprocess.run([sys.executable, "-m", "dv_flow.mgr", "run", "merged"],
                       cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    found = [os.path.join(root, f) for root, _, files in os.walk(d)
             for f in files if f == "merged.cdb"]
    assert len(found) == 1
    r = subprocess.run([sys.executable, "-m", "covsight.cli", "show", "summary",
                        found[0]], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["overall_coverage"] == 75.0
