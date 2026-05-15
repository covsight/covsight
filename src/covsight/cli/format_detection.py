"""Detect database format from file path or content."""
import pathlib
from typing import Optional

from covsight.core.ext import FormatRegistry


_EXT_MAP = {
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".cdb": "ncdb",
    ".db": "sqlite",
    ".sqlite": "sqlite",
    ".sqlite3": "sqlite",
    ".dat": "vltcov",
}


def detect_format(path: str, registry: Optional[FormatRegistry] = None) -> str:
    if registry is None:
        registry = FormatRegistry()

    ext = pathlib.Path(path).suffix.lower()
    if ext in _EXT_MAP:
        name = _EXT_MAP[ext]
        if name in registry.db_formats():
            return name

    raise ValueError(
        f"Cannot detect format for '{path}'. Available formats: "
        f"{', '.join(sorted(registry.db_formats().keys())) or '(none installed)'}"
    )
