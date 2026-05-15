"""Base class for covsight show commands."""
import json
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, TextIO

from covsight.cli.format_detection import detect_format
from covsight.core.ext import FormatRegistry


def _default_db_format(registry: FormatRegistry) -> str:
    formats = registry.db_formats()
    if "ncdb" in formats:
        return "ncdb"
    if formats:
        return next(iter(formats.keys()))
    raise ValueError("No database formats are installed")


class ShowBase(ABC):
    def __init__(self, args):
        self.args = args
        self.db = None

    def execute(self):
        registry = FormatRegistry()
        if self.args.input_format is None:
            try:
                self.args.input_format = detect_format(self.args.db, registry)
            except ValueError:
                self.args.input_format = _default_db_format(registry)

        input_desc = registry.get_db_format(self.args.input_format)
        self.db = input_desc.fmt_if.read(self.args.db)
        try:
            self._write_output(self.get_data())
        finally:
            if self.db is not None:
                self.db.close()

    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        raise NotImplementedError()

    def _write_output(self, data: Dict[str, Any]):
        output_format = getattr(self.args, "output_format", "json")
        out = getattr(self.args, "out", None)
        fp = sys.stdout if out is None else open(out, "w")
        close_fp = out is not None
        try:
            if output_format == "json":
                self._write_json(data, fp)
            elif output_format in ("text", "txt"):
                self._write_text(data, fp)
            else:
                raise Exception(f"Unknown output format: {output_format}")
        finally:
            if close_fp:
                fp.close()

    def _write_json(self, data: Dict[str, Any], fp: TextIO):
        json.dump(data, fp, indent=2)
        fp.write("\n")

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        self._format_text_recursive(data, fp, indent=0)

    def _format_text_recursive(self, obj: Any, fp: TextIO, indent: int = 0):
        ind = "  " * indent
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    fp.write(f"{ind}{key}:\n")
                    self._format_text_recursive(value, fp, indent + 1)
                else:
                    fp.write(f"{ind}{key}: {value}\n")
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    self._format_text_recursive(item, fp, indent)
                else:
                    fp.write(f"{ind}- {item}\n")
        else:
            fp.write(f"{ind}{obj}\n")
