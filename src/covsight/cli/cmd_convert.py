"""Convert command."""
from covsight.cli.format_detection import detect_format
from covsight.core.conversion import ConversionContext, ConversionListener
from covsight.core.ext import FormatRegistry


def _default_db_format(registry: FormatRegistry) -> str:
    formats = registry.db_formats()
    if "ncdb" in formats:
        return "ncdb"
    if formats:
        return next(iter(formats.keys()))
    raise ValueError("No database formats are installed")


def convert(args):
    registry = FormatRegistry()
    if args.input_format is None:
        args.input_format = detect_format(args.input, registry)
    if args.output_format is None:
        args.output_format = _default_db_format(registry)

    input_desc = registry.get_db_format(args.input_format)
    output_desc = registry.get_db_format(args.output_format)
    input_if = input_desc.fmt_if
    output_if = output_desc.fmt_if

    ctx = ConversionContext(strict=getattr(args, "strict", False), listener=ConversionListener())
    in_db = input_if.read(args.input)
    try:
        _apply_test_info(in_db, args)
        try:
            output_if.write(in_db, args.out, ctx)
        except TypeError:
            output_if.write(in_db, args.out)
        ctx.complete()
        if getattr(args, "warn_summary", False) and ctx.warnings:
            import sys
            print(ctx.summarize(), file=sys.stderr)
    finally:
        in_db.close()


def _apply_test_info(db, args):
    info = dict(name=getattr(args, "test_name", None),
                seed=getattr(args, "seed", None),
                status=getattr(args, "status", None))
    if any(v is not None for v in info.values()):
        from covsight.core.conversion import apply_test_info
        apply_test_info(db, **info)


def register(subparsers):
    parser = subparsers.add_parser("convert", help="Convert coverage data between formats")
    parser.add_argument("--out", "-o", required=True, help="Output database path")
    parser.add_argument("--input-format", "-if", help="Input database format")
    parser.add_argument("--output-format", "-of", help="Output database format")
    parser.add_argument("--strict", action="store_true", default=False, help="Treat lossy conversion as an error")
    parser.add_argument("--warn-summary", action="store_true", default=False, help="Print a warning summary at the end")
    parser.add_argument("--test-name", help="Name of the test that produced the input")
    parser.add_argument("--seed", help="Seed of the test that produced the input")
    parser.add_argument("--status", help="Test outcome: pass/ok, fail/error, warning, fatal")
    parser.add_argument("input", help="Source database to convert")
    parser.set_defaults(func=convert)
