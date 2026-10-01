"""
Show Code Coverage Command

Line, branch, expression, condition, toggle and FSM coverage: totals per
kind, then per instance and per source file.  ``-of lcov`` and
``-of cobertura`` write an LCOV tracefile or Cobertura XML (line and branch
coverage) for CI tools; ``--source-root`` makes their paths repo-relative.
"""
from typing import Any, Dict, TextIO

from covsight.cli.show_base import ShowBase


class ShowCodeCoverage(ShowBase):

    def _coverage(self):
        from covsight.analysis.code_coverage import CodeCoverage
        if getattr(self, "_cc", None) is None:
            self._cc = CodeCoverage(self.db)
            if getattr(self.args, "source_root", None):
                self._cc.relocate(self.args.source_root)
        return self._cc

    def get_data(self) -> Dict[str, Any]:
        from covsight.analysis.code_coverage import kinds_dict, stats_dict

        cc = self._coverage()
        kinds = cc.kinds_present()
        data = {
            "database": self.args.db,
            "overall": stats_dict(cc.overall(kinds)),
            "by_kind": kinds_dict(cc.by_kind(kinds)),
            "instances": [
                {"instance": inst or "(root)", "by_kind": kinds_dict(stats)}
                for inst, stats in cc.by_instance(kinds).items()],
            "files": [
                {"file": fname or "(unknown)", "by_kind": kinds_dict(stats)}
                for fname, stats in cc.by_file(kinds).items()],
        }
        if not kinds:
            data["note"] = "No code coverage in this database."
        return data

    def _write_output(self, data: Dict[str, Any]):
        fmt = getattr(self.args, "output_format", "json")
        if fmt not in ("lcov", "cobertura"):
            return super()._write_output(data)
        out = getattr(self.args, "out", None)
        if out is None:
            import sys
            self._export(fmt, sys.stdout)
        else:
            with open(out, "w") as fp:
                self._export(fmt, fp)

    def _export(self, fmt, fp):
        if fmt == "lcov":
            from covsight.analysis.lcov import write_lcov
            write_lcov(self._coverage(), fp, self._test_name())
        else:
            import os
            from covsight.analysis.cobertura import write_cobertura
            root = getattr(self.args, "source_root", None)
            write_cobertura(self._coverage(), fp,
                            sources=[os.path.abspath(root)] if root else None,
                            version=_version())

    def _test_name(self):
        from covsight.core.api import HistoryNodeKind
        try:
            names = [n.getLogicalName() for n in self.db.historyNodes(HistoryNodeKind.TEST)]
        except Exception:
            names = []
        return names[0] if len(names) == 1 else None

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        from covsight.cli.show.text_table import matrix_table, stats_table
        fp.write("Code coverage: %s\n\n" % data["database"])
        if "note" in data:
            fp.write(data["note"] + "\n")
            return
        rows = list(data["by_kind"].items()) + [("overall", data["overall"])]
        stats_table(fp, "Kind", rows)
        kinds = list(data["by_kind"])
        fp.write("\n")
        matrix_table(fp, "Instance", kinds,
                     [(i["instance"], i["by_kind"]) for i in data["instances"]])
        fp.write("\n")
        matrix_table(fp, "File", kinds,
                     [(f["file"], f["by_kind"]) for f in data["files"]])


def _version() -> str:
    try:
        from importlib.metadata import version
        return "covsight " + version("covsight")
    except Exception:
        return "covsight"
