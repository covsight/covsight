"""Directives that put an example's generated output on its docs page.

``dfm run docs`` in ``examples/`` runs every example and copies its output
to ``docs/source/examples/_gen/<example>/`` (see examples/collect_docs.py):
covsight.Show transcripts, covsight.Check's check.json and the merged
database.  Nothing there is committed; the Forgejo docs job generates it.

.. covsight-transcript:: 01-code-basics/show_basic
   :commands: 1        (optional: 1-based indices, comma-separated)

   Each command as ``$ covsight ...`` followed by its output.

.. covsight-source:: 01-code-basics/show_basic
   :command: 3         (a ``show source -of json`` command of that Show task)
   :lines: 17-37       (optional: only these lines of the file)
   :file: design.sv    (optional when the output has one file)

   The source with each line's hit count, and the branch arms and
   expression rows under the line they start on; missed and partly hit
   lines highlighted (HTML; other builders get ``show source``'s text).

.. covsight-parity:: 01-code-basics

   covsight's covered/total per kind beside verilator_coverage's, with the
   reason for each explained difference.

.. covsight-download:: 01-code-basics/merged.cdb

   A download link to a generated file.

Missing output (examples not run) gives a note on the page and an INFO log
line, so the docs build without Verilator.  Set ``covsight_examples_required``
(or the environment variable ``COVSIGHT_EXAMPLES_REQUIRED=1``) to make it an
error; the docs job does.
"""
import html
import json
import os

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx import addnodes
from sphinx.errors import ExtensionError
from sphinx.util import logging

logger = logging.getLogger(__name__)

GEN = os.path.join("examples", "_gen")


def _gen_dir(env):
    return os.path.join(env.srcdir, GEN)


def _required(config):
    return bool(config.covsight_examples_required) or \
        os.environ.get("COVSIGHT_EXAMPLES_REQUIRED", "") not in ("", "0")


class _ExampleDirective(Directive):
    required_arguments = 1
    has_content = False

    def _path(self):
        return os.path.join(_gen_dir(self.state.document.settings.env),
                            *self.arguments[0].split("/"))

    def _missing(self, what):
        env = self.state.document.settings.env
        msg = ("example output not found: %s (run `dfm run docs` in examples/)"
               % os.path.join(GEN, what))
        if _required(env.config):
            raise ExtensionError("%s:%d: %s" % (env.docname, self.lineno, msg))
        logger.info("%s: %s", env.docname, msg)
        note = nodes.note()
        note += nodes.paragraph(text="This example's output has not been generated "
                                     "in this build. Run ``dfm run docs`` in "
                                     "examples/ and rebuild to see it.")
        return [note]

    def _depend(self, path):
        self.state.document.settings.env.note_dependency(path)


class TranscriptDirective(_ExampleDirective):
    option_spec = {"commands": directives.unchanged}

    def run(self):
        root = self._path()
        index_path = os.path.join(root, "transcript.json")
        if not os.path.isfile(index_path):
            return self._missing(os.path.join(self.arguments[0], "transcript.json"))
        self._depend(index_path)
        with open(index_path) as f:
            index = json.load(f)
        if "commands" in self.options:
            picks = [int(n) for n in self.options["commands"].split(",")]
            index = [index[n - 1] for n in picks]
        ret = []
        for entry in index:
            out_path = os.path.join(root, entry["file"])
            self._depend(out_path)
            with open(out_path) as f:
                text = f.read().rstrip("\n")
            block = nodes.literal_block(
                "", "$ %s\n%s" % (entry["command"], text))
            block["language"] = "text"
            block["classes"].append("covsight-transcript")
            ret.append(block)
        return ret


class SourceDirective(_ExampleDirective):
    option_spec = {"command": directives.positive_int,
                   "lines": directives.unchanged,
                   "file": directives.unchanged}

    def run(self):
        root = self._path()
        index_path = os.path.join(root, "transcript.json")
        if not os.path.isfile(index_path):
            return self._missing(os.path.join(self.arguments[0], "transcript.json"))
        self._depend(index_path)
        with open(index_path) as f:
            entry = json.load(f)[self.options.get("command", 1) - 1]
        out_path = os.path.join(root, entry["file"])
        self._depend(out_path)
        with open(out_path) as f:
            data = json.load(f)
        files = data["files"]
        if "file" in self.options:
            files = [f for f in files if f["file"] == self.options["file"]
                     or f["file"].endswith("/" + self.options["file"])]
        if len(files) != 1:
            raise self.error("%s: expected one file in '%s', found %d (use :file:)"
                             % (self.name, entry["command"], len(files)))
        sfile = dict(files[0])
        if "lines" in self.options:
            lo, _, hi = self.options["lines"].partition("-")
            lo, hi = int(lo), int(hi or lo)
            sfile["lines"] = [ln for ln in sfile["lines"] if lo <= ln["line"] <= hi]

        from covsight.cli.show.show_source import write_file_text
        import io
        buf = io.StringIO()
        write_file_text(sfile, buf)
        text = nodes.literal_block("", buf.getvalue().rstrip("\n"))
        text["language"] = "text"
        fallback = addnodes.only(expr="not html")
        fallback += text
        return [nodes.raw("", _source_html(sfile), format="html"), fallback]


def _token_class(ttype):
    from pygments.token import STANDARD_TYPES
    while ttype not in STANDARD_TYPES:
        ttype = ttype.parent
    return STANDARD_TYPES[ttype]


def _highlight(fname, lines):
    """{line: html} for ``lines`` (a list of (n, text)), highlighted as one
    text so constructs spanning lines lex correctly."""
    from pygments.lexers import TextLexer, get_lexer_for_filename
    from pygments.util import ClassNotFound
    try:
        lexer = get_lexer_for_filename(fname)
    except ClassNotFound:
        lexer = TextLexer()
    nums = [n for n, _ in lines]
    out, cur = {}, []
    i = 0
    for ttype, value in lexer.get_tokens("\n".join(t for _, t in lines) + "\n"):
        cls = _token_class(ttype)
        for k, part in enumerate(value.split("\n")):
            if k:
                if i < len(nums):
                    out[nums[i]] = "".join(cur)
                i, cur = i + 1, []
            if part:
                esc = html.escape(part)
                cur.append('<span class="%s">%s</span>' % (cls, esc) if cls else esc)
    return out


def _source_html(sfile):
    esc = html.escape
    totals = " · ".join("%s %d/%d" % (k, st["covered"], st["total"])
                        for k, st in sfile["by_kind"].items())
    lines = sfile["lines"]
    code = _highlight(sfile["file"], [(ln["line"], ln["text"] or "") for ln in lines])
    rows = []
    prev = None
    for ln in lines:
        if prev is not None and ln["line"] != prev + 1:
            rows.append('<tr class="cs-gap"><td class="cs-ln">⋮</td><td></td><td></td></tr>')
        prev = ln["line"]
        cls = "cs-" + ln["status"] if ln["status"] else "cs-none"
        count = "" if ln["count"] is None else str(ln["count"])
        rows.append('<tr class="%s"><td class="cs-ln">%d</td><td class="cs-n">%s</td>'
                    '<td class="cs-code">%s</td></tr>'
                    % (cls, ln["line"], count, code.get(ln["line"], "")))
        for a in ln["annotations"]:
            arms = "".join(
                '<tr class="%s"><td class="cs-n">%d</td><td>%s</td></tr>'
                % ("cs-covered" if r["covered"] else "cs-missed", r["count"], esc(r["name"]))
                for r in a["rows"])
            rows.append(
                '<tr class="cs-ann"><td></td><td></td><td><div class="cs-point">'
                '<span class="cs-kind">%s</span> <span class="cs-scope">%s</span>'
                '<table class="cs-rows">%s</table></div></td></tr>'
                % (esc(a["kind"]), esc(a["scope"]), arms))
    return ('<div class="covsight-source"><div class="cs-head"><code>%s</code> '
            '<span class="cs-totals">%s</span></div><div class="highlight">'
            '<table class="cs-src"><thead><tr><th>Line</th><th>Hits</th>'
            '<th>Source</th></tr></thead><tbody>%s</tbody></table></div></div>'
            % (esc(sfile["file"]), esc(totals), "".join(rows)))


class ParityDirective(_ExampleDirective):
    STATE = {"match": "agrees", "explained": "differs (explained)",
             "mismatch": "DIFFERS", "stale": "agrees (stale note)"}

    def run(self):
        path = os.path.join(self._path(), "check.json")
        if not os.path.isfile(path):
            return self._missing(os.path.join(self.arguments[0], "check.json"))
        self._depend(path)
        with open(path) as f:
            check = json.load(f)
        rows = check.get("parity") or []
        if not rows:
            return [nodes.paragraph(text="No verilator_coverage comparison was run.")]

        table = nodes.table(classes=["covsight-parity"])
        group = nodes.tgroup(cols=4)
        table += group
        for width in (20, 20, 35, 25):
            group += nodes.colspec(colwidth=width)
        head = nodes.thead()
        group += head
        head += self._row(["Kind", "covsight", "verilator_coverage", "Result"])
        body = nodes.tbody()
        group += body
        notes = []
        for r in rows:
            vlt = r["verilator"]
            if r["verilator_without_std"] != vlt:
                vlt += " (%s without std)" % r["verilator_without_std"]
            body += self._row([r["kind"], r["covsight"], vlt,
                               self.STATE.get(r["state"], r["state"])])
            if r["state"] == "explained" and r.get("explanation"):
                notes.append("%s: %s" % (r["kind"], r["explanation"]))
        ret = [table]
        if notes:
            bl = nodes.bullet_list()
            for n in notes:
                bl += nodes.list_item("", nodes.paragraph(text=n))
            ret.append(bl)
        return ret

    @staticmethod
    def _row(cells):
        row = nodes.row()
        for c in cells:
            entry = nodes.entry()
            entry += nodes.paragraph(text=c)
            row += entry
        return row


class DownloadDirective(_ExampleDirective):
    def run(self):
        path = self._path()
        if not os.path.isfile(path):
            return self._missing(self.arguments[0])
        env = self.state.document.settings.env
        target = "/" + "/".join([GEN.replace(os.sep, "/"), self.arguments[0]])
        ref = addnodes.download_reference(
            "", "", reftarget=target, refdoc=env.docname, refexplicit=True)
        ref += nodes.literal(text=os.path.basename(path))
        para = nodes.paragraph()
        para += nodes.Text("Download: ")
        para += ref
        return [para]


def _add_static(app, config):
    config.html_static_path.append(os.path.join(os.path.dirname(__file__), "static"))


def setup(app):
    app.add_config_value("covsight_examples_required", False, "env")
    app.connect("config-inited", _add_static)
    app.add_css_file("covsight-example.css")
    app.add_directive("covsight-source", SourceDirective)
    app.add_directive("covsight-transcript", TranscriptDirective)
    app.add_directive("covsight-parity", ParityDirective)
    app.add_directive("covsight-download", DownloadDirective)
    return {"version": "0.1", "parallel_read_safe": True,
            "parallel_write_safe": True}
