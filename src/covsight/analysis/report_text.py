"""Text report format plugin."""
from covsight.analysis.coverage_report_builder import CoverageReportBuilder
from covsight.analysis.text_formatter import TextCoverageReportFormatter
from covsight.core.api import UCIS
from covsight.core.ext import FormatDescRpt, FormatIfRpt, FormatRptOutFlags


class TextReportPlugin(FormatIfRpt):
    def __init__(self):
        self.details = False
        self.order_bins_by_hit = False
        self.round = 2

    @staticmethod
    def describe() -> FormatDescRpt:
        return FormatDescRpt(
            fmt_if=TextReportPlugin(),
            name="text",
            out_flags=FormatRptOutFlags.Stream,
            description="Produces a human-readable textual coverage report",
        )

    def report(self, db: UCIS, out, args):
        formatter = TextCoverageReportFormatter(CoverageReportBuilder.build(db), out)
        formatter.details = self.details
        formatter.order_bins_by_hit = self.order_bins_by_hit
        formatter.round = self.round
        formatter.report()
