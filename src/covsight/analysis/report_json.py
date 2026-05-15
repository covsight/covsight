"""JSON report format plugin."""
import json

from covsight.analysis.coverage_report import CoverageReport
from covsight.analysis.coverage_report_builder import CoverageReportBuilder
from covsight.core.api import UCIS
from covsight.core.ext import FormatDescRpt, FormatIfRpt, FormatRptOutFlags


def _bin_to_dict(bin_obj: CoverageReport.CoverBin) -> dict:
    return {
        "name": bin_obj.name,
        "goal": bin_obj.goal,
        "count": bin_obj.count,
        "hit": bin_obj.hit,
    }


def _coverpoint_to_dict(cp: CoverageReport.Coverpoint) -> dict:
    data = {
        "name": cp.name,
        "coverage": cp.coverage,
        "weight": cp.weight,
    }
    if cp.bins:
        data["bins"] = [_bin_to_dict(b) for b in cp.bins]
    if cp.ignore_bins:
        data["ignorebins"] = [_bin_to_dict(b) for b in cp.ignore_bins]
    if cp.illegal_bins:
        data["illegalbins"] = [_bin_to_dict(b) for b in cp.illegal_bins]
    return data


def _cross_to_dict(cr: CoverageReport.Cross) -> dict:
    data = {
        "name": cr.name,
        "coverage": cr.coverage,
        "weight": cr.weight,
    }
    if cr.bins:
        data["bins"] = [_bin_to_dict(b) for b in cr.bins]
    return data


def _covergroup_to_dict(cg: CoverageReport.Covergroup) -> dict:
    data = {
        "name": cg.name,
        "instname": cg.instname,
        "coverage": cg.coverage,
        "weight": cg.weight,
    }
    if cg.coverpoints:
        data["coverpoints"] = [_coverpoint_to_dict(cp) for cp in cg.coverpoints]
    if cg.crosses:
        data["crosses"] = [_cross_to_dict(cr) for cr in cg.crosses]
    if cg.covergroups:
        data["covergroups"] = [_covergroup_to_dict(sub) for sub in cg.covergroups]
    return data


class JsonReportPlugin(FormatIfRpt):
    def __init__(self):
        self.details = True

    @staticmethod
    def describe() -> FormatDescRpt:
        return FormatDescRpt(
            fmt_if=JsonReportPlugin(),
            name="json",
            out_flags=FormatRptOutFlags.Stream,
            description="Produces a machine-readable JSON coverage report",
        )

    def report(self, db: UCIS, out, args):
        report = CoverageReportBuilder.build(db)
        payload = {
            "coverage": report.coverage,
            "covergroups": [_covergroup_to_dict(cg) for cg in report.covergroups],
        }
        json.dump(payload, out, indent=4)
        out.write("\n")
