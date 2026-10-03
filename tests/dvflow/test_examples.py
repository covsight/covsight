"""The example suite (examples/) end to end: each example runs, its check
passes, `dfm run docs` writes the tree the docs directives read, and a
total that moves fails the run.

Runs a copy of examples/ in a temporary directory (Verilator required).
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "..", "examples")
SUITE = ["01-code-basics"]


@pytest.fixture(scope="module")
def suite(tmp_path_factory):
    pytest.importorskip("dv_flow.libhdlsim")
    if shutil.which("verilator") is None:
        pytest.skip("verilator not on PATH")
    root = tmp_path_factory.mktemp("ex")
    dst = root / "examples"
    dst.mkdir()
    for f in ("flow.yaml", "collect_docs.py"):
        shutil.copy(os.path.join(EXAMPLES, f), dst)
    for ex in SUITE:
        shutil.copytree(os.path.join(EXAMPLES, ex), dst / ex,
                        ignore=shutil.ignore_patterns("rundir"))
    return root


def dfm(cwd, task):
    return subprocess.run([sys.executable, "-m", "dv_flow.mgr", "run", task],
                          cwd=cwd, capture_output=True, text=True)


def test_suite_imports_every_example():
    with open(os.path.join(EXAMPLES, "flow.yaml")) as f:
        text = f.read()
    for ex in SUITE:
        assert "from: %s/flow.yaml" % ex in text


def test_docs_tree(suite):
    r = dfm(suite / "examples", "docs")
    assert r.returncode == 0, r.stdout + r.stderr
    gen = suite / "docs" / "source" / "examples" / "_gen" / "01-code-basics"
    check = json.loads((gen / "check.json").read_text())
    assert check["passed"], check["errors"]
    assert {p["state"] for p in check["parity"]} == {"match"}
    assert (gen / "merged.cdb").is_file()
    for show in ("show_basic", "show_merged"):
        index = json.loads((gen / show / "transcript.json").read_text())
        assert index and all(e["status"] == 0 for e in index)
        for e in index:
            text = (gen / show / e["file"]).read_text()
            assert str(suite) not in text, "absolute path in %s" % e["file"]
    basic = (gen / "show_basic" / "01-show-code-coverage.txt").read_text()
    assert "line              8      9" in basic        # the hole t_full closes


def test_moved_total_fails(suite):
    ex = suite / "examples" / "01-code-basics"
    expect = (ex / "expect.yaml").read_text()
    (ex / "expect.yaml").write_text(expect.replace("line: 9/9", "line: 8/9"))
    try:
        r = dfm(suite / "examples", "all")
        assert r.returncode != 0
        assert "totals.line" in r.stdout        # dfm wraps the full message
    finally:
        (ex / "expect.yaml").write_text(expect)
