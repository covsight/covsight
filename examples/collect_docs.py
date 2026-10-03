"""Copy each example's output from the dv-flow run directory into the docs.

    python3 collect_docs.py <rundir> <out> <examples dir>

For every example the suite's flow.yaml imports, the
``covsight.Show`` transcripts, the ``covsight.Check`` result and the merged
database go to ``<out>/<example>/``:

    <out>/01-code-basics/
      check.json
      merged.cdb
      show_basic/      01-show-code-coverage.txt ... transcript.json
      show_merged/     ...

The ``covsight-example`` Sphinx directive renders a page from this tree.
An example without a check.json is an error: its page would be empty.
"""
import os
import shutil
import sys

import yaml


def _package(flow):
    with open(flow) as f:
        return (yaml.safe_load(f) or {}).get("package", {})


def examples(src):
    """``(directory, package name)`` for each example the suite imports."""
    for imp in _package(os.path.join(src, "flow.yaml")).get("imports", []):
        path = imp.get("from") if isinstance(imp, dict) else None
        if path:
            flow = os.path.join(src, path)
            yield os.path.basename(os.path.dirname(flow)), _package(flow)["name"]


def collect(rundir, out, name, pkg):
    dst = os.path.join(out, name)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    prefix = pkg + "."
    found = []
    for task_dir in sorted(os.listdir(rundir)):
        if not task_dir.startswith(prefix):
            continue
        task, path = task_dir[len(prefix):], os.path.join(rundir, task_dir)
        if os.path.isfile(os.path.join(path, "transcript.json")):
            shutil.copytree(path, os.path.join(dst, task),
                            ignore=shutil.ignore_patterns("*.json", "*.log"),
                            dirs_exist_ok=True)
            shutil.copy(os.path.join(path, "transcript.json"), os.path.join(dst, task))
            found.append(task)
        for fname in ("check.json", "merged.cdb"):
            if os.path.isfile(os.path.join(path, fname)):
                shutil.copy(os.path.join(path, fname), dst)
                found.append(fname)
    if "check.json" not in found:
        sys.exit("collect_docs: %s (package %s) has no check.json under %s" % (
            name, pkg, rundir))
    print("collect_docs: %s: %s" % (name, ", ".join(found)))


def main(argv):
    if len(argv) != 4:
        sys.exit(__doc__)
    rundir, out, src = argv[1:]
    os.makedirs(out, exist_ok=True)
    for name, pkg in examples(src):
        collect(rundir, out, name, pkg)


if __name__ == "__main__":
    main(sys.argv)
