"""Merge command."""
from typing import List

from covsight.cli.format_detection import detect_format
from covsight.core.api import UCIS
from covsight.core.ext import FormatRegistry
from covsight.core.merge import DbMerger


def _default_db_format(registry: FormatRegistry) -> str:
    formats = registry.db_formats()
    if "ncdb" in formats:
        return "ncdb"
    if formats:
        return next(iter(formats.keys()))
    raise ValueError("No database formats are installed")


def merge(args):
    registry = FormatRegistry()
    if args.input_format is None:
        try:
            args.input_format = detect_format(args.db[0], registry)
        except ValueError:
            args.input_format = _default_db_format(registry)
    if args.output_format is None:
        args.output_format = _default_db_format(registry)

    if args.input_format == "ncdb" and args.output_format == "ncdb":
        from covsight.core.ncdb.ncdb_merger import NcdbMerger
        NcdbMerger().merge(args.db, args.out)
        return

    input_desc = registry.get_db_format(args.input_format)
    output_desc = registry.get_db_format(args.output_format)

    db_l: List[UCIS] = []
    try:
        for input_path in args.db:
            db_l.append(input_desc.fmt_if.read(input_path))
        out_db: UCIS = output_desc.fmt_if.create()
        try:
            DbMerger().merge(out_db, db_l)
            output_desc.fmt_if.write(out_db, args.out)
        finally:
            out_db.close()
    finally:
        for db in db_l:
            db.close()


def register(subparsers):
    parser = subparsers.add_parser("merge", help="Merge two or more coverage databases")
    parser.add_argument("--out", "-o", required=True, help="Output database path")
    parser.add_argument("--input-format", "-if", help="Input database format")
    parser.add_argument("--output-format", "-of", help="Output database format")
    parser.add_argument("db", nargs="+", help="Input databases")
    parser.set_defaults(func=merge)
