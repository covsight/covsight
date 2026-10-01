"""Cobertura XML output for line and branch coverage.

Read by GitHub Actions coverage reporters (e.g. irongut/CodeCoverageSummary,
5monkeys/cobertura-action), GitLab's coverage visualization, the Jenkins
Cobertura plugin, Azure DevOps and SonarQube.

Mapping (coverage-04.dtd):

* one ``<package>`` per source directory, one ``<class>`` per source file;
* one ``<line>`` per executable line (see ``CodeCoverage.line_hits``);
* a line holding branch arms has ``branch="true"`` and
  ``condition-coverage="<pct>% (<covered>/<arms>)"``.
"""
import os
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict
from typing import Dict, List, Optional, TextIO, Tuple

from .code_coverage import CodeCoverage

DOCTYPE = ('<!DOCTYPE coverage SYSTEM '
           '"http://cobertura.sourceforge.net/xml/coverage-04.dtd">')


def _rate(covered: int, valid: int) -> str:
    # Cobertura reports an empty set as fully covered.
    return "%.4g" % (covered / valid if valid else 1.0)


class _Counts:
    def __init__(self):
        self.lines_valid = self.lines_covered = 0
        self.branches_valid = self.branches_covered = 0

    def add(self, other: "_Counts"):
        self.lines_valid += other.lines_valid
        self.lines_covered += other.lines_covered
        self.branches_valid += other.branches_valid
        self.branches_covered += other.branches_covered

    def rates(self, elem):
        elem.set("line-rate", _rate(self.lines_covered, self.lines_valid))
        elem.set("branch-rate", _rate(self.branches_covered, self.branches_valid))


def file_records(cc: CodeCoverage
                 ) -> "OrderedDict[str, List[Tuple[int, int, Optional[Tuple[int, int]]]]]":
    """``{file: [(line, hits, (arms covered, arms) or None), ...]}``, sorted."""
    lines = cc.line_hits()
    arms: Dict[str, Dict[int, List[int]]] = {}
    for fname, recs in cc.branches().items():
        for line, _block, _branch, hits in recs:
            ent = arms.setdefault(fname, {}).setdefault(line, [0, 0])
            ent[0] += hits > 0
            ent[1] += 1
    ret = OrderedDict()
    for fname in sorted(set(lines) | set(arms)):
        da = lines.get(fname, {})
        br = arms.get(fname, {})
        ret[fname] = [(ln, da.get(ln, 0), tuple(br[ln]) if ln in br else None)
                      for ln in sorted(set(da) | set(br))]
    return ret


def write_cobertura(cc: CodeCoverage, fp: TextIO, sources: List[str] = None,
                    timestamp: Optional[int] = None, version: str = ""):
    """Write ``cc`` as Cobertura XML.  ``sources`` lists the roots that file
    names are relative to (default ``.``)."""
    root = ET.Element("coverage")
    total = _Counts()
    src_elem = ET.SubElement(root, "sources")
    for s in sources or ["."]:
        ET.SubElement(src_elem, "source").text = s
    packages = ET.SubElement(root, "packages")

    by_dir: "OrderedDict[str, list]" = OrderedDict()
    for fname, recs in file_records(cc).items():
        by_dir.setdefault(os.path.dirname(fname), []).append((fname, recs))

    for dname in sorted(by_dir):
        pkg = ET.SubElement(packages, "package",
                            name=dname.replace("/", ".").strip(".") or ".")
        pkg_counts = _Counts()
        classes = ET.SubElement(pkg, "classes")
        for fname, recs in by_dir[dname]:
            cls = ET.SubElement(classes, "class", name=os.path.basename(fname),
                                filename=fname)
            ET.SubElement(cls, "methods")
            lines_elem = ET.SubElement(cls, "lines")
            counts = _Counts()
            for line, hits, br in recs:
                le = ET.SubElement(lines_elem, "line", number=str(line),
                                   hits=str(hits))
                counts.lines_valid += 1
                counts.lines_covered += hits > 0
                if br is None:
                    le.set("branch", "false")
                    continue
                covered, n = br
                le.set("branch", "true")
                le.set("condition-coverage", "%d%% (%d/%d)" % (
                    round(100.0 * covered / n), covered, n))
                counts.branches_valid += n
                counts.branches_covered += covered
            counts.rates(cls)
            cls.set("complexity", "0")
            pkg_counts.add(counts)
        pkg_counts.rates(pkg)
        pkg.set("complexity", "0")
        total.add(pkg_counts)

    total.rates(root)
    root.set("lines-covered", str(total.lines_covered))
    root.set("lines-valid", str(total.lines_valid))
    root.set("branches-covered", str(total.branches_covered))
    root.set("branches-valid", str(total.branches_valid))
    root.set("complexity", "0")
    root.set("version", version or "covsight")
    root.set("timestamp", str(int(time.time() * 1000) if timestamp is None else timestamp))

    ET.indent(root)
    fp.write('<?xml version="1.0" ?>\n%s\n' % DOCTYPE)
    fp.write(ET.tostring(root, encoding="unicode"))
    fp.write("\n")
