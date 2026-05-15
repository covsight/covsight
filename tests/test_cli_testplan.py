"""CLI tests for `covsight testplan` subcommands.

Uses subprocess so the tests exercise the full CLI stack including argparse
registration, _load_plan(), and all formatters.  A shared ``uart_yaml`` fixture
writes a realistic testplan to a tmp directory.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml


# ── helpers ───────────────────────────────────────────────────────────────────

def run(*args, cwd=None) -> subprocess.CompletedProcess:
    """Run ``covsight testplan <args>`` and return the result."""
    return subprocess.run(
        ["covsight", "testplan", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


# ── fixtures ──────────────────────────────────────────────────────────────────

UART_YAML_CONTENT = textwrap.dedent("""\
    $schema: "https://schema.covsight.io/testplan/v1"
    format_version: 1
    name: uart
    owner: dv-team
    substitutions:
      name: uart
    goals:
      - id: functional
        title: Functional verification
        status: in_progress
        goals:
          - id: reset
            title: Reset behavior
            status: complete
            testpoints:
              - name: uart_reset
                stage: V1
                desc: Verify UART recovers cleanly after reset.
                tests: [uart_smoke, uart_reset_test]
                coverage:
                  - type: covergroup
                    path: uart_env.uart_reset_cg
          - id: baud
            title: Baud rate
            status: planned
            testpoints:
              - name: uart_baud_rate
                stage: V2
                priority: high
                tests: ["uart_baud_{name}_test"]
                coverage:
                  - type: coverpoint
                    path: uart_env.uart_cg.baud_rate_cp
                requirements:
                  - system: JIRA
                    project: UART
                    item_id: REQ-7
    covergroups:
      - name: uart_cg
        desc: UART functional coverage
        coverpoints:
          - name: baud_rate_cp
            path: uart_env.uart_cg.baud_rate_cp
          - name: parity_cp
            path: uart_env.uart_cg.parity_cp
""")


@pytest.fixture
def uart_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "uart.yaml"
    p.write_text(UART_YAML_CONTENT, encoding="utf-8")
    return p


@pytest.fixture
def bad_weight_yaml(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        name: bad
        testpoints:
          - name: tp_bad
            stage: V1
            tests: [t1]
            weight: 0
    """)
    p = tmp_path / "bad_weight.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def bad_binding_yaml(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        name: bad_binding
        testpoints:
          - name: tp_bind
            stage: V1
            tests: [t1]
            coverage:
              - type: fg
                path: x.y.z
    """)
    p = tmp_path / "bad_binding.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def template_yaml(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        name: templ
        substitutions:
          intf: [a, b]
        testpoints:
          - name: tp_intf
            stage: V1
            tests: ["test_{intf}"]
    """)
    p = tmp_path / "templ.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ── show tests ────────────────────────────────────────────────────────────────

class TestShow:
    def test_show_text_default(self, uart_yaml):
        r = run("show", str(uart_yaml))
        assert r.returncode == 0, r.stderr
        assert "uart_reset" in r.stdout
        assert "uart_baud_rate" in r.stdout
        assert "uart_cg" in r.stdout

    def test_show_json(self, uart_yaml):
        r = run("show", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["name"] == "uart"

    def test_show_yaml(self, uart_yaml):
        r = run("show", str(uart_yaml), "-of", "yaml")
        assert r.returncode == 0, r.stderr
        data = yaml.safe_load(r.stdout)
        assert data["name"] == "uart"

    def test_show_section_goals(self, uart_yaml):
        r = run("show", str(uart_yaml), "-s", "goals")
        assert r.returncode == 0, r.stderr
        assert "Functional" in r.stdout  # goal title
        # covergroups section should be absent when only goals requested
        assert "uart_cg" not in r.stdout

    def test_show_section_testpoints(self, uart_yaml):
        r = run("show", str(uart_yaml), "-s", "testpoints")
        assert r.returncode == 0, r.stderr
        # Top-level testpoints only (none in fixture — they're in goals)
        # The command should still run without error
        assert r.returncode == 0

    def test_show_section_covergroups(self, uart_yaml):
        r = run("show", str(uart_yaml), "-s", "covergroups")
        assert r.returncode == 0, r.stderr
        assert "uart_cg" in r.stdout
        assert "uart_reset" not in r.stdout

    def test_show_filter_stage_v1(self, uart_yaml):
        r = run("show", str(uart_yaml), "--stage", "V1")
        assert r.returncode == 0, r.stderr
        assert "uart_reset" in r.stdout
        assert "uart_baud_rate" not in r.stdout

    def test_show_filter_stage_v2(self, uart_yaml):
        r = run("show", str(uart_yaml), "--stage", "V2")
        assert r.returncode == 0, r.stderr
        assert "uart_baud_rate" in r.stdout
        assert "uart_reset" not in r.stdout

    def test_show_filter_status_complete(self, uart_yaml):
        r = run("show", str(uart_yaml), "--status", "complete")
        assert r.returncode == 0, r.stderr
        assert "Reset behavior" in r.stdout or "reset" in r.stdout.lower()
        # planned baud goal should not appear
        assert "Baud rate" not in r.stdout

    def test_show_depth_1(self, uart_yaml):
        r = run("show", str(uart_yaml), "-d", "1")
        assert r.returncode == 0, r.stderr
        assert "Functional verification" in r.stdout or "functional" in r.stdout
        # Depth 1 = show top goals only, not sub-goals
        assert "Reset behavior" not in r.stdout
        assert "Baud rate" not in r.stdout

    def test_show_coverage(self, uart_yaml):
        r = run("show", str(uart_yaml), "--show-coverage")
        assert r.returncode == 0, r.stderr
        assert "uart_env.uart_cg.baud_rate_cp" in r.stdout
        assert "uart_env.uart_reset_cg" in r.stdout

    def test_show_requirements(self, uart_yaml):
        r = run("show", str(uart_yaml), "--show-requirements")
        assert r.returncode == 0, r.stderr
        assert "REQ-7" in r.stdout

    def test_show_out_file_json(self, uart_yaml, tmp_path):
        out = tmp_path / "out.json"
        r = run("show", str(uart_yaml), "-of", "json", "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["name"] == "uart"

    def test_show_missing_file(self, tmp_path):
        r = run("show", str(tmp_path / "no_such.yaml"))
        assert r.returncode == 1
        assert "not found" in r.stderr.lower() or "error" in r.stderr.lower()

    def test_show_json_no_coverage_by_default(self, uart_yaml):
        r = run("show", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        # coverage key should be stripped from output by default in JSON mode
        for goal in data.get("goals", []):
            for sub in goal.get("goals", []):
                for tp in sub.get("testpoints", []):
                    assert "coverage" not in tp


# ── validate tests ────────────────────────────────────────────────────────────

class TestValidate:
    def test_validate_ok(self, uart_yaml):
        r = run("validate", str(uart_yaml))
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_validate_multiple_ok(self, uart_yaml):
        r = run("validate", str(uart_yaml), str(uart_yaml))
        assert r.returncode == 0, r.stderr
        assert r.stdout.count("OK") >= 2

    def test_validate_bad_weight(self, bad_weight_yaml):
        r = run("validate", str(bad_weight_yaml))
        assert r.returncode == 1
        assert "weight" in r.stdout.lower() or "weight" in r.stderr.lower()

    def test_validate_unknown_binding_schema_error(self, bad_binding_yaml):
        # JSON Schema defines binding type as enum; unknown type is always a schema error
        r = run("validate", str(bad_binding_yaml))
        assert r.returncode == 1
        # The invalid type should appear somewhere in the error output
        assert "fg" in r.stdout or "fg" in r.stderr

    def test_validate_unknown_binding_strict(self, bad_binding_yaml):
        r = run("validate", str(bad_binding_yaml), "--strict")
        assert r.returncode == 1
        assert "fg" in r.stdout or "fg" in r.stderr

    def test_validate_missing_file(self, tmp_path):
        r = run("validate", str(tmp_path / "no_such.yaml"))
        assert r.returncode == 1

    def test_validate_json_output_ok(self, uart_yaml):
        r = run("validate", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["passed"] is True
        assert data["files"][0]["errors"] == []

    def test_validate_json_output_fail(self, bad_weight_yaml):
        r = run("validate", str(bad_weight_yaml), "-of", "json")
        assert r.returncode == 1
        data = json.loads(r.stdout)
        assert data["passed"] is False
        assert len(data["files"][0]["errors"]) >= 1


# ── stats tests ───────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_text(self, uart_yaml):
        r = run("stats", str(uart_yaml))
        assert r.returncode == 0, r.stderr
        assert "Testpoints" in r.stdout
        assert "Goals" in r.stdout

    def test_stats_json(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["testpoints"]["total"] == 2

    def test_stats_by_stage(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["testpoints"]["by_stage"].get("V1") == 1
        assert data["testpoints"]["by_stage"].get("V2") == 1

    def test_stats_with_coverage(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["testpoints"]["with_coverage"] == 2

    def test_stats_with_requirements(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["testpoints"]["with_requirements"] == 1

    def test_stats_goals_depth(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["goals"]["max_depth"] == 2

    def test_stats_goals_total(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["goals"]["total"] == 3  # functional + reset + baud

    def test_stats_covergroups(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["covergroups"]["declared"] == 1
        assert data["covergroups"]["coverpoints_listed"] == 2

    def test_stats_coverage_by_type(self, uart_yaml):
        r = run("stats", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        by_type = data["coverage_bindings"]["by_type"]
        assert by_type.get("covergroup") == 1
        assert by_type.get("coverpoint") == 1


# ── convert tests ─────────────────────────────────────────────────────────────

class TestConvert:
    def test_convert_yaml_to_json(self, uart_yaml):
        r = run("convert", str(uart_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["name"] == "uart"

    def test_convert_yaml_to_json_file(self, uart_yaml, tmp_path):
        out = tmp_path / "out.json"
        r = run("convert", str(uart_yaml), "-of", "json", "-o", str(out))
        assert r.returncode == 0, r.stderr
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["name"] == "uart"

    def test_convert_yaml_to_yaml(self, uart_yaml):
        r = run("convert", str(uart_yaml), "-of", "yaml")
        assert r.returncode == 0, r.stderr
        data = yaml.safe_load(r.stdout)
        assert data["name"] == "uart"

    def test_convert_roundtrip(self, uart_yaml, tmp_path):
        # yaml -> json -> yaml
        json_path = tmp_path / "uart.json"
        r1 = run("convert", str(uart_yaml), "-of", "json", "-o", str(json_path))
        assert r1.returncode == 0, r1.stderr
        r2 = run("convert", str(json_path), "-of", "yaml")
        assert r2.returncode == 0, r2.stderr
        data = yaml.safe_load(r2.stdout)
        assert data["name"] == "uart"

    def test_convert_default_output_is_yaml(self, uart_yaml):
        r = run("convert", str(uart_yaml))
        assert r.returncode == 0, r.stderr
        # Should parse as YAML
        data = yaml.safe_load(r.stdout)
        assert data is not None
        assert data["name"] == "uart"

    def test_convert_vendor_format_deferred(self, tmp_path):
        fake_xml = tmp_path / "foo.xml"
        fake_xml.write_text("<testplan/>")
        r = run("convert", str(fake_xml), "-if", "vpf")
        assert r.returncode == 1
        assert "not yet wired" in r.stderr.lower() or "not yet" in r.stderr

    def test_convert_with_subs(self, template_yaml):
        r = run("convert", str(template_yaml), "-of", "json")
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        # Substitution {intf} expands to a,b  => two tests
        all_tests = []
        for tp in data.get("testpoints", []):
            all_tests.extend(tp.get("tests", []))
        assert "test_a" in all_tests
        assert "test_b" in all_tests


# ── smoke extension ───────────────────────────────────────────────────────────

class TestSmoke:
    def test_testplan_help(self):
        r = run("--help")
        assert r.returncode == 0, r.stderr
        assert "show" in r.stdout
        assert "validate" in r.stdout
        assert "stats" in r.stdout
        assert "convert" in r.stdout
        assert "export" in r.stdout

    def test_show_help(self):
        r = run("show", "--help")
        assert r.returncode == 0, r.stderr
        assert "--show-coverage" in r.stdout
        assert "--depth" in r.stdout or "-d" in r.stdout

    def test_validate_help(self):
        r = run("validate", "--help")
        assert r.returncode == 0, r.stderr
        assert "--strict" in r.stdout

    def test_stats_help(self):
        r = run("stats", "--help")
        assert r.returncode == 0, r.stderr

    def test_convert_help(self):
        r = run("convert", "--help")
        assert r.returncode == 0, r.stderr
        assert "--no-resolve-imports" in r.stdout
