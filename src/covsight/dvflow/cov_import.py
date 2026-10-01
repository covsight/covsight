"""covsight.Import: convert simulator coverage databases to NCDB."""
import asyncio
import logging
import os
import shutil
from typing import Dict, List

from dv_flow.mgr import FileSet, TaskDataResult
from dv_flow.mgr.task_data import SeverityE

from covsight.dvflow.sources import (
    COVSIGHT_NCDB, FORMAT_MAP, CovSource, collect_sources, safe_name,
)

_log = logging.getLogger("covsight.Import")

_ON_UNSUPPORTED = ("error", "warn", "skip")


def _mapping_revision(fmt: str):
    """Importer revision for ``fmt``; a change invalidates converted output."""
    if fmt == "vltcov":
        from covsight.core.vltcov import MAPPING_REVISION
        return MAPPING_REVISION
    return None


async def UpToDate(ctxt) -> bool:
    """Extra up-to-date check run by dv-flow after its own (unchanged inputs
    and params): output written by an older importer is stale."""
    memento = ctxt.memento if isinstance(ctxt.memento, dict) else {}
    for sig in (memento.get("outputs") or {}).values():
        fmt = FORMAT_MAP.get(sig.get("format"))
        if sig.get("mapping") != _mapping_revision(fmt):
            return False
    return True


def _signature(src: CovSource, params: Dict) -> Dict:
    st = os.stat(src.path)
    return dict(mtime_ns=st.st_mtime_ns, size=st.st_size,
                format=src.format, test=src.test_name, seed=src.seed,
                status=src.status, params=params,
                mapping=_mapping_revision(src.covsight_format))


def _convert(src: CovSource, out_path: str, include_std: bool):
    """Runs in a worker thread: read ``src``, stamp its identity, write NCDB."""
    from covsight.core.conversion import apply_test_info

    fmt = src.covsight_format
    if fmt == "ncdb":
        shutil.copyfile(src.path, out_path)
        return []
    if fmt == "vltcov":
        from covsight.core.vltcov import VltParser, VltToUcis
        parser = VltParser()
        items = parser.parse_file(src.path)
        mapper = VltToUcis(include_std=include_std)
        db = mapper.map(items, test_name=src.test_name, physical_name=src.path)
        warnings = list(mapper.warnings)
        warnings += ["%s:%d: unparseable line" % (src.path, n) for n, _ in parser.errors]
    else:
        from covsight.core.ext import FormatRegistry
        db = FormatRegistry().get_db_format(fmt).fmt_if.read(src.path)
        warnings = []

    apply_test_info(db, name=src.test_name or None, seed=src.seed,
                    status=src.status or None, physical_name=src.path)
    from covsight.core.ncdb.ncdb_writer import NcdbWriter
    NcdbWriter().write(db, out_path)
    return warnings


async def Import(ctxt, input) -> TaskDataResult:
    p = input.params
    on_unsupported = (getattr(p, "on_unsupported", "") or "error").lower()
    if on_unsupported not in _ON_UNSUPPORTED:
        ctxt.error("on_unsupported must be one of %s (got %r)" % (
            "/".join(_ON_UNSUPPORTED), on_unsupported))
        return TaskDataResult(status=1)
    include_std = bool(getattr(p, "include_std", False))
    override = dict(test_name=getattr(p, "test_name", "") or None,
                    seed=getattr(p, "seed", "") or None,
                    status=getattr(p, "status", "") or None)

    sources = collect_sources(input.inputs)
    if not sources:
        ctxt.info("no coverage databases among the inputs")

    prev = (input.memento or {}).get("outputs", {}) if isinstance(input.memento, dict) else {}
    memento: Dict[str, Dict] = {}
    output: List[FileSet] = []
    used_names = set()
    status = 0
    changed = False

    for idx, src in enumerate(sources):
        for k, v in override.items():
            if v is not None:
                setattr(src, k, v)
        if len(sources) > 1 and override["test_name"]:
            # One name for several databases: keep them distinct.
            src.test_name = "%s_%d" % (override["test_name"], idx)

        if src.covsight_format is None:
            msg = "%s: coverage format %r is not supported" % (
                src.path, src.format or "(none)")
            if on_unsupported == "error":
                ctxt.error(msg)
                status = 1
            elif on_unsupported == "warn":
                ctxt.marker(msg, severity=SeverityE.Warning)
            continue
        if not os.path.isfile(src.path):
            ctxt.error("%s: coverage database does not exist" % src.path)
            status = 1
            continue

        name = safe_name(src.test_name or os.path.basename(src.path))
        base, i = name, 1
        while name in used_names:
            name = "%s_%d" % (base, i)
            i += 1
        used_names.add(name)
        out_file = name + ".cdb"
        out_path = os.path.join(input.rundir, out_file)

        sig = _signature(src, dict(include_std=include_std))
        if prev.get(out_file) == sig and os.path.isfile(out_path):
            _log.debug("%s up-to-date", out_file)
        else:
            try:
                warnings = await asyncio.to_thread(_convert, src, out_path, include_std)
            except Exception as e:
                ctxt.error("%s: conversion failed: %s" % (src.path, e))
                status = 1
                continue
            for w in warnings:
                ctxt.marker(w, severity=SeverityE.Warning)
            changed = True
        memento[out_file] = sig

        attrs = ["format=ncdb", "test=%s" % src.test_name]
        if src.seed is not None:
            attrs.append("seed=%s" % src.seed)
        if src.status:
            attrs.append("status=%s" % src.status)
        output.append(FileSet(src=input.name, filetype=COVSIGHT_NCDB,
                              basedir=input.rundir, files=[out_file],
                              attributes=attrs))

    # Remove databases from earlier runs whose source has gone away.
    for stale in set(prev) - set(memento):
        try:
            os.unlink(os.path.join(input.rundir, stale))
            changed = True
        except OSError:
            pass

    return TaskDataResult(status=status, changed=changed or input.changed,
                          output=output, memento={"outputs": memento})

