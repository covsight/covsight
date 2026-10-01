"""covsight.dvflow.sources: finding coverage databases among task inputs.

Inputs are given as dicts -- the shape items take after a dv-flow cache
round-trip -- so no simulator or dv-flow-mgr is needed.
"""
from covsight.dvflow.sources import collect_sources, ncdb_paths, safe_name


def cov_fs(rundir, fmt="vlt-dat", files=("coverage.dat",)):
    return {"type": "std.FileSet", "filetype": "simCovDb", "basedir": rundir,
            "files": list(files), "attributes": ["role=cov", "format=%s" % fmt]}


def sim_run(rundir, status=0, **runinfo):
    return {"type": "hdlsim.SimRunResult", "status": status,
            "runinfo": dict(runinfo, rundir=rundir),
            "artifacts": [{"type": "std.FileSet", "filetype": "simLog",
                           "basedir": rundir, "files": ["sim.log"]},
                          cov_fs(rundir)]}


def test_sim_run_result():
    (src,) = collect_sources([sim_run("/w/run_a", seed=5)])
    assert src.path == "/w/run_a/coverage.dat"
    assert src.covsight_format == "vltcov"
    assert (src.test_name, src.seed, src.status) == ("run_a", "5", "pass")


def test_sim_run_failed_and_case_name():
    (src,) = collect_sources([sim_run("/w/r", status=3, case_name="smoke")])
    assert (src.test_name, src.seed, src.status) == ("smoke", None, "error")


def test_test_result_wins_over_forwarded_sim_run():
    rr = sim_run("/w/r1")
    tr = {"type": "hdlsim.TestResult", "name": "c0", "status": "fail",
          "passed": False, "seed": 9, "runinfo": {}, "artifacts": rr["artifacts"]}
    for order in ([rr, tr], [tr, rr]):
        (src,) = collect_sources(order)
        assert (src.test_name, src.seed, src.status, src.origin) == (
            "c0", "9", "fail", "hdlsim.TestResult")


def test_suite_result():
    trs = [{"type": "hdlsim.TestResult", "name": n, "status": "pass",
            "passed": True, "seed": 0, "artifacts": [cov_fs("/w/" + n)]}
           for n in ("a", "b")]
    srcs = collect_sources([{"type": "hdlsim.SuiteResult", "results": trs}])
    assert [(s.test_name, s.seed) for s in srcs] == [("a", None), ("b", None)]


def test_bare_fileset_and_unknown_format():
    srcs = collect_sources([cov_fs("/w/x", fmt="xezim-json", files=["xezim_cov.json"])])
    assert srcs[0].test_name == "x" and srcs[0].covsight_format is None


def test_ignores_unrelated_items():
    assert collect_sources([{"type": "std.FileSet", "filetype": "simLog",
                             "basedir": "/w", "files": ["sim.log"]}]) == []


def test_ncdb_paths_and_safe_name():
    items = [{"filetype": "covsightNCDB", "basedir": "/o", "files": ["a.cdb"]},
             {"filetype": "covsightNCDB", "basedir": "/o", "files": ["a.cdb", "b.cdb"]},
             {"filetype": "simCovDb", "basedir": "/o", "files": ["c.dat"]}]
    assert ncdb_paths(items) == ["/o/a.cdb", "/o/b.cdb"]
    assert safe_name("t.c0 [x]/y") == "t.c0_x_y"
