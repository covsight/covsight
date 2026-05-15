"""Report command."""
import os
import shutil
import sys

from covsight.cli.format_detection import detect_format
from covsight.core.ext import FormatRegistry, FormatRptOutFlags


def _default_db_format(registry: FormatRegistry) -> str:
    formats = registry.db_formats()
    if "ncdb" in formats:
        return "ncdb"
    if formats:
        return next(iter(formats.keys()))
    raise ValueError("No database formats are installed")


def report(args):
    registry = FormatRegistry()
    if args.input_format is None:
        try:
            args.input_format = detect_format(args.db, registry)
        except ValueError:
            args.input_format = _default_db_format(registry)
    if args.output_format is None:
        args.output_format = "text"

    input_desc = registry.get_db_format(args.input_format)
    output_desc = registry.get_rpt_format(args.output_format)
    in_db = input_desc.fmt_if.read(args.db)

    fp = None
    try:
        if args.out is None:
            if (output_desc.out_flags & FormatRptOutFlags.Stream) == 0:
                raise Exception(f"Output format {args.output_format} requires an explicit destination")
            fp = sys.stdout
        elif (output_desc.out_flags & FormatRptOutFlags.Stream) != 0:
            fp = open(args.out, "w")
        elif (output_desc.out_flags & FormatRptOutFlags.Dir) != 0:
            if os.path.exists(args.out):
                if not os.path.isdir(args.out):
                    raise Exception(f"Output format {args.output_format} requires a directory destination")
                shutil.rmtree(args.out)
            os.makedirs(args.out)
            fp = args.out
        else:
            raise Exception(f"Unsupported output flags for {args.output_format}: {output_desc.out_flags}")

        output_desc.fmt_if.report(in_db, fp, args)
    finally:
        if fp not in (None, sys.stdout) and hasattr(fp, "close"):
            fp.close()
        in_db.close()


def register(subparsers):
    parser = subparsers.add_parser("report", help="Generate a coverage report")
    parser.add_argument("--out", "-o", help="Output report path")
    parser.add_argument("--input-format", "-if", help="Input database format")
    parser.add_argument("--output-format", "-of", choices=["text", "json"], help="Report output format")
    parser.add_argument("db", help="Coverage database path")
    parser.set_defaults(func=report)
