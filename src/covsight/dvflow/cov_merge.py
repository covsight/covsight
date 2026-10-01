"""covsight.Merge: combine NCDB databases into one."""
import asyncio
import os
import shutil

from dv_flow.mgr import FileSet, TaskDataResult

from covsight.dvflow.sources import COVSIGHT_NCDB, ncdb_paths


def _merge(paths, out_path):
    if len(paths) == 1:
        shutil.copyfile(paths[0], out_path)
        return
    from covsight.core.ncdb.ncdb_merger import NcdbMerger
    NcdbMerger().merge(paths, out_path)


async def Merge(ctxt, input) -> TaskDataResult:
    out_file = getattr(input.params, "output", "") or "merged.cdb"
    out_path = os.path.join(input.rundir, out_file)
    paths = ncdb_paths(input.inputs)
    if not paths:
        ctxt.error("no %s databases among the inputs" % COVSIGHT_NCDB)
        return TaskDataResult(status=1)

    sig = [[p, os.stat(p).st_mtime_ns, os.stat(p).st_size] for p in paths]
    memento = {"inputs": sig, "output": out_file}
    changed = True
    if input.memento == memento and os.path.isfile(out_path):
        changed = False
    else:
        try:
            await asyncio.to_thread(_merge, paths, out_path)
        except Exception as e:
            ctxt.error("merge failed: %s" % e)
            return TaskDataResult(status=1)

    return TaskDataResult(
        changed=changed or input.changed,
        output=[FileSet(src=input.name, filetype=COVSIGHT_NCDB,
                        basedir=input.rundir, files=[out_file],
                        attributes=["format=ncdb", "merged=%d" % len(paths)])],
        memento=memento)
