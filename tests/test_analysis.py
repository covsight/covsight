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


def test_cross_bins_use_at_least():
    """A cross bin is hit when its count reaches at_least, as a coverpoint
    bin is; its goal (often 0) is not the threshold."""
    from covsight.core.api import CoverTypeT
    db = _build_db()
    (inst,) = db.scopes(ScopeTypeT.INSTANCE)
    (cg,) = inst.scopes(ScopeTypeT.COVERGROUP)
    (cp,) = cg.scopes(ScopeTypeT.COVERPOINT)
    cr = cg.createCross("t_x_t", None, 1, SourceT.SV, [cp, cp])
    cr.createBin("<a,a>", None, 1, 3, "a,a", CoverTypeT.CVGBIN)
    cr.createBin("<b,b>", None, 1, 0, "b,b", CoverTypeT.CVGBIN)
    for ci in cr.coverItems(CoverTypeT.CVGBIN):
        ci.getCoverData().goal = 0
    (cr_r,) = CoverageReportBuilder.build(db).covergroups[0].crosses
    assert [b.hit for b in cr_r.bins] == [True, False]
