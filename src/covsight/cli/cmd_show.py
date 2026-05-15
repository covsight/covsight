"""Show command registration and dispatch."""
from importlib import import_module


_SHOW_IMPLS = {
    "summary": ("covsight.cli.show.show_summary", "ShowSummary"),
    "gaps": ("covsight.cli.show.show_gaps", "ShowGaps"),
    "covergroups": ("covsight.cli.show.show_covergroups", "ShowCovergroups"),
    "bins": ("covsight.cli.show.show_bins", "ShowBins"),
    "tests": ("covsight.cli.show.show_tests", "ShowTests"),
    "hierarchy": ("covsight.cli.show.show_hierarchy", "ShowHierarchy"),
    "metrics": ("covsight.cli.show.show_metrics", "ShowMetrics"),
    "compare": ("covsight.cli.show.show_compare", "ShowCompare"),
    "hotspots": ("covsight.cli.show.show_hotspots", "ShowHotspots"),
    "code-coverage": ("covsight.cli.show.show_code_coverage", "ShowCodeCoverage"),
    "assertions": ("covsight.cli.show.show_assertions", "ShowAssertions"),
    "toggle": ("covsight.cli.show.show_toggle", "ShowToggle"),
}


def show(args):
    module_name, class_name = _SHOW_IMPLS[args.show_cmd]
    cls = getattr(import_module(module_name), class_name)
    cls(args).execute()


def register(subparsers):
    parser = subparsers.add_parser("show", help="Query and display coverage information")
    show_sub = parser.add_subparsers(dest="show_cmd")

    summary = show_sub.add_parser("summary", help="Display overall coverage summary")
    summary.add_argument("--out", "-o", help="Output location")
    summary.add_argument("--input-format", "-if", help="Input database format")
    summary.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    summary.add_argument("db", help="Path to the coverage database")

    gaps = show_sub.add_parser("gaps", help="Display coverage gaps")
    gaps.add_argument("--out", "-o", help="Output location")
    gaps.add_argument("--input-format", "-if", help="Input database format")
    gaps.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    gaps.add_argument("--threshold", "-t", type=float, default=None, help="Only show coverpoints below this threshold")
    gaps.add_argument("db", help="Path to the coverage database")

    covergroups = show_sub.add_parser("covergroups", help="Display detailed covergroup information")
    covergroups.add_argument("--out", "-o", help="Output location")
    covergroups.add_argument("--input-format", "-if", help="Input database format")
    covergroups.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    covergroups.add_argument("--include-bins", "-b", action="store_true", default=False, help="Include detailed bin information")
    covergroups.add_argument("db", help="Path to the coverage database")

    bins = show_sub.add_parser("bins", help="Display bin-level coverage details")
    bins.add_argument("--out", "-o", help="Output location")
    bins.add_argument("--input-format", "-if", help="Input database format")
    bins.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    bins.add_argument("--covergroup", "-cg", help="Filter by covergroup name")
    bins.add_argument("--coverpoint", "-cp", help="Filter by coverpoint name")
    bins.add_argument("--min-hits", type=int, default=None, help="Minimum hit count")
    bins.add_argument("--max-hits", type=int, default=None, help="Maximum hit count")
    bins.add_argument("--sort", "-s", choices=["count", "name"], default=None, help="Sort bins")
    bins.add_argument("db", help="Path to the coverage database")

    tests = show_sub.add_parser("tests", help="Display test execution information")
    tests.add_argument("--out", "-o", help="Output location")
    tests.add_argument("--input-format", "-if", help="Input database format")
    tests.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    tests.add_argument("db", help="Path to the coverage database")

    hierarchy = show_sub.add_parser("hierarchy", help="Display design hierarchy structure")
    hierarchy.add_argument("--out", "-o", help="Output location")
    hierarchy.add_argument("--input-format", "-if", help="Input database format")
    hierarchy.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    hierarchy.add_argument("--max-depth", "-d", type=int, default=None, help="Maximum depth to traverse")
    hierarchy.add_argument("db", help="Path to the coverage database")

    metrics = show_sub.add_parser("metrics", help="Display coverage metrics and statistics")
    metrics.add_argument("--out", "-o", help="Output location")
    metrics.add_argument("--input-format", "-if", help="Input database format")
    metrics.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    metrics.add_argument("db", help="Path to the coverage database")

    compare = show_sub.add_parser("compare", help="Compare coverage between two databases")
    compare.add_argument("--out", "-o", help="Output location")
    compare.add_argument("--input-format", "-if", help="Input database format")
    compare.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    compare.add_argument("db", help="Path to the baseline coverage database")
    compare.add_argument("compare_db", help="Path to the comparison database")

    hotspots = show_sub.add_parser("hotspots", help="Identify coverage hotspots")
    hotspots.add_argument("--out", "-o", help="Output location")
    hotspots.add_argument("--input-format", "-if", help="Input database format")
    hotspots.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    hotspots.add_argument("--threshold", "-t", type=float, default=80.0, help="Coverage threshold")
    hotspots.add_argument("--limit", "-l", type=int, default=10, help="Maximum items to show")
    hotspots.add_argument("db", help="Path to the coverage database")

    code_cov = show_sub.add_parser("code-coverage", help="Display code coverage information")
    code_cov.add_argument("--out", "-o", help="Output location")
    code_cov.add_argument("--input-format", "-if", help="Input database format")
    code_cov.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt", "lcov", "cobertura", "jacoco", "clover"])
    code_cov.add_argument("db", help="Path to the coverage database")

    assertions = show_sub.add_parser("assertions", help="Display assertion coverage information")
    assertions.add_argument("--out", "-o", help="Output location")
    assertions.add_argument("--input-format", "-if", help="Input database format")
    assertions.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    assertions.add_argument("db", help="Path to the coverage database")

    toggle = show_sub.add_parser("toggle", help="Display toggle coverage information")
    toggle.add_argument("--out", "-o", help="Output location")
    toggle.add_argument("--input-format", "-if", help="Input database format")
    toggle.add_argument("--output-format", "-of", default="json", choices=["json", "text", "txt"])
    toggle.add_argument("db", help="Path to the coverage database")

    parser.set_defaults(func=show)
