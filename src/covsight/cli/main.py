"""covsight CLI entry point."""
import argparse
import sys
import traceback
from importlib.metadata import entry_points


def build_parser():
    parser = argparse.ArgumentParser(prog="covsight", description="Coverage analysis and UCIS database tooling")
    parser.add_argument("--version", "-V", action="store_true", help="Print version and exit")
    subparsers = parser.add_subparsers(dest="command")

    from covsight.cli.cmd_convert import register as reg_convert
    from covsight.cli.cmd_merge import register as reg_merge
    from covsight.cli.cmd_show import register as reg_show
    from covsight.cli.cmd_report import register as reg_report
    from covsight.cli.cmd_history import register as reg_history
    from covsight.cli.cmd_testplan import register as reg_testplan

    reg_convert(subparsers)
    reg_merge(subparsers)
    reg_show(subparsers)
    reg_report(subparsers)
    reg_history(subparsers)
    reg_testplan(subparsers)

    for ep in entry_points(group="covsight.cli"):
        try:
            plugin = ep.load()
            plugin.register(subparsers)
        except Exception:
            pass

    return parser


def main():
    parser = build_parser()
    if len(sys.argv) >= 2 and sys.argv[1] in ("--version", "-V"):
        try:
            from importlib.metadata import version
            print(version("covsight"))
        except Exception:
            print("covsight (unknown version)")
        return

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
