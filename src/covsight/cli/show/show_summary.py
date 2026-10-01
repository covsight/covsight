"""
Show Summary Command

Displays high-level coverage summary including overall coverage
percentages, statistics by coverage type, and test information.
"""
from typing import Any, Dict
from covsight.cli.show_base import ShowBase


class ShowSummary(ShowBase):
    """
    Display overall coverage summary.
    
    Provides:
    - Overall coverage percentage: functional coverage when the database
      has covergroups (``overall_basis: functional``), else code coverage
    - Coverage by type (functional, code, assertion)
    - Test statistics
    - Coverage scope counts
    """
    
    def get_data(self) -> Dict[str, Any]:
        """
        Extract summary data from the database.
        
        Returns:
            Dictionary containing summary information
        """
        from covsight.analysis.coverage_report_builder import CoverageReportBuilder
        
        from covsight.analysis.code_coverage import CodeCoverage

        # Build coverage report
        report = CoverageReportBuilder.build(self.db)
        code = CodeCoverage(self.db)

        if report.covergroups or not code.items:
            overall, basis = report.coverage, "functional"
        else:
            overall, basis = round(code.overall().coverage_pct, 2), "code"

        # Collect overall statistics
        summary = {
            "database": self.args.db,
            "overall_coverage": overall,
            "overall_basis": basis,
            "coverage_by_type": self._get_coverage_by_type(report, code),
            "statistics": self._get_statistics(report),
            "tests": self._get_test_info(),
        }
        
        return summary
    
    def _get_coverage_by_type(self, report, code) -> Dict[str, Any]:
        """Extract coverage percentages by type."""
        coverage_by_type = {}
        
        # Functional coverage (covergroups)
        if report.covergroups:
            total_weight = 0
            weighted_coverage = 0.0
            for cg in report.covergroups:
                weight = getattr(cg, 'weight', 1)
                total_weight += weight
                weighted_coverage += cg.coverage * weight
            
            coverage_by_type['functional'] = {
                'coverage': weighted_coverage / total_weight if total_weight > 0 else 0.0,
                'covergroups': len(report.covergroups)
            }
        else:
            coverage_by_type['functional'] = {
                'coverage': 0.0,
                'covergroups': 0
            }
        
        from covsight.analysis.code_coverage import (
            DIRECTIVE_KINDS, kinds_dict, stats_dict,
        )
        kinds = code.kinds_present()
        if kinds:
            coverage_by_type['code'] = dict(
                stats_dict(code.overall(kinds)),
                by_kind=kinds_dict(code.by_kind(kinds)))
        directives = code.by_kind(DIRECTIVE_KINDS)
        if directives['cover'].total:
            coverage_by_type['cover_directives'] = stats_dict(directives['cover'])

        return coverage_by_type
    
    def _get_statistics(self, report) -> Dict[str, Any]:
        """Get coverage statistics."""
        stats = {
            'total_covergroups': len(report.covergroups) if report.covergroups else 0,
        }
        
        # Count coverpoints and bins
        total_coverpoints = 0
        total_bins = 0
        covered_bins = 0
        
        if report.covergroups:
            for cg in report.covergroups:
                if hasattr(cg, 'coverpoints') and cg.coverpoints:
                    total_coverpoints += len(cg.coverpoints)
                    for cp in cg.coverpoints:
                        if hasattr(cp, 'bins') and cp.bins:
                            total_bins += len(cp.bins)
                            covered_bins += sum(1 for bin in cp.bins if bin.count > 0)
        
        stats['total_coverpoints'] = total_coverpoints
        stats['total_bins'] = total_bins
        stats['covered_bins'] = covered_bins
        
        return stats
    
    def _get_test_info(self) -> Dict[str, Any]:
        """Get test execution information."""
        from covsight.core.api import HistoryNodeKind, TestStatusT

        tests = []

        # Use individual getters — getTestData() only exists in the C-library
        # wrapper; MemHistoryNode and SqliteHistoryNode use per-field accessors.
        try:
            for node in self.db.historyNodes(HistoryNodeKind.TEST):
                entry = {'name': node.getLogicalName()}
                if hasattr(node, 'getTestStatus'):
                    entry['status'] = node.getTestStatus()
                if hasattr(node, 'getDate'):
                    d = node.getDate()
                    if d is not None:
                        entry['date'] = str(d)
                tests.append(entry)
        except Exception:
            pass

        return {
            'total_tests': len(tests),
            'tests': tests
        }
