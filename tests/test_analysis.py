import os

from covsight.analysis import CoverageReport, CoverageReportBuilder
from covsight.core.api import FlagsT, HistoryNodeKind, ScopeTypeT, SourceInfo, SourceT, TestStatusT as StatusEnum
from covsight.core.api.test_data import TestData as TestMetadata
from covsight.core.mem import MemFactory

StatusEnum.__test__ = False
TestMetadata.__test__ = False


def _build_db():
    db = MemFactory.create()
    node = db.createHistoryNode(None, "logicalName", "file.ucis", HistoryNodeKind.TEST)
    node.setTestData(TestMetadata(teststatus=StatusEnum.OK, toolcategory="covsight:test", date="20200202020"))

    file_h = db.createFileHandle("dummy", os.getcwd())
    srcinfo = SourceInfo(file_h, 0, 0)
    du = db.createScope("foo.bar", srcinfo, 1, SourceT.SV, ScopeTypeT.DU_MODULE, FlagsT.INST_ONCE | FlagsT.SCOPE_UNDER_DU)
    instance = db.createInstance("dummy", None, 1, SourceT.SV, ScopeTypeT.INSTANCE, du, FlagsT.INST_ONCE)
    cg = instance.createCovergroup("cg", SourceInfo(file_h, 3, 0), 1, SourceT.SV)
    cp = cg.createCoverpoint("t", SourceInfo(file_h, 4, 0), 1, SourceT.SV)
    cp.createBin("auto[a]", SourceInfo(file_h, 4, 0), 1, 4, "a")
    return db


def test_coverage_report_builder_smoke():
    report = CoverageReportBuilder.build(_build_db())
    assert isinstance(report, CoverageReport)
    assert len(report.covergroups) == 1
    assert report.covergroups[0].name == "cg"
    assert len(report.covergroups[0].coverpoints) == 1
    assert report.covergroups[0].coverpoints[0].coverage == 100
