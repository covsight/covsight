"""covsight.analysis.parity: covsight's totals against verilator_coverage's.

Uses the fixtures in data/vltcov (coverage.dat plus the saved
``verilator_coverage --report summary`` output), so no Verilator is needed.
"""
import os

import pytest

from covsight.analysis import parity
from covsight.analysis.totals import kind_totals
from covsight.core.vltcov import VltParser, VltToUcis

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "vltcov")


def dat(name):
    return os.path.join(DATA, name + ".dat")


def vlt_summary(name):
    with open(os.path.join(DATA, name + ".summary.txt")) as f:
        return parity.parse_vlt_summary(f.read())


def totals(name):
    db = VltToUcis().map(VltParser().parse_file(dat(name)))
    return {k: (v.covered, v.total) for k, v in kind_totals(db).items()}


def test_parse_summary():
    s = vlt_summary("cov_top")
    assert s["line"] == (11, 30)
    assert s["branch"] == (7, 14)
    assert s["fsm_arc"] == (0, 0)
    assert s["user"] == (1, 1)


def test_std_counts_cover_the_difference():
    # cov_top's design is small; most of Verilator's line/branch/expr totals
    # are the std package (semaphore, process), which covsight drops.
    std = parity.std_counts([dat("cov_top")])
    assert std["line"] == (0, 19)
    assert set(std) <= {"line", "branch", "expr"}


# Known differences per fixture, as an example's expect.yaml would list them.
EXPLAINED = {
    "cov_top": {},
    "hier_top_pi": {
        # Verilator finding 9: FSM points written once per instance.
        "fsm_state": "Verilator duplicates FSM points per instance",
        "fsm_transition": "Verilator duplicates FSM points per instance",
        "covergroup": "Verilator counts the default bin",
    },
}


@pytest.mark.parametrize("name", sorted(EXPLAINED))
def test_fixtures_after_std(name):
    res = parity.compare(totals(name), vlt_summary(name),
                         parity.std_counts([dat(name)]), EXPLAINED[name])
    assert res, "no kinds compared"
    assert {r.kind: r.state for r in res if r.state != "match"} == {
        k: "explained" for k in EXPLAINED[name]}


def test_states():
    vlt = {"line": (5, 10), "branch": (2, 4), "toggle": (3, 3), "expr": (1, 2)}
    cs = {"line": (5, 10), "branch": (2, 3), "toggle": (3, 3), "expression": (1, 1)}
    res = {r.kind: r for r in parity.compare(
        cs, vlt, explanations={"branch": "one arm folded away",
                               "toggle": "old note"})}
    assert res["line"].state == "match"
    assert res["branch"].state == "explained"
    assert "one arm folded away" in res["branch"].describe()
    assert res["toggle"].state == "stale"
    assert res["expression"].state == "mismatch"
    # Kinds that are 0/0 on both sides are left out.
    assert "fsm_state" not in res


def test_include_std_skips_subtraction():
    vlt = {"line": (1, 5)}
    std = {"line": (0, 4)}
    (r,) = parity.compare({"line": (1, 1)}, vlt, std)
    assert r.state == "match"
    (r,) = parity.compare({"line": (1, 5)}, vlt, std, include_std=True)
    assert r.state == "match"


def test_std_points_merge_across_files():
    # The same file twice: points are keyed, so totals do not double.
    one = parity.std_counts([dat("cov_top")])
    two = parity.std_counts([dat("cov_top"), dat("cov_top")])
    assert one == two
