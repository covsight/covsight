"""
Show Assertions Command

Cover directives (``cover property``) and assertions.

* A cover directive is *covered* when its cover count reaches its goal.
* An assertion is *failed* if it has any failure count, *passed* if it has a
  pass count, and *not exercised* otherwise.  Vacuous, attempt and other
  counts are reported as recorded.
"""
from collections import OrderedDict
from typing import Any, Dict, TextIO

from covsight.cli.show_base import ShowBase

# CoverTypeT name -> key in the per-assertion "counts" dict
_COUNT_KEYS = OrderedDict([
    ("COVERBIN", "cover"), ("ASSERTBIN", "fail"), ("FAILBIN", "fail"),
    ("PASSBIN", "pass"), ("VACUOUSBIN", "vacuous"), ("DISABLEDBIN", "disabled"),
    ("ATTEMPTBIN", "attempt"), ("ACTIVEBIN", "active"),
    ("PEAKACTIVEBIN", "peak_active"),
])


class ShowAssertions(ShowBase):

    def get_data(self) -> Dict[str, Any]:
        from covsight.analysis.code_coverage import walk_scopes
        from covsight.core.api import CoverTypeT, ScopeTypeT

        rows = []
        tally = {"cover": [0, 0], "assert": [0, 0, 0]}  # covered,total / pass,fail,none
        for inst, scope in walk_scopes(self.db):
            st = scope.getScopeType()
            if st not in (ScopeTypeT.COVER, ScopeTypeT.ASSERT):
                continue
            counts: Dict[str, int] = OrderedDict()
            covered = False
            for ci in scope.coverItems(CoverTypeT.ALL):
                cd = ci.getCoverData()
                try:
                    tname = CoverTypeT(cd.type).name
                except ValueError:
                    tname = str(cd.type)
                key = _COUNT_KEYS.get(tname, tname.lower())
                counts[key] = counts.get(key, 0) + int(cd.data or 0)
                if tname == "COVERBIN" and cd.data >= max(cd.at_least or 0, 1):
                    covered = True

            name = scope.getScopeName()
            row = OrderedDict(name="%s.%s" % (inst, name) if inst else name,
                              kind="cover" if st == ScopeTypeT.COVER else "assert")
            if row["kind"] == "cover":
                row["status"] = "covered" if covered else "uncovered"
                tally["cover"][0] += covered
                tally["cover"][1] += 1
            else:
                if counts.get("fail", 0) > 0:
                    row["status"] = "failed"
                    tally["assert"][1] += 1
                elif counts.get("pass", 0) > 0 or counts.get("cover", 0) > 0:
                    row["status"] = "passed"
                    tally["assert"][0] += 1
                else:
                    row["status"] = "not_exercised"
                    tally["assert"][2] += 1
            row["counts"] = counts
            si = scope.getSourceInfo()
            if si is not None and si.file is not None:
                row["file"] = si.file.getFileName()
                row["line"] = si.line
            rows.append(row)

        n_cov, n_cov_total = tally["cover"]
        n_pass, n_fail, n_none = tally["assert"]
        return {
            "database": self.args.db,
            "summary": {
                "cover": {
                    "total": n_cov_total, "covered": n_cov,
                    "coverage": round(100.0 * n_cov / n_cov_total, 2) if n_cov_total else 0.0,
                },
                "assert": {
                    "total": n_pass + n_fail + n_none, "passed": n_pass,
                    "failed": n_fail, "not_exercised": n_none,
                },
            },
            "assertions": rows,
        }

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        s = data["summary"]
        fp.write("Assertions: %s\n\n" % data["database"])
        if not data["assertions"]:
            fp.write("No cover directives or assertions in this database.\n")
            return
        c, a = s["cover"], s["assert"]
        if c["total"]:
            fp.write("Cover directives: %.2f%% (%d/%d)\n" % (c["coverage"], c["covered"], c["total"]))
        if a["total"]:
            fp.write("Assertions: %d (passed %d, failed %d, not exercised %d)\n" % (
                a["total"], a["passed"], a["failed"], a["not_exercised"]))
        fp.write("\n")
        width = max(len(r["name"]) for r in data["assertions"])
        for r in data["assertions"]:
            counts = " ".join("%s=%d" % kv for kv in r["counts"].items())
            loc = " (%s:%d)" % (r["file"], r["line"]) if "file" in r else ""
            fp.write("%-*s  %-6s  %-13s  %s%s\n" % (
                width, r["name"], r["kind"], r["status"], counts, loc))
