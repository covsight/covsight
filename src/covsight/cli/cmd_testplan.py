"""Testplan subcommands."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional


# ── shared parent parsers ─────────────────────────────────────────────────────

_P_INPUT = argparse.ArgumentParser(add_help=False)
_P_INPUT.add_argument(
    "--input-format", "-if",
    dest="input_format",
    default="auto",
    metavar="FMT",
    help="Input format: auto | yaml | json | hjson  (default: auto)",
)
_P_INPUT.add_argument(
    "--subs",
    metavar="KEY=VAL",
    action="append",
    default=[],
    help="Template substitution KEY=VAL (repeatable; multi-value: KEY=A KEY=B)",
)

_P_OUTPUT = argparse.ArgumentParser(add_help=False)
_P_OUTPUT.add_argument(
    "--output-format", "-of",
    dest="output_format",
    default="text",
    metavar="FMT",
    help="Output format: text | json | yaml  (default: text)",
)
_P_OUTPUT.add_argument(
    "--out", "-o",
    default=None,
    help="Output file path (default: stdout)",
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _open_ncdb(path: str):
    from covsight.core.ncdb.ncdb_ucis import NcdbUCIS
    return NcdbUCIS(path)


def _parse_subs(args) -> dict:
    """Parse --subs KEY=VAL items from args into a substitution dict."""
    subs: dict = {}
    for s in getattr(args, "subs", []) or []:
        if "=" in s:
            k, _, v = s.partition("=")
            subs.setdefault(k, []).append(v)
    # Flatten single-element lists to scalars for cleaner substitution output.
    return {k: (v[0] if len(v) == 1 else v) for k, v in subs.items()}


def _load_plan(args):
    """Load a testplan from args.testplan using args.input_format and args.subs.

    Raises SystemExit(1) with a human-readable message on any error.
    Returns a fully-resolved :class:`~covsight.core.ncdb.testplan.Testplan`.
    """
    from covsight.core.ncdb.testplan_yaml import load_testplan
    from covsight.core.ncdb.testplan_imports import ParseError

    fmt = getattr(args, "input_format", "auto") or "auto"
    _SUPPORTED = {"auto", "yaml", "json", "hjson"}
    if fmt not in _SUPPORTED:
        print(
            f"Error: --input-format '{fmt}' is not yet wired into the CLI.\n"
            f"  Supported values: {', '.join(sorted(_SUPPORTED))}.\n"
            f"  Vendor format support (vpf, vcplanner, questa) is planned for a\n"
            f"  future release via the covsight-core format registry.",
            file=sys.stderr,
        )
        sys.exit(1)

    path = args.testplan
    subs = _parse_subs(args)

    try:
        return load_testplan(path, substitutions=subs or None)
    except FileNotFoundError as e:
        print(f"Error: testplan file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except ParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading testplan '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def _open_output(args):
    """Return (file_object, should_close) for the output destination."""
    path = getattr(args, "out", None)
    if path:
        return open(path, "w", encoding="utf-8"), True
    return sys.stdout, False


def _serialise(obj: dict, fmt: str) -> str:
    """Serialise a dict to a string in the requested format."""
    if fmt == "json":
        return json.dumps(obj, indent=2)
    if fmt in ("yaml", "yml"):
        import yaml  # type: ignore[import-untyped]
        return yaml.dump(obj, default_flow_style=False, allow_unicode=True).rstrip()
    raise ValueError(f"Unknown serialisation format: {fmt!r}")


# ── show ──────────────────────────────────────────────────────────────────────

def cmd_testplan_show(args) -> None:
    """Display testplan contents as a tree or structured data."""
    from covsight.core.ncdb.testplan import Testplan, Goal, Testpoint, iter_testpoints

    plan = _load_plan(args)
    fmt = getattr(args, "output_format", "text") or "text"
    sections = set(getattr(args, "section", None) or ["all"])
    if "all" in sections:
        sections = {"goals", "testpoints", "covergroups"}

    # Filters
    stage_filter: List[str] = list(getattr(args, "stage", None) or [])
    status_filter: List[str] = list(getattr(args, "status", None) or [])
    owner_filter: str = getattr(args, "owner", None) or ""
    tag_filter: List[str] = list(getattr(args, "tag", None) or [])
    max_depth: Optional[int] = getattr(args, "depth", None)
    show_cov: bool = getattr(args, "show_coverage", False)
    show_req: bool = getattr(args, "show_requirements", False)
    show_custom: bool = getattr(args, "show_custom", False)

    out, should_close = _open_output(args)
    try:
        if fmt in ("json", "yaml"):
            _show_structured(plan, fmt, sections, stage_filter, status_filter,
                             owner_filter, tag_filter, show_cov, show_req,
                             show_custom, out)
        else:
            _show_text(plan, sections, stage_filter, status_filter,
                       owner_filter, tag_filter, max_depth, show_cov,
                       show_req, show_custom, out)
    finally:
        if should_close:
            out.close()


def _tp_matches_filters(tp, stage_filter, owner_filter, tag_filter) -> bool:
    if stage_filter and tp.stage not in stage_filter:
        return False
    if owner_filter and owner_filter.lower() not in tp.owner.lower():
        return False
    if tag_filter and not any(t in tp.tags for t in tag_filter):
        return False
    return True


def _goal_matches_filters(goal, status_filter, owner_filter, tag_filter) -> bool:
    if status_filter and goal.status not in status_filter:
        return False
    if owner_filter and owner_filter.lower() not in goal.owner.lower():
        return False
    if tag_filter and not any(t in goal.tags for t in tag_filter):
        return False
    return True


def _goal_tree_has_match(goal, status_filter, owner_filter, tag_filter) -> bool:
    """Return True if this goal or any descendant passes all filters."""
    if _goal_matches_filters(goal, status_filter, owner_filter, tag_filter):
        return True
    return any(
        _goal_tree_has_match(sub, status_filter, owner_filter, tag_filter)
        for sub in goal.goals
    )


def _render_testpoint(tp, indent: str, show_cov: bool, show_req: bool,
                       show_custom: bool, out) -> None:
    prio = f"  ★ {tp.priority}" if tp.priority else ""
    n_tests = len(tp.tests)
    tests_str = f"  {n_tests} test{'s' if n_tests != 1 else ''}"
    na_str = "  [N/A]" if tp.na else ""
    desc_str = f"  — {tp.desc}" if tp.desc else ""
    stage_str = f"[{tp.stage}] " if tp.stage else ""
    out.write(f"{indent}{stage_str}{tp.name}{prio}{tests_str}{na_str}{desc_str}\n")
    if tp.tests:
        out.write(f"{indent}  {', '.join(tp.tests)}\n")
    if show_cov and tp.coverage:
        for b in tp.coverage:
            out.write(f"{indent}  ↳ {b.type:<12} {b.path}\n")
    if show_req and tp.requirements:
        for r in tp.requirements:
            ref = f"{r.system}/{r.project}/{r.item_id}" if r.system else r.item_id
            url_str = f"  ({r.url})" if r.url else ""
            out.write(f"{indent}  ⟶ req  {ref}{url_str}\n")
    if show_custom and tp.custom:
        out.write(f"{indent}  custom: {json.dumps(tp.custom)}\n")


def _render_goal(goal, indent: str, depth: int, max_depth: Optional[int],
                 stage_filter, status_filter, owner_filter, tag_filter,
                 show_cov, show_req, show_custom, out) -> None:
    # Skip if neither this goal nor any descendant matches the filters
    if not _goal_tree_has_match(goal, status_filter, owner_filter, tag_filter):
        return

    status_str = f"  [{goal.status}]" if goal.status else ""
    owner_str = f"  @{goal.owner}" if goal.owner else ""
    out.write(f"{indent}Goal: {goal.title or goal.id}{status_str}{owner_str}\n")

    if max_depth is not None and depth >= max_depth:
        return

    for tp in goal.testpoints:
        if _tp_matches_filters(tp, stage_filter, owner_filter, tag_filter):
            _render_testpoint(tp, indent + "  ", show_cov, show_req, show_custom, out)

    for sub in goal.goals:
        _render_goal(sub, indent + "  ", depth + 1, max_depth, stage_filter,
                     status_filter, owner_filter, tag_filter, show_cov, show_req,
                     show_custom, out)


def _show_text(plan, sections, stage_filter, status_filter, owner_filter,
               tag_filter, max_depth, show_cov, show_req, show_custom, out) -> None:
    name_str = plan.name or "(unnamed)"
    src_str = f"  ({plan.source_file})" if plan.source_file else ""
    out.write(f"[plan] {name_str}{src_str}\n")

    if "goals" in sections or "testpoints" in sections:
        # Top-level testpoints (not in any goal)
        if "testpoints" in sections:
            for tp in plan.testpoints:
                if _tp_matches_filters(tp, stage_filter, owner_filter, tag_filter):
                    _render_testpoint(tp, "  ", show_cov, show_req, show_custom, out)

        if "goals" in sections:
            for goal in plan.goals:
                _render_goal(goal, "  ", 1, max_depth, stage_filter, status_filter,
                             owner_filter, tag_filter, show_cov, show_req,
                             show_custom, out)

    if "covergroups" in sections and plan.covergroups:
        out.write("  Covergroups:\n")
        for cg in plan.covergroups:
            n_cp = len(cg.coverpoints)
            cp_str = f"  ({n_cp} coverpoint{'s' if n_cp != 1 else ''})" if n_cp else ""
            out.write(f"    {cg.name}{cp_str}")
            if cg.desc:
                out.write(f"  — {cg.desc}")
            out.write("\n")
            if show_cov:
                for cp in cg.coverpoints:
                    path_str = f"  {cp.path}" if cp.path else ""
                    out.write(f"      {cp.name}{path_str}\n")


def _show_structured(plan, fmt, sections, stage_filter, status_filter,
                     owner_filter, tag_filter, show_cov, show_req, show_custom,
                     out) -> None:
    d = plan.to_dict()
    # Apply section filter
    keys_to_keep = set()
    always = {"$schema", "format_version", "name", "description", "owner",
               "tags", "substitutions", "imports", "source_file", "custom"}
    keys_to_keep |= always
    if "goals" in sections:
        keys_to_keep.add("goals")
    if "testpoints" in sections:
        keys_to_keep.add("testpoints")
    if "covergroups" in sections:
        keys_to_keep.add("covergroups")
    d = {k: v for k, v in d.items() if k in keys_to_keep}

    if not show_cov:
        _strip_key_recursive(d, "coverage")
    if not show_req:
        _strip_key_recursive(d, "requirements")
    if not show_custom:
        _strip_key_recursive(d, "custom")

    out.write(_serialise(d, fmt) + "\n")


def _strip_key_recursive(obj, key: str) -> None:
    if isinstance(obj, dict):
        obj.pop(key, None)
        for v in obj.values():
            _strip_key_recursive(v, key)
    elif isinstance(obj, list):
        for item in obj:
            _strip_key_recursive(item, key)


# ── validate ──────────────────────────────────────────────────────────────────

def cmd_testplan_validate(args) -> None:
    """Validate one or more testplan files."""
    from covsight.core.ncdb.testplan_yaml import load_testplan, validate_testplan
    from covsight.core.ncdb.testplan_imports import ParseError
    from covsight.core.ncdb.testplan import CoverageBinding

    strict: bool = getattr(args, "strict", False)
    fmt = getattr(args, "output_format", "text") or "text"
    out, should_close = _open_output(args)

    overall_ok = True
    all_results = []

    try:
        for path in args.testplans:
            errors: List[dict] = []
            warnings: List[dict] = []

            # 1. Parse
            subs = _parse_subs(args)
            try:
                plan = load_testplan(path, substitutions=subs or None)
            except FileNotFoundError:
                errors.append({"path": path, "loc": "", "msg": "file not found"})
                all_results.append({"file": path, "errors": errors, "warnings": warnings})
                overall_ok = False
                continue
            except ParseError as e:
                errors.append({"path": path, "loc": "", "msg": str(e.message)})
                all_results.append({"file": path, "errors": errors, "warnings": warnings})
                overall_ok = False
                continue
            except Exception as e:
                errors.append({"path": path, "loc": "", "msg": str(e)})
                all_results.append({"file": path, "errors": errors, "warnings": warnings})
                overall_ok = False
                continue

            # 2. JSON Schema validation
            try:
                d = {k: v for k, v in plan.to_dict().items()
                     if k not in {"source_file", "import_timestamp"}}
                schema_errors = validate_testplan(d)
                for msg in schema_errors:
                    errors.append({"path": path, "loc": "", "msg": msg})
            except ImportError:
                warnings.append({"path": path, "loc": "",
                                  "msg": "jsonschema not installed; schema validation skipped"})

            # 3. Semantic checks
            for tp in _iter_all_testpoints_from_plan(plan):
                if tp.weight is not None and tp.weight <= 0:
                    errors.append({"path": path, "loc": f"testpoint '{tp.name}'",
                                   "msg": f"weight must be >= 1 (got {tp.weight})"})
                for b in tp.coverage:
                    if b.type not in CoverageBinding.TYPES:
                        w = {"path": path, "loc": f"testpoint '{tp.name}' coverage",
                             "msg": f"unknown binding type '{b.type}'"}
                        if strict:
                            errors.append(w)
                        else:
                            warnings.append(w)

            for goal in _iter_all_goals(plan.goals):
                if not goal.id:
                    warnings.append({"path": path, "loc": f"goal '{goal.title}'",
                                      "msg": "goal has no 'id' field"})

            if not plan.name:
                warnings.append({"path": path, "loc": "", "msg": "plan has no 'name' field"})

            all_results.append({"file": path, "errors": errors, "warnings": warnings})
            if errors or (strict and warnings):
                overall_ok = False

        if fmt == "json":
            output = {
                "passed": overall_ok,
                "files": [
                    {
                        "file": r["file"],
                        "errors": [{"loc": e["loc"], "msg": e["msg"]} for e in r["errors"]],
                        "warnings": [{"loc": w["loc"], "msg": w["msg"]} for w in r["warnings"]],
                    }
                    for r in all_results
                ],
            }
            out.write(json.dumps(output, indent=2) + "\n")
        else:
            for r in all_results:
                for e in r["errors"]:
                    loc = f"  {e['loc']}: " if e["loc"] else "  "
                    out.write(f"ERROR   {r['file']}: {loc}{e['msg']}\n")
                for w in r["warnings"]:
                    loc = f"  {w['loc']}: " if w["loc"] else "  "
                    out.write(f"WARNING {r['file']}: {loc}{w['msg']}\n")
                n_e = len(r["errors"])
                n_w = len(r["warnings"])
                if n_e == 0 and n_w == 0:
                    out.write(f"OK      {r['file']}\n")
                else:
                    status = "OK" if n_e == 0 and not (strict and n_w) else "FAIL"
                    out.write(f"{status}    {r['file']}: {n_e} error(s), {n_w} warning(s)\n")

    finally:
        if should_close:
            out.close()

    if not overall_ok:
        sys.exit(1)


def _iter_all_testpoints_from_plan(plan):
    from covsight.core.ncdb.testplan import iter_testpoints
    yield from iter_testpoints(plan)


def _iter_all_goals(goals):
    for g in goals:
        yield g
        yield from _iter_all_goals(g.goals)


# ── stats ─────────────────────────────────────────────────────────────────────

def cmd_testplan_stats(args) -> None:
    """Print aggregate statistics about a testplan."""
    from covsight.core.ncdb.testplan import iter_testpoints

    plan = _load_plan(args)
    fmt = getattr(args, "output_format", "text") or "text"
    out, should_close = _open_output(args)

    try:
        stats = _compute_stats(plan)

        if fmt == "json":
            out.write(json.dumps(stats, indent=2) + "\n")
        else:
            _print_stats_text(stats, out)
    finally:
        if should_close:
            out.close()


def _compute_stats(plan) -> dict:
    from covsight.core.ncdb.testplan import iter_testpoints

    # Goals
    all_goals = list(_iter_all_goals(plan.goals))
    goal_status: dict = {}
    for g in all_goals:
        s = g.status or "unknown"
        goal_status[s] = goal_status.get(s, 0) + 1
    max_depth = _goal_max_depth(plan.goals, 0)

    # Testpoints
    all_tp = list(iter_testpoints(plan))
    by_stage: dict = {}
    na_count = 0
    unimp_count = 0
    with_cov = 0
    with_req = 0
    for tp in all_tp:
        s = tp.stage or "unknown"
        by_stage[s] = by_stage.get(s, 0) + 1
        if tp.na:
            na_count += 1
        if not tp.tests and not tp.na:
            unimp_count += 1
        if tp.coverage:
            with_cov += 1
        if tp.requirements:
            with_req += 1

    # Coverage bindings
    all_bindings = [b for tp in all_tp for b in tp.coverage]
    by_type: dict = {}
    for b in all_bindings:
        by_type[b.type] = by_type.get(b.type, 0) + 1

    # Covergroups
    n_cp_total = sum(len(cg.coverpoints) for cg in plan.covergroups)

    # Imports
    n_imports = len(plan.imports)

    return {
        "plan": {
            "name": plan.name,
            "source_file": plan.source_file,
            "format_version": plan.format_version,
            "imports": n_imports,
        },
        "goals": {
            "total": len(all_goals),
            "by_status": goal_status,
            "max_depth": max_depth,
        },
        "testpoints": {
            "total": len(all_tp),
            "by_stage": by_stage,
            "na": na_count,
            "unimplemented": unimp_count,
            "with_coverage": with_cov,
            "with_requirements": with_req,
        },
        "coverage_bindings": {
            "total": len(all_bindings),
            "by_type": by_type,
        },
        "covergroups": {
            "declared": len(plan.covergroups),
            "coverpoints_listed": n_cp_total,
        },
    }


def _goal_max_depth(goals, current: int) -> int:
    if not goals:
        return current
    return max(_goal_max_depth(g.goals, current + 1) for g in goals)


def _print_stats_text(stats: dict, out) -> None:
    p = stats["plan"]
    g = stats["goals"]
    t = stats["testpoints"]
    cb = stats["coverage_bindings"]
    cg = stats["covergroups"]

    src = f"  ({p['source_file']})" if p["source_file"] else ""
    out.write(f"Testplan: {p['name'] or '(unnamed)'}{src}\n")
    out.write("─" * 60 + "\n")

    out.write("Goals\n")
    out.write(f"  Total:        {g['total']}")
    if g["by_status"]:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(g["by_status"].items()))
        out.write(f"  ({parts})")
    out.write("\n")
    out.write(f"  Max depth:    {g['max_depth']}\n\n")

    out.write("Testpoints\n")
    out.write(f"  Total:        {t['total']}\n")
    if t["by_stage"]:
        parts = "  ".join(f"{k}={v}" for k, v in sorted(t["by_stage"].items()))
        out.write(f"  By stage:     {parts}\n")
    out.write(f"  N/A:          {t['na']}\n")
    out.write(f"  Unimplemented:{t['unimplemented']}\n")
    total = t["total"] or 1
    out.write(f"  With coverage:{t['with_coverage']} / {t['total']} "
              f"({100*t['with_coverage']//total}%)\n")
    out.write(f"  With req.:    {t['with_requirements']} / {t['total']}\n\n")

    out.write("Coverage bindings\n")
    out.write(f"  Total:        {cb['total']}\n")
    if cb["by_type"]:
        parts = "  ".join(f"{k}={v}" for k, v in sorted(cb["by_type"].items()))
        out.write(f"  By type:      {parts}\n")
    out.write("\n")

    out.write("Covergroups declared\n")
    out.write(f"  Groups:       {cg['declared']}\n")
    out.write(f"  Coverpoints:  {cg['coverpoints_listed']}\n")

    if p["imports"]:
        out.write(f"\nImports resolved: {p['imports']}\n")


# ── convert ───────────────────────────────────────────────────────────────────

def cmd_testplan_convert(args) -> None:
    """Convert a testplan between formats (Phase 1: yaml/json/hjson only)."""
    import os

    fmt_in = getattr(args, "input_format", "auto") or "auto"
    fmt_out = getattr(args, "output_format", "text") or "text"
    if fmt_out == "text":
        fmt_out = "yaml"  # convert defaults to yaml output
    no_resolve = getattr(args, "no_resolve_imports", False)

    _SUPPORTED_IN = {"auto", "yaml", "json", "hjson"}
    if fmt_in not in _SUPPORTED_IN:
        print(
            f"Error: --input-format '{fmt_in}' is not yet wired into the CLI.\n"
            f"  Supported: {', '.join(sorted(_SUPPORTED_IN))}.\n"
            f"  Vendor format support is planned for a future release.",
            file=sys.stderr,
        )
        sys.exit(1)

    if fmt_out not in ("yaml", "json"):
        print(
            f"Error: --output-format '{fmt_out}' is not supported for convert.\n"
            f"  Supported: yaml, json.",
            file=sys.stderr,
        )
        sys.exit(1)

    if no_resolve:
        # Re-read the raw dict and build plan without import resolution
        from covsight.core.ncdb.testplan_imports import _parse_file
        import os as _os
        try:
            raw = _parse_file(os.path.abspath(args.testplan))
        except Exception as e:
            print(f"Error loading '{args.testplan}': {e}", file=sys.stderr)
            sys.exit(1)
        # Build plan from raw without resolving imports
        from covsight.core.ncdb.testplan_yaml import _build_plan
        subs = _parse_subs(args)
        if subs:
            raw.setdefault("substitutions", {})
            raw["substitutions"] = {**raw["substitutions"], **subs}
        plan = _build_plan(raw, raw.get("substitutions", {}),
                           os.path.abspath(args.testplan))
    else:
        plan = _load_plan(args)

    out, should_close = _open_output(args)
    try:
        out.write(_serialise(plan.to_dict(), fmt_out) + "\n")
    finally:
        if should_close:
            out.close()


# ── import (existing, extended) ───────────────────────────────────────────────

def cmd_testplan_import(args) -> None:
    from covsight.core.ncdb.ncdb_writer import NcdbWriter
    import os

    plan = _load_plan(args)
    db = _open_ncdb(args.db)
    db.setTestplan(plan)
    tmp = args.db + ".tmp"
    NcdbWriter().write(db, tmp)
    os.replace(tmp, args.db)
    n_tp = sum(1 for _ in _iter_all_testpoints_from_plan(plan))
    print(f"Imported testplan from '{args.testplan}': {n_tp} testpoints, "
          f"{len(plan.covergroups)} covergroups")


# ── export (new) ──────────────────────────────────────────────────────────────

def cmd_testplan_export(args) -> None:
    """Extract a testplan embedded in a .cdb file to YAML or JSON."""
    from covsight.core.ncdb.testplan import get_testplan

    db = _open_ncdb(args.db)
    plan = get_testplan(db)
    if plan is None:
        print(
            "Error: no testplan embedded in this database.\n"
            "  Use 'covsight testplan import' to embed one first.",
            file=sys.stderr,
        )
        sys.exit(1)

    fmt = getattr(args, "output_format", "text") or "text"
    if fmt == "text":
        fmt = "yaml"  # export defaults to yaml output
    out, should_close = _open_output(args)
    try:
        out.write(_serialise(plan.to_dict(), fmt) + "\n")
    finally:
        if should_close:
            out.close()


# ── closure (existing, extended) ─────────────────────────────────────────────

def cmd_testplan_closure(args) -> None:
    from covsight.core.ncdb.testplan import get_testplan, Testplan
    from covsight.core.ncdb.testplan_closure import compute_closure, TPStatus
    from covsight.core.ncdb.reports import (
        report_testpoint_closure, format_testpoint_closure,
        report_stage_gate, format_stage_gate,
    )
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

    # Apply --filter-status
    filter_statuses = set(s.upper() for s in (getattr(args, "filter_status", None) or []))
    if filter_statuses:
        valid = {s.value.upper() for s in TPStatus}
        invalid = filter_statuses - valid
        if invalid:
            print(f"Error: invalid --filter-status value(s): {', '.join(sorted(invalid))}\n"
                  f"  Valid: {', '.join(sorted(valid))}", file=sys.stderr)
            sys.exit(1)
        results = [r for r in results if r.status.value.upper() in filter_statuses]

    out_path = getattr(args, "out", None)
    out = open(out_path, "w") if out_path else sys.stdout
    try:
        summary = report_testpoint_closure(results)
        output_format = getattr(args, "output_format", "text") or "text"

        if output_format == "json":
            out.write(summary.to_json() + "\n")
        else:
            show_goals = getattr(args, "show_goals", False)
            show_coverage = getattr(args, "show_coverage", False)

            if show_goals:
                _render_closure_goals(plan, results, show_coverage, out)
            else:
                out.write(format_testpoint_closure(summary) + "\n")

            if getattr(args, "stage", None):
                gate = report_stage_gate(results, args.stage, plan)
                out.write("\n" + format_stage_gate(gate) + "\n")
    finally:
        if out is not sys.stdout:
            out.close()


def _render_closure_goals(plan, results, show_coverage: bool, out) -> None:
    """Render closure results as an indented goal tree."""
    from covsight.core.ncdb.testplan_closure import TPStatus
    from covsight.core.ncdb.testplan import iter_testpoints

    # Build testpoint-name → result lookup
    by_name = {r.testpoint.name: r for r in results}

    _STATUS_SYM = {
        TPStatus.CLOSED:        "✓",
        TPStatus.PARTIAL:       "~",
        TPStatus.FAILING:       "✗",
        TPStatus.NOT_RUN:       "?",
        TPStatus.NA:            "N/A",
        TPStatus.UNIMPLEMENTED: "-",
    }

    def _tp_result_line(r, indent: str) -> str:
        sym = _STATUS_SYM.get(r.status, "?")
        stage = f"[{r.testpoint.stage}] " if r.testpoint.stage else ""
        tests = ", ".join(r.matched_tests[:3])
        if len(r.matched_tests) > 3:
            tests += f" (+{len(r.matched_tests)-3})"
        line = (f"{indent}{stage}{r.testpoint.name:<30} "
                f"{sym} {r.status.value:<12}  {tests}\n")
        if show_coverage and r.coverage_results:
            for cr in r.coverage_results:
                pct = f"{cr.coverage_pct:.1f}%" if cr.coverage_pct is not None else "n/a"
                line += f"{indent}  ↳ {cr.binding_type:<12} {cr.path_pattern}  {pct}\n"
        return line

    def _goal_closed_total(goal):
        tps = []
        _collect_tps(goal, tps)
        closed = sum(1 for tp in tps
                     if by_name.get(tp.name) and
                     by_name[tp.name].status in (TPStatus.CLOSED, TPStatus.NA))
        return closed, len(tps)

    def _collect_tps(goal, acc):
        acc.extend(goal.testpoints)
        for sg in goal.goals:
            _collect_tps(sg, acc)

    def _render(goal, indent):
        closed, total = _goal_closed_total(goal)
        pct = f"{100*closed//total}%" if total else "—"
        status_str = f"  [{goal.status}]" if goal.status else ""
        out.write(f"{indent}Goal: {goal.title or goal.id}{status_str}"
                  f"  {pct}  ({closed}/{total} closed)\n")
        for tp in goal.testpoints:
            r = by_name.get(tp.name)
            if r:
                out.write(_tp_result_line(r, indent + "  "))
        for sub in goal.goals:
            _render(sub, indent + "  ")

    # Top-level testpoints
    for tp in plan.testpoints:
        r = by_name.get(tp.name)
        if r:
            out.write(_tp_result_line(r, ""))

    for goal in plan.goals:
        _render(goal, "")


# ── export-junit (existing) ───────────────────────────────────────────────────

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


# ── registration ──────────────────────────────────────────────────────────────

def register(subparsers):
    parser = subparsers.add_parser(
        "testplan",
        help="Author, validate, and manage testplans",
    )
    tp = parser.add_subparsers(dest="testplan_cmd")

    # ── show ──────────────────────────────────────────────────────────────────
    show_p = tp.add_parser(
        "show",
        parents=[_P_INPUT, _P_OUTPUT],
        help="Display testplan contents (goals, testpoints, covergroups)",
    )
    show_p.add_argument("testplan", help="Path to the testplan file")
    show_p.add_argument(
        "--section", "-s",
        dest="section",
        action="append",
        choices=["all", "goals", "testpoints", "covergroups"],
        metavar="SECTION",
        help="Section(s) to show: all | goals | testpoints | covergroups  (repeatable)",
    )
    show_p.add_argument("--stage", action="append", metavar="STAGE",
                        help="Filter testpoints by stage (repeatable)")
    show_p.add_argument("--status", action="append", metavar="STATUS",
                        help="Filter goals by status (repeatable)")
    show_p.add_argument("--owner", default=None, metavar="OWNER",
                        help="Filter by owner (substring match)")
    show_p.add_argument("--tag", action="append", metavar="TAG",
                        help="Filter by tag (repeatable)")
    show_p.add_argument("--depth", "-d", type=int, default=None,
                        help="Max goal hierarchy depth to render")
    show_p.add_argument("--show-coverage", action="store_true", default=False,
                        help="Include coverage binding paths")
    show_p.add_argument("--show-requirements", action="store_true", default=False,
                        help="Include requirement links")
    show_p.add_argument("--show-custom", action="store_true", default=False,
                        help="Include custom dicts")
    show_p.set_defaults(func=cmd_testplan_show)

    # ── validate ──────────────────────────────────────────────────────────────
    val_p = tp.add_parser(
        "validate",
        parents=[_P_INPUT, _P_OUTPUT],
        help="Validate testplan file(s) against schema and semantic rules",
    )
    val_p.add_argument("testplans", nargs="+", metavar="testplan",
                       help="One or more testplan files to validate")
    val_p.add_argument("--strict", action="store_true", default=False,
                       help="Treat warnings as errors")
    val_p.set_defaults(func=cmd_testplan_validate)

    # ── stats ─────────────────────────────────────────────────────────────────
    stats_p = tp.add_parser(
        "stats",
        parents=[_P_INPUT, _P_OUTPUT],
        help="Print aggregate statistics about a testplan",
    )
    stats_p.add_argument("testplan", help="Path to the testplan file")
    stats_p.set_defaults(func=cmd_testplan_stats)

    # ── convert ───────────────────────────────────────────────────────────────
    conv_p = tp.add_parser(
        "convert",
        parents=[_P_INPUT, _P_OUTPUT],
        help="Convert between testplan formats (yaml/json/hjson)",
    )
    conv_p.add_argument("testplan", help="Input testplan file")
    conv_p.add_argument(
        "--no-resolve-imports",
        dest="no_resolve_imports",
        action="store_true",
        default=False,
        help="Preserve imports[] array in output; do not flatten",
    )
    conv_p.set_defaults(func=cmd_testplan_convert)

    # ── import (extended) ─────────────────────────────────────────────────────
    imp = tp.add_parser(
        "import",
        parents=[_P_INPUT],
        help="Import a testplan into a .cdb file",
    )
    imp.add_argument("db", help="Path to the NCDB .cdb file")
    imp.add_argument("testplan", help="Path to the testplan file (any supported format)")
    imp.set_defaults(func=cmd_testplan_import)

    # ── export (new) ──────────────────────────────────────────────────────────
    exp = tp.add_parser(
        "export",
        parents=[_P_OUTPUT],
        help="Extract a testplan embedded in a .cdb file",
    )
    exp.add_argument("db", help="Path to the NCDB .cdb file")
    exp.set_defaults(func=cmd_testplan_export)

    # ── closure (extended) ────────────────────────────────────────────────────
    closure = tp.add_parser(
        "closure",
        help="Compute and display testpoint closure",
    )
    closure.add_argument("db", help="Path to the NCDB .cdb file")
    closure.add_argument("--testplan", default=None, metavar="PATH",
                         help="External testplan file")
    closure.add_argument("--waivers", default=None, metavar="PATH",
                         help="External waivers JSON file")
    closure.add_argument("--stage", default=None, metavar="STAGE",
                         help="Evaluate a stage gate")
    closure.add_argument("--out", "-o", default=None, help="Output file")
    closure.add_argument("--output-format", "-of", dest="output_format",
                         default="text", choices=["text", "json"],
                         help="Output format")
    closure.add_argument("--show-goals", action="store_true", default=False,
                         help="Display results as goal-tree with per-goal aggregates")
    closure.add_argument("--filter-status", action="append", metavar="STATUS",
                         help="Only show testpoints with this closure status (repeatable)")
    closure.add_argument("--show-coverage", action="store_true", default=False,
                         help="Include per-binding coverage %% in output")
    closure.set_defaults(func=cmd_testplan_closure)

    # ── export-junit (unchanged) ──────────────────────────────────────────────
    junit = tp.add_parser(
        "export-junit",
        help="Export testpoint closure results as JUnit XML",
    )
    junit.add_argument("db", help="Path to the NCDB .cdb file")
    junit.add_argument("--testplan", default=None, metavar="PATH",
                       help="External testplan JSON file")
    junit.add_argument("--out", "-o", default=None, help="Output XML file")
    junit.add_argument("--suite-name", default=None, metavar="NAME",
                       help="JUnit testsuite name attribute")
    junit.set_defaults(func=cmd_testplan_export_junit)
