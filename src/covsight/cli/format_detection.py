"""Detect database format from file content or path."""
import pathlib
from typing import Optional

from covsight.core.ext import FormatRegistry


_EXT_MAP = {
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".cdb": "ncdb",
    ".ncdb": "ncdb",
    ".db": "sqlite",
    ".sqlite": "sqlite",
    ".sqlite3": "sqlite",
    ".dat": "vltcov",
}


def _sniff(path: str) -> Optional[str]:
    """Format name from the file's leading bytes, or None."""
    try:
        with open(path, "rb") as fp:
            head = fp.read(256)
    except OSError:
        return None
    if head.startswith(b"PK"):
        from covsight.core.ncdb.format_detect import detect_cdb_format
        fmt = detect_cdb_format(path)
        return fmt if fmt != "unknown" else None
    if head.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    text = head.lstrip()
    if text.startswith(b"# SystemC::Coverage"):
        return "vltcov"
    if text.startswith(b"<?xml") or text.startswith(b"<UCIS") or b"<UCIS" in head:
        return "xml"
    return None


def detect_format(path: str, registry: Optional[FormatRegistry] = None) -> str:
    """Return the registered format name for ``path``.

    Content is checked before the extension, so a renamed file is still read
    correctly.  Raises ValueError when the format cannot be determined or is
    not installed -- callers should report that rather than guess.
    """
    if registry is None:
        registry = FormatRegistry()
    available = registry.db_formats()

    name = _sniff(path)
    if name is None:
        name = _EXT_MAP.get(pathlib.Path(path).suffix.lower())
    if name is not None and name in available:
        return name

    installed = ", ".join(sorted(available.keys())) or "(none installed)"
    if name is not None:
        raise ValueError(
            f"'{path}' looks like format '{name}', which is not installed. "
            f"Installed formats: {installed}")
    raise ValueError(
        f"Cannot detect the format of '{path}'; specify it with "
        f"--input-format. Installed formats: {installed}")
