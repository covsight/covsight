"""Testplan subcommands."""
from __future__ import annotations

import sys


def _open_ncdb(path: str):
    from covsight.core.ncdb.ncdb_ucis import NcdbUCIS
    return NcdbUCIS(path)


def cmd_testplan_import(args) -> None:
    from covsight.core.ncdb.testplan_hjson import import_hjson
    from covsight.core.ncdb.ncdb_writer import NcdbWriter
    import os

    subs: dict = {}
    for s in getattr(args, "subs", []) or []:
        if "=" in s:
            k, _, v = s.partition("=")
            subs.setdefault(k, []).append(v)

    plan = import_hjson(args.hjson_path, substitutions=subs or None)
    db = _open_ncdb(args.db)
    db.setTestplan(plan)
    tmp = args.db + ".tmp"
    NcdbWriter().write(db, tmp)
    os.replace(tmp, args.db)
    print(f"Imported testplan from '{args.hjson_path}': {len(plan.testpoints)} testpoints, {len(plan.covergroups)} covergroups")


def cmd_testplan_closure(args) -> None:
    from covsight.core.ncdb.testplan import get_testplan, Testplan
    from covsight.core.ncdb.testplan_closure import compute_closure
    from covsight.core.ncdb.reports import report_testpoint_closure, format_testpoint_closure, report_stage_gate, format_stage_gate
    from covsight.core.ncdb.waivers import WaiverSet

    db = _open_ncdb(args.db)
    plan = Testplan.load(args.testplan) if getattr(args, "testplan", None) else get_testplan(db)
    if plan is None:
        print("Error: no testplan found. Embed one with 'covsight testplan import' or supply --testplan.", file=sys.stderr)
        sys.exit(1)

    waivers = None
    if getattr(args, "waivers", None):
        waivers = WaiverSet.load(args.waivers)
    elif hasattr(db, "getWaivers"):
        waivers = db.getWaivers()

    results = compute_closure(plan, db, waivers=waivers)
    out = open(args.out, "w") if getattr(args, "out", None) else sys.stdout
    try:
        summary = report_testpoint_closure(results)
        if getattr(args, "output_format", "text") == "json":
            out.write(summary.to_json() + "\n")
        else:
            out.write(format_testpoint_closure(summary) + "\n")
            if getattr(args, "stage", None):
                gate = report_stage_gate(results, args.stage, plan)
                out.write("\n" + format_stage_gate(gate) + "\n")
    finally:
        if out is not sys.stdout:
            out.close()


def cmd_testplan_export_junit(args) -> None:
    from covsight.core.ncdb.testplan import get_testplan, Testplan
    from covsight.core.ncdb.testplan_closure import compute_closure
    from covsight.core.ncdb.testplan_export import export_junit_xml

    db = _open_ncdb(args.db)
    plan = Testplan.load(args.testplan) if getattr(args, "testplan", None) else get_testplan(db)
    if plan is None:
        print("Error: no testplan found. Embed one with 'covsight testplan import' or supply --testplan.", file=sys.stderr)
        sys.exit(1)

    results = compute_closure(plan, db)
    output_path = getattr(args, "out", None) or "closure_results.xml"
    suite_name = getattr(args, "suite_name", None) or "testplan_closure"
    export_junit_xml(results, output_path, suite_name=suite_name)
    print(f"JUnit XML written to '{output_path}'")


def register(subparsers):
    parser = subparsers.add_parser("testplan", help="Manage testplans embedded in NCDB databases")
    tp = parser.add_subparsers(dest="testplan_cmd")

    imp = tp.add_parser("import", help="Import an Hjson/JSON testplan into a .cdb file")
    imp.add_argument("db", help="Path to the NCDB .cdb file")
    imp.add_argument("hjson_path", help="Path to the .hjson or .json testplan file")
    imp.add_argument("--subs", metavar="KEY=VAL", action="append", default=[], help="Template substitution (repeatable)")
    imp.set_defaults(func=cmd_testplan_import)

    closure = tp.add_parser("closure", help="Compute and display testpoint closure")
    closure.add_argument("db", help="Path to the NCDB .cdb file")
    closure.add_argument("--testplan", default=None, metavar="PATH", help="External testplan JSON file")
    closure.add_argument("--waivers", default=None, metavar="PATH", help="External waivers JSON file")
    closure.add_argument("--stage", default=None, metavar="STAGE", help="Evaluate a stage gate")
    closure.add_argument("--out", "-o", default=None, help="Output file")
    closure.add_argument("--output-format", "-of", default="text", choices=["text", "json"], help="Output format")
    closure.set_defaults(func=cmd_testplan_closure)

    junit = tp.add_parser("export-junit", help="Export testpoint closure results as JUnit XML")
    junit.add_argument("db", help="Path to the NCDB .cdb file")
    junit.add_argument("--testplan", default=None, metavar="PATH", help="External testplan JSON file")
    junit.add_argument("--out", "-o", default=None, help="Output XML file")
    junit.add_argument("--suite-name", default=None, metavar="NAME", help="JUnit testsuite name attribute")
    junit.set_defaults(func=cmd_testplan_export_junit)
