"""Find coverage databases among a dv-flow task's inputs.

Kept free of dv-flow imports so it can be exercised directly.  Inputs may be
pydantic models or (after a cache round-trip) plain dicts, so every field is
read through :func:`_get`.

Sources, in order of preference for test identity:

* ``hdlsim.TestResult`` -- carries the verdict, case name and seed
* ``hdlsim.SimRunResult`` -- carries exit status and ``runinfo``
* ``hdlsim.SuiteResult`` -- its ``results`` list of TestResults
* a bare FileSet with ``filetype: simCovDb``

TestResult forwards its SimRunResult's artifacts, so the same database can
arrive twice; it is imported once, with the richest identity available.
"""
import dataclasses as dc
import os
import re
from typing import Any, Dict, List, Optional

SIM_COV_DB = "simCovDb"
COVSIGHT_NCDB = "covsightNCDB"

# simCovDb `format=` attribute -> covsight format name
FORMAT_MAP = {
    "vlt-dat": "vltcov",
    "ncdb": "ncdb",
}

_RANK = {"hdlsim.TestResult": 3, "hdlsim.SimRunResult": 2, "std.FileSet": 1}


@dc.dataclass
class CovSource:
    path: str               # absolute path of the database file
    format: str             # the simCovDb `format=` attribute ("" if absent)
    test_name: str = ""
    seed: Optional[str] = None
    status: Optional[str] = None   # pass / fail / error
    origin: str = ""        # input item type that supplied the identity

    @property
    def covsight_format(self) -> Optional[str]:
        return FORMAT_MAP.get(self.format)


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _attrs(fs) -> Dict[str, str]:
    ret = {}
    for a in _get(fs, "attributes", None) or []:
        k, sep, v = str(a).partition("=")
        if sep:
            ret[k] = v
    return ret


def _fileset_paths(fs) -> List[str]:
    basedir = _get(fs, "basedir", "") or ""
    return [f if os.path.isabs(f) else os.path.normpath(os.path.join(basedir, f))
            for f in _get(fs, "files", None) or []]


def _cov_filesets(artifacts) -> List[Any]:
    return [a for a in artifacts or [] if _get(a, "filetype") == SIM_COV_DB]


def _test_result_identity(tr) -> Dict[str, Any]:
    runinfo = _get(tr, "runinfo", None) or {}
    seed = _get(tr, "seed", 0) or runinfo.get("seed")
    status = _get(tr, "status", "") or ("pass" if _get(tr, "passed", False) else "fail")
    return dict(test_name=_get(tr, "name", "") or _get(tr, "testname", "")
                or runinfo.get("case_name", "") or runinfo.get("testname", ""),
                seed=None if seed in (None, "") else str(seed),
                status=status)


def _sim_run_identity(rr) -> Dict[str, Any]:
    runinfo = _get(rr, "runinfo", None) or {}
    seed = runinfo.get("seed")
    name = runinfo.get("case_name") or runinfo.get("testname") or ""
    if not name and runinfo.get("rundir"):
        name = os.path.basename(os.path.normpath(runinfo["rundir"]))
    return dict(test_name=name,
                seed=None if seed in (None, "") else str(seed),
                status="pass" if (_get(rr, "status", 0) or 0) == 0 else "error")


def collect_sources(inputs) -> List[CovSource]:
    """Coverage databases found in ``inputs``, one entry per file."""
    found: Dict[str, CovSource] = {}
    rank: Dict[str, int] = {}

    def add(fs, identity, origin):
        fmt = _attrs(fs).get("format", "")
        for path in _fileset_paths(fs):
            r = _RANK.get(origin, 0)
            if path in found and rank[path] >= r:
                continue
            ident = dict(identity)
            if not ident.get("test_name"):
                ident["test_name"] = (_get(fs, "src", "") or
                                      os.path.basename(os.path.dirname(path)))
            found[path] = CovSource(path=path, format=fmt, origin=origin, **ident)
            rank[path] = r

    for item in inputs or []:
        itype = _get(item, "type", "")
        if itype == "hdlsim.TestResult":
            for fs in _cov_filesets(_get(item, "artifacts")):
                add(fs, _test_result_identity(item), itype)
        elif itype == "hdlsim.SuiteResult":
            for tr in _get(item, "results", None) or []:
                for fs in _cov_filesets(_get(tr, "artifacts")):
                    add(fs, _test_result_identity(tr), "hdlsim.TestResult")
        elif itype == "hdlsim.SimRunResult":
            for fs in _cov_filesets(_get(item, "artifacts")):
                add(fs, _sim_run_identity(item), itype)
        elif _get(item, "filetype") == SIM_COV_DB:
            add(item, {}, "std.FileSet")
    return list(found.values())


def ncdb_paths(inputs) -> List[str]:
    """Paths of ``covsightNCDB`` FileSets among ``inputs``, in input order."""
    ret = []
    for item in inputs or []:
        if _get(item, "filetype") == COVSIGHT_NCDB:
            for p in _fileset_paths(item):
                if p not in ret:
                    ret.append(p)
    return ret


_UNSAFE = re.compile(r"[^A-Za-z0-9_.+-]+")


def safe_name(name: str) -> str:
    return _UNSAFE.sub("_", name).strip("._") or "cov"
