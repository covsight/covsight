"""covsight.dvflow.expect: loading and validating expect.yaml (no dv-flow needed)."""
import json
import os
import textwrap

import pytest
import yaml

from covsight.dvflow.expect import ExpectError, load_expect, parse_expect

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "..", "src", "covsight",
                      "dvflow", "expect.schema.json")

VALID = textwrap.dedent("""\
    totals:
      line: 11/11
      branch: 7 / 8
      fsm_state: 2/2
      covergroup: 3/4
    transcript:
      - show code-coverage -of text
      - covsight show hierarchy
    parity:
      covergroup: Verilator counts the default bin
    warnings:
      - "%Warning-COVERIGN"
    """)


def errors_of(text):
    with pytest.raises(ExpectError) as e:
        parse_expect(textwrap.dedent(text), "ex/expect.yaml")
    return e.value.errors


def test_valid():
    e = parse_expect(VALID, "ex/expect.yaml")
    assert e.totals == {"line": (11, 11), "branch": (7, 8),
                        "fsm_state": (2, 2), "covergroup": (3, 4)}
    # A leading "covsight " is dropped.
    assert e.transcript == ["show code-coverage -of text", "show hierarchy"]
    assert e.parity == {"covergroup": "Verilator counts the default bin"}
    assert e.warnings == ["%Warning-COVERIGN"]


def test_empty_file_expects_nothing():
    e = parse_expect("", "x")
    assert (e.totals, e.transcript, e.parity, e.warnings) == ({}, [], {}, [])


def test_load_from_file(tmp_path):
    p = tmp_path / "expect.yaml"
    p.write_text(VALID)
    assert load_expect(str(p)).totals["line"] == (11, 11)


@pytest.mark.parametrize("text,line,fragment", [
    ("totals:\n  line: 11\n", 2, "expected 'covered/total'"),
    ("totals:\n  line: 1/1\n  branch: 9/8\n", 3, "more than total"),
    ("totals:\n  lines: 1/1\n", 2, "unknown coverage kind 'lines'"),
    ("parity:\n  toggle: ''\n", 2, "give the reason"),
    ("transcript: show summary\n", 1, "expected a list"),
    ("warnings:\n  - '(['\n", 2, "not a valid regular expression"),
    ("totalz:\n  line: 1/1\n", 1, "unknown key 'totalz'"),
    ("totals: [1, 2]\n", 1, "expected a mapping"),
    ("- a\n- b\n", 1, "expected a mapping with keys"),
    ("totals:\n\tline: 1/1\n", 2, "not valid YAML"),
])
def test_errors_have_file_and_line(text, line, fragment):
    errs = errors_of(text)
    assert len(errs) == 1, errs
    assert errs[0].startswith("ex/expect.yaml:%d: " % line), errs[0]
    assert fragment in errs[0]


def test_all_errors_reported_at_once():
    errs = errors_of("""\
        totals:
          line: x
          bogus: 1/1
        extra: 1
        """)
    assert [e.split(":")[1] for e in errs] == ["2", "3", "4"]


def test_schema_agrees():
    jsonschema = pytest.importorskip("jsonschema")
    with open(SCHEMA) as f:
        schema = json.load(f)
    jsonschema.validate(yaml.safe_load(VALID), schema)
    for bad in ({"totals": {"line": "11"}}, {"totals": {"lines": "1/1"}},
                {"extra": 1}, {"transcript": "show summary"}):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)
    # Schema kinds are the loader's kinds.
    from covsight.analysis.totals import KINDS
    assert schema["$defs"]["kind"]["enum"] == list(KINDS)
