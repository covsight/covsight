"""``expect.yaml``: what an example's coverage run should produce.

Read by ``covsight.Check`` (totals, parity notes, expected warnings) and by
``covsight.Show`` (the transcript commands)::

    totals:            # covered/total per kind; kinds left out are not checked
      line: 11/11
      branch: 7/8
    transcript:        # covsight commands for the docs, in order
      - show code-coverage -of text
    parity:            # known differences from verilator_coverage, each explained
      covergroup: Verilator counts the default bin
    warnings:          # Verilator build warnings expected (regex); others fail
      - COVERIGN

Kind names are covsight's (:data:`covsight.analysis.totals.KINDS`).  Errors
are reported as ``file:line: message``.  No dv-flow imports, so this can be
used and tested on its own; ``expect.schema.json`` describes the same format
for editors.
"""
from __future__ import annotations

import dataclasses as dc
import re
from typing import Dict, List, Tuple

import yaml

from covsight.analysis.totals import KINDS

_RATIO_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
_KEYS = ("totals", "transcript", "parity", "warnings")


class ExpectError(Exception):
    """One or more problems in an expect.yaml; ``errors`` lists them."""

    def __init__(self, errors: List[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


@dc.dataclass
class Expect:
    path: str = ""
    totals: Dict[str, Tuple[int, int]] = dc.field(default_factory=dict)
    transcript: List[str] = dc.field(default_factory=list)
    parity: Dict[str, str] = dc.field(default_factory=dict)
    warnings: List[str] = dc.field(default_factory=list)


def _scalar(node) -> str:
    return node.value if isinstance(node, yaml.ScalarNode) else None


def load_expect(path: str) -> Expect:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return parse_expect(text, path)


def parse_expect(text: str, path: str = "<expect>") -> Expect:
    errors: List[str] = []

    def err(node, msg):
        line = node.start_mark.line + 1 if node is not None else 1
        errors.append("%s:%d: %s" % (path, line, msg))

    try:
        root = yaml.compose(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = mark.line + 1 if mark else 1
        raise ExpectError(["%s:%d: not valid YAML: %s" % (
            path, line, getattr(e, "problem", None) or e)])

    ret = Expect(path=path)
    if root is None:
        return ret
    if not isinstance(root, yaml.MappingNode):
        raise ExpectError(["%s:1: expected a mapping with keys %s" % (
            path, ", ".join(_KEYS))])

    for knode, vnode in root.value:
        key = _scalar(knode)
        if key == "totals":
            _totals(vnode, ret, err)
        elif key == "parity":
            _parity(vnode, ret, err)
        elif key in ("transcript", "warnings"):
            _str_list(key, vnode, ret, err)
        else:
            err(knode, "unknown key %r (expected one of: %s)" % (key, ", ".join(_KEYS)))

    if errors:
        raise ExpectError(errors)
    return ret


def _kind(knode, err):
    kind = _scalar(knode)
    if kind not in KINDS:
        err(knode, "unknown coverage kind %r (expected one of: %s)" % (
            kind, ", ".join(KINDS)))
        return None
    return kind


def _mapping(key, vnode, err):
    if not isinstance(vnode, yaml.MappingNode):
        err(vnode, "%s: expected a mapping of kind to value" % key)
        return []
    return vnode.value


def _totals(vnode, ret, err):
    for knode, rnode in _mapping("totals", vnode, err):
        kind = _kind(knode, err)
        m = _RATIO_RE.match(_scalar(rnode) or "")
        if m is None:
            err(rnode, "totals.%s: expected 'covered/total', e.g. 7/8" % _scalar(knode))
            continue
        cov, tot = int(m.group(1)), int(m.group(2))
        if cov > tot:
            err(rnode, "totals.%s: covered (%d) is more than total (%d)" % (
                _scalar(knode), cov, tot))
        elif kind:
            ret.totals[kind] = (cov, tot)


def _parity(vnode, ret, err):
    for knode, snode in _mapping("parity", vnode, err):
        kind = _kind(knode, err)
        reason = _scalar(snode)
        if not reason or not reason.strip():
            err(snode, "parity.%s: give the reason for the difference" % _scalar(knode))
        elif kind:
            ret.parity[kind] = reason.strip()


def _str_list(key, vnode, ret, err):
    if not isinstance(vnode, yaml.SequenceNode):
        err(vnode, "%s: expected a list of strings" % key)
        return
    out = getattr(ret, key)
    for item in vnode.value:
        s = _scalar(item)
        if not s or not s.strip():
            err(item, "%s: expected a non-empty string" % key)
            continue
        s = s.strip()
        if key == "transcript":
            if s.startswith("covsight "):
                s = s[len("covsight "):]
        else:
            try:
                re.compile(s)
            except re.error as e:
                err(item, "warnings: %r is not a valid regular expression: %s" % (s, e))
                continue
        out.append(s)
