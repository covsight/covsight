"""LCOV tracefile (``.info``) output for line and branch coverage.

Consumed by genhtml, Codecov, Coveralls, SonarQube and most CI coverage
plugins.  Only line (``DA``) and branch (``BRDA``) records are written; LCOV
has no notion of toggle, expression or FSM coverage.
"""
import re
from typing import Optional, TextIO

from .code_coverage import CodeCoverage

_TN_UNSAFE = re.compile(r"[^A-Za-z0-9_]")


def write_lcov(cc: CodeCoverage, fp: TextIO, test_name: Optional[str] = None):
    """Write ``cc`` as an LCOV tracefile.  Files without a recorded source
    location cannot be represented and are omitted."""
    lines = cc.line_hits()
    branches = cc.branches()
    # TN may only contain word characters.
    fp.write("TN:%s\n" % _TN_UNSAFE.sub("_", test_name or ""))
    for fname in sorted(set(lines) | set(branches)):
        fp.write("SF:%s\n" % fname)
        brs = branches.get(fname, [])
        for line, block, branch, hits in brs:
            fp.write("BRDA:%d,%d,%d,%d\n" % (line, block, branch, hits))
        if brs:
            fp.write("BRF:%d\n" % len(brs))
            fp.write("BRH:%d\n" % sum(1 for b in brs if b[3] > 0))
        da = lines.get(fname, {})
        for line in sorted(da):
            fp.write("DA:%d,%d\n" % (line, da[line]))
        fp.write("LF:%d\n" % len(da))
        fp.write("LH:%d\n" % sum(1 for n in da.values() if n > 0))
        fp.write("end_of_record\n")
