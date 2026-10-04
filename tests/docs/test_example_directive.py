"""docs/source/_ext/covsight_example.py on a small Sphinx project.

The generated tree is faked; examples/collect_docs.py (tested with the
example flow in tests/dvflow/test_examples.py) writes the real one.
"""
import json
import os
import re
import subprocess
import sys

import pytest

pytest.importorskip("sphinx")

EXT = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "source", "_ext")

PAGE = """\
Example
=======

.. covsight-transcript:: ex/show_a

.. covsight-transcript:: ex/show_a
   :commands: 2

.. covsight-parity:: ex

.. covsight-download:: ex/merged.cdb

.. covsight-source:: ex/show_a
   :command: 3
   :lines: 2-3
"""


SOURCE = {"database": "m.cdb", "files": [{
    "file": "d.sv", "found": True,
    "by_kind": {"line": {"covered": 1, "total": 2, "coverage": 50.0}},
    "lines": [
        {"line": 1, "text": "module d;", "count": None, "status": None, "annotations": []},
        {"line": 2, "text": "  if (a && b) x = 1;", "count": 4, "status": "partial",
         "annotations": [{"kind": "expression", "scope": "d.sv:2:9", "col": 9, "rows": [
             {"name": "(a==1 && b==1) => 1", "count": 0, "covered": False},
             {"name": "(a==0) => 0", "count": 4, "covered": True}]}]},
        {"line": 3, "text": "  y = 2;", "count": 0, "status": "missed", "annotations": []},
        {"line": 4, "text": "endmodule", "count": None, "status": None, "annotations": []}]}]}


def project(tmp_path, gen=True):
    src = tmp_path / "src"
    src.mkdir()
    (src / "conf.py").write_text(
        "import sys\nsys.path.insert(0, %r)\nextensions = ['covsight_example']\n"
        % os.path.abspath(EXT))
    (src / "index.rst").write_text(PAGE)
    if gen:
        ex = src / "examples" / "_gen" / "ex"
        (ex / "show_a").mkdir(parents=True)
        (ex / "show_a" / "01-show-summary.txt").write_text("SUMMARY OUT\n")
        (ex / "show_a" / "02-show-hierarchy.txt").write_text("HIER OUT\n")
        (ex / "show_a" / "transcript.json").write_text(json.dumps([
            {"command": "covsight show summary m.cdb", "file": "01-show-summary.txt", "status": 0},
            {"command": "covsight show hierarchy m.cdb", "file": "02-show-hierarchy.txt", "status": 0},
            {"command": "covsight show source m.cdb -of json", "file": "03-show-source.txt", "status": 0}]))
        (ex / "show_a" / "03-show-source.txt").write_text(json.dumps(SOURCE))
        (ex / "check.json").write_text(json.dumps({"passed": True, "parity": [
            {"kind": "line", "state": "match", "covsight": "9/9", "verilator": "9/9",
             "verilator_without_std": "9/9", "explanation": ""},
            {"kind": "covergroup", "state": "explained", "covsight": "3/4",
             "verilator": "3/5", "verilator_without_std": "3/5",
             "explanation": "Verilator counts the ignore bin"}]}))
        (ex / "merged.cdb").write_bytes(b"PK")
    return src


def build(src, out, required=False):
    env = dict(os.environ)
    env.pop("COVSIGHT_EXAMPLES_REQUIRED", None)
    if required:
        env["COVSIGHT_EXAMPLES_REQUIRED"] = "1"
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-E", "-q", "-b", "text",
                        str(src), str(out)], capture_output=True, text=True, env=env)
    text = (out / "index.txt").read_text() if (out / "index.txt").exists() else ""
    return r, text


def test_renders_transcripts_parity_and_download(tmp_path):
    r, text = build(project(tmp_path), tmp_path / "out", required=True)
    assert r.returncode == 0, r.stderr
    assert "$ covsight show summary m.cdb\nSUMMARY OUT" in text.replace("   ", "")
    assert text.count("HIER OUT") == 2            # all commands, then :commands: 2
    assert text.count("SUMMARY OUT") == 1
    assert "differs (explained)" in text and "Verilator counts the ignore bin" in text
    assert "Download: \"merged.cdb\"" in text
    # covsight-source: the text builder gets show source's text, lines 2-3
    assert "d.sv  line 1/2" in text
    assert "2 ~ 4 |   if (a && b) x = 1;" in text and "3 # 0 |   y = 2;" in text
    assert "# 0 |   (a==1 && b==1) => 1" in text
    assert not re.search(r"^\s*1\s+\| module d;", text, re.M)   # :lines: 2-3


def test_source_html(tmp_path):
    out = tmp_path / "out"
    env = dict(os.environ, COVSIGHT_EXAMPLES_REQUIRED="1")
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-E", "-q", "-b", "html",
                        str(project(tmp_path)), str(out)], capture_output=True, text=True,
                       env=env)
    assert r.returncode == 0, r.stderr
    html = (out / "index.html").read_text()
    assert html.count('class="covsight-source"') == 1
    assert '<tr class="cs-partial"><td class="cs-ln">2</td><td class="cs-n">4</td>' in html
    assert '<tr class="cs-missed"><td class="cs-ln">3</td>' in html
    assert "(a==1 &amp;&amp; b==1) =&gt; 1" in html          # escaped
    assert 'class="cs-ln">1<' not in html                     # :lines: 2-3
    assert (out / "_static" / "covsight-example.css").is_file()


def test_missing_output_is_a_note(tmp_path):
    r, text = build(project(tmp_path, gen=False), tmp_path / "out")
    assert r.returncode == 0, r.stderr               # -W: no warning either
    assert text.count("has not been generated") == 5


def test_missing_output_fails_when_required(tmp_path):
    r, _ = build(project(tmp_path, gen=False), tmp_path / "out", required=True)
    assert r.returncode != 0
    assert "example output not found" in r.stderr
