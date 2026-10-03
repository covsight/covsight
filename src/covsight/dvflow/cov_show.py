"""covsight.Show: run covsight commands on a database and keep their output.

Each command (``show code-coverage -of text``) runs as ``covsight <command>
<db>`` from the database's directory, so the output names the database by
its file name, as a user typing the command would see it.  Output goes to
``<n>-<slug>.txt``; ``transcript.json`` lists the commands in order:

    [{"command": "covsight show summary merged.cdb", "file": "01-show-summary.txt",
      "status": 0}]

Commands come from the ``commands`` parameter or, when that is empty, from
the ``transcript`` list in the file named by ``expect``.  ``{srcdir}`` in a
command is the flow's source directory; the transcript shows it as ``.``, as
a user running the command from there would type it
(``show code-coverage -sr {srcdir}`` reports source files relative to it).
"""
import asyncio
import json
import os
import re
import shlex
import subprocess
import sys
from typing import List

from dv_flow.mgr import FileSet, TaskDataResult

from covsight.dvflow.sources import COVSIGHT_NCDB, ncdb_paths

TRANSCRIPT = "covsightTranscript"
INDEX = "transcript.json"


def _slug(cmd: str) -> str:
    words = []
    for w in shlex.split(cmd):
        if w.startswith("-") or w == "{db}" or len(words) == 3:
            break
        words.append(w)
    return re.sub(r"[^A-Za-z0-9]+", "-", "-".join(words)).strip("-").lower() or "cmd"


def _argv(cmd: str, db_name: str, srcdir: str = ".") -> List[str]:
    """Command words with the database put where a user would type it: in
    place of ``{db}``, else after the subcommand words, before any option."""
    words = [w.replace("{srcdir}", srcdir) for w in shlex.split(cmd)]
    if "{db}" in words:
        return [db_name if w == "{db}" else w for w in words]
    i = next((n for n, w in enumerate(words) if w.startswith("-")), len(words))
    return words[:i] + [db_name] + words[i:]


def _display(cmd: str, db_name: str) -> str:
    return "covsight " + " ".join(shlex.quote(w) for w in _argv(cmd, db_name))


def _run(cmd: str, db_path: str, srcdir: str) -> subprocess.CompletedProcess:
    db_dir, db_name = os.path.split(db_path)
    argv = _argv(cmd, db_name, os.path.abspath(srcdir or "."))
    return subprocess.run([sys.executable, "-m", "covsight.cli"] + argv,
                          cwd=db_dir or ".", capture_output=True, text=True)


def resolve(path: str, srcdir: str) -> str:
    """A parameter path, relative to the task's source directory."""
    return path if os.path.isabs(path) else os.path.join(srcdir or ".", path)


def commands_of(params, srcdir) -> List[str]:
    cmds = list(getattr(params, "commands", None) or [])
    if cmds:
        return [c[len("covsight "):] if c.startswith("covsight ") else c for c in cmds]
    expect = getattr(params, "expect", "") or ""
    if expect:
        from covsight.dvflow.expect import load_expect
        return load_expect(resolve(expect, srcdir)).transcript
    return []


async def Show(ctxt, input) -> TaskDataResult:
    try:
        cmds = commands_of(input.params, input.srcdir)
    except Exception as e:
        ctxt.error(str(e))
        return TaskDataResult(status=1)
    dbs = ncdb_paths(input.inputs)
    if len(dbs) != 1:
        ctxt.error("expected one %s database among the inputs, got %d%s" % (
            COVSIGHT_NCDB, len(dbs), " (merge them first)" if dbs else ""))
        return TaskDataResult(status=1)
    (db,) = dbs

    st = os.stat(db)
    memento = {"db": [db, st.st_mtime_ns, st.st_size], "commands": cmds}
    index_path = os.path.join(input.rundir, INDEX)
    if input.memento == memento and os.path.isfile(index_path):
        with open(index_path) as f:
            files = [e["file"] for e in json.load(f)] + [INDEX]
        return TaskDataResult(changed=input.changed, memento=memento, output=[
            FileSet(src=input.name, filetype=TRANSCRIPT, basedir=input.rundir,
                    files=files)])

    index, files, status = [], [], 0
    for n, cmd in enumerate(cmds, 1):
        r = await asyncio.to_thread(_run, cmd, db, input.srcdir)
        fname = "%02d-%s.txt" % (n, _slug(cmd))
        with open(os.path.join(input.rundir, fname), "w") as f:
            f.write(r.stdout)
        index.append({"command": _display(cmd, os.path.basename(db)),
                      "file": fname, "status": r.returncode})
        files.append(fname)
        if r.returncode != 0:
            status = 1
            ctxt.error("'%s' failed (exit %d): %s" % (
                index[-1]["command"], r.returncode, r.stderr.strip()[-500:]))
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)
    files.append(INDEX)

    return TaskDataResult(
        status=status, changed=True, memento=memento if status == 0 else None,
        output=[FileSet(src=input.name, filetype=TRANSCRIPT,
                        basedir=input.rundir, files=files)])
