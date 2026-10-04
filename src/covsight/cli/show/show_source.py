"""
Show Source Command

Source files annotated with their code coverage: each line's hit count,
and under the line the branch arms and expression rows that start on it.
``#`` marks a line, arm or row that was never hit; ``~`` a line that ran
but has an arm or row below it that did not.  Source text is read from
``--source-root`` (or the recorded path); a file that cannot be found is
listed by its measured lines alone.
"""
from typing import Any, Dict, TextIO

from covsight.cli.show_base import ShowBase

LEGEND = ("# never hit   ~ ran, but an arm or row below was not hit")

_MARK = {"missed": "#", "partial": "~"}


class ShowSource(ShowBase):

    def get_data(self) -> Dict[str, Any]:
        from covsight.analysis.code_coverage import CodeCoverage
        from covsight.analysis.source_view import annotate, to_dict

        cc = CodeCoverage(self.db)
        root = getattr(self.args, "source_root", None)
        if root:
            cc.relocate(root)
        files = [to_dict(sf) for sf in
                 annotate(cc, root, getattr(self.args, "file", None) or ())]
        if getattr(self.args, "uncovered", False):
            for f in files:
                f["lines"] = [ln for ln in f["lines"]
                              if ln["status"] in ("missed", "partial")]
                f["uncovered_only"] = True
        data = {"database": self.args.db, "files": files}
        if not files:
            data["note"] = "No line, branch or expression coverage%s." % (
                " in the selected files" if getattr(self.args, "file", None) else "")
        return data

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        fp.write("Source coverage: %s\n" % data["database"])
        if "note" in data:
            fp.write("\n" + data["note"] + "\n")
            return
        fp.write(LEGEND + "\n")
        for f in data["files"]:
            fp.write("\n")
            write_file_text(f, fp)


def _totals(by_kind) -> str:
    return "  ".join("%s %d/%d" % (k, st["covered"], st["total"])
                     for k, st in by_kind.items())


def write_file_text(f: Dict[str, Any], fp: TextIO):
    """One file of ``show source``'s JSON as text."""
    fp.write("%s  %s\n" % (f["file"], _totals(f["by_kind"])))
    if not f["found"]:
        fp.write("(source not found; use --source-root)\n")
    lines = f["lines"]
    if not lines and f.get("uncovered_only"):
        fp.write("(every line, branch arm and expression row was hit)\n")
        return
    counts = [ln["count"] for ln in lines if ln["count"] is not None]
    counts += [r["count"] for ln in lines for a in ln["annotations"] for r in a["rows"]]
    cw = max([len(str(c)) for c in counts] + [1])
    lw = max([len(str(ln["line"])) for ln in lines] + [1])
    pad = " " * (lw + 1)
    prev = None
    for ln in lines:
        if prev is not None and ln["line"] != prev + 1:
            fp.write("%s%s  ...\n" % (pad, " " * (cw + 2)))
        prev = ln["line"]
        count = "" if ln["count"] is None else str(ln["count"])
        fp.write(("%*d %s %*s | %s" % (
            lw, ln["line"], _MARK.get(ln["status"], " "), cw, count,
            ln["text"] if ln["text"] is not None else "")).rstrip() + "\n")
        for a in ln["annotations"]:
            fp.write("%s  %s | %s %s\n" % (pad, " " * cw, a["kind"], a["scope"]))
            for r in a["rows"]:
                fp.write("%s%s %*d |   %s\n" % (
                    pad, " " if r["covered"] else "#", cw, r["count"], r["name"]))
