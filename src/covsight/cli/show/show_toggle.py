"""
Show Toggle Command

Toggle coverage per signal: whether each bit has risen (0->1) and fallen
(1->0).  A signal is fully toggled when every bit has done both.
"""
from collections import OrderedDict
from typing import Any, Dict, TextIO

from covsight.cli.show_base import ShowBase


class ShowToggle(ShowBase):

    def get_data(self) -> Dict[str, Any]:
        from covsight.analysis.code_coverage import (
            CodeCoverage, parse_toggle_bin, stats_dict,
        )

        cc = CodeCoverage(self.db)
        signals: "OrderedDict[int, Dict]" = OrderedDict()
        for it in cc.items:
            if it.kind != "toggle":
                continue
            sig = signals.get(id(it.scope))
            if sig is None:
                name = it.scope_name
                sig = signals[id(it.scope)] = {
                    "signal": "%s.%s" % (it.instance, name) if it.instance else name,
                    "instance": it.instance,
                    "file": it.file,
                    "line": it.line,
                    "bits": OrderedDict(),
                    "bins": [],
                }
            parsed = parse_toggle_bin(it.name)
            if parsed is None:
                # Not a transition name; still a toggle bin that counts.
                sig["bins"].append({"name": it.name, "count": it.count,
                                    "covered": it.covered})
                continue
            bit, frm, to = parsed
            entry = sig["bits"].setdefault(bit if bit is not None else "", {})
            if (frm, to) == ("0", "1"):
                entry["rise"] = entry.get("rise", 0) + it.count
                entry["rise_covered"] = entry.get("rise_covered", False) or it.covered
            elif (frm, to) == ("1", "0"):
                entry["fall"] = entry.get("fall", 0) + it.count
                entry["fall_covered"] = entry.get("fall_covered", False) or it.covered
            else:
                entry.setdefault("other", {})["%s->%s" % (frm, to)] = it.count

        rows = []
        n_full = n_partial = 0
        for sig in signals.values():
            bits = []
            untoggled = []
            full = True
            any_hit = False
            for bit, e in sig["bits"].items():
                rise = e.get("rise_covered", False)
                fall = e.get("fall_covered", False)
                full = full and rise and fall
                dirs = [d for d, ok in (("0->1", rise), ("1->0", fall)) if not ok]
                if dirs:
                    untoggled.append(("[%s] " % bit if bit else "") + ",".join(dirs))
                any_hit = any_hit or rise or fall or any(e.get("other", {}).values())
                b = {"bit": bit or None, "rise": e.get("rise", 0),
                     "fall": e.get("fall", 0), "toggled": rise and fall}
                if "other" in e:
                    b["other"] = e["other"]
                bits.append(b)
            for b in sig["bins"]:
                full = full and b["covered"]
                any_hit = any_hit or b["covered"]
                if not b["covered"]:
                    untoggled.append(b["name"])
            status = "full" if full else ("partial" if any_hit else "none")
            n_full += status == "full"
            n_partial += status == "partial"
            if getattr(self.args, "uncovered", False) and status == "full":
                continue
            row = OrderedDict(signal=sig["signal"], status=status,
                              width=max(len(bits), 1))
            if sig["file"]:
                row["file"] = sig["file"]
                row["line"] = sig["line"]
            row["untoggled"] = untoggled
            row["bits"] = bits
            if sig["bins"]:
                row["bins"] = sig["bins"]
            rows.append(row)

        bins = cc.by_kind(("toggle",))["toggle"]
        return {
            "database": self.args.db,
            "summary": {
                "total_signals": len(signals),
                "fully_toggled": n_full,
                "partially_toggled": n_partial,
                "not_toggled": len(signals) - n_full - n_partial,
                "bins": stats_dict(bins),
                "coverage_percentage": round(bins.coverage_pct, 2),
            },
            "signals": rows,
        }

    def _write_text(self, data: Dict[str, Any], fp: TextIO):
        s = data["summary"]
        fp.write("Toggle coverage: %s\n\n" % data["database"])
        if not s["total_signals"]:
            fp.write("No toggle coverage in this database.\n")
            return
        fp.write("Signals: %d (full %d, partial %d, none %d)\n" % (
            s["total_signals"], s["fully_toggled"], s["partially_toggled"],
            s["not_toggled"]))
        fp.write("Bins:    %.2f%% (%d/%d)\n\n" % (
            s["bins"]["coverage"], s["bins"]["covered"], s["bins"]["total"]))
        width = max([len(r["signal"]) for r in data["signals"]] + [6])
        fp.write("%-*s  %-7s  %s\n" % (width, "Signal", "Status", "Untoggled"))
        fp.write("%s  %s  %s\n" % ("-" * width, "-" * 7, "-" * 9))
        for r in data["signals"]:
            fp.write(("%-*s  %-7s  %s" % (width, r["signal"], r["status"],
                                           "; ".join(r["untoggled"]))).rstrip() + "\n")
