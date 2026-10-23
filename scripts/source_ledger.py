#!/usr/bin/env python
"""The row ledger: every exchange of every inventory, with where it came from.

    python scripts/source_ledger.py          # writes docs/SOURCE_LEDGER.md

Walks ``optimiser_lca.build.inventories()`` (no Brightway) and writes one
table per activity: key, printed amount, unit, the amount after ``scale``,
the note, and how the row is located — by its own locator (another source
named at the start of its note), by a grade (``ADDED`` / ``ASSUMED`` /
``DERIVED``), or by its activity (a row of the activity's own source table,
which the activity's ``comment`` names). Rows with none of those are listed
first as *unaccounted*; ``tests/test_sources.py`` holds that list at zero.

This is the module → source direction of the guarantee in
LCA_ASSURANCE_PLAN.md Part 2: nothing in a module without a stated origin.
The source → module direction (every source row has a disposition) is the
per-source ledgers under docs/source_ledgers/ and ``tests/test_sources.py``.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimiser_lca import build  # noqa: E402
from optimiser_lca.common import FG  # noqa: E402

OUT = ROOT / "docs" / "SOURCE_LEDGER.md"

GRADES = re.compile(r"\b(ADDED|ASSUMED|DERIVED|TRANSCRIBED)\b")
# A locator at the start of a note: an author, a report code, a table or
# figure reference. Rows carrying one belong to a table other than (or more
# specific than) their activity's.
LOCATOR = re.compile(
    r"^(Jasper|Voß|Voss|Smith|IEA|Z-PV|Usai|Babatunde|Gramc|Zhang|Gandiglio|Leng|Gerloff|Hermesmann|"
    r"Mehmeti|Degen|Carrère|Carrere|Engels|Hu |Verma|Teffera|Vestas|ecoinvent|Table|Tab\.|SI |ESI|"
    r"Fig|§|A\d{1,2}\b|S\d{1,2}\b|r\d{1,3}\b|row \d)", re.I)
# What each module's activities are transcribed from, for the inherited case.
SOURCE_OF = {
    "upv": "Smith 2024 Appendix A (table named in the activity) / IEA PVPS Z-PV-239",
    "gb_grid": "the study's own grid basis (optimiser_lca/grid.py) and the 2025 series",
    "hydrogen": "Hermesmann & Müller 2022 Tables 2–3 / Gerloff 2021 SI Figs 1–5, Tables 3–6",
    "data_centre": "Zhang et al. 2025 Table 1 / S1",
    "bess": "Jasper et al. 2026 SI (container) / Voß et al. 2025 Table 3 and ESI (cell)",
    "fuel_cell": "Babatunde 2024 Table S1 / Usai 2021 SI Table 1 / Gramc 2025",
    "h2_tank": "Gandiglio et al. 2022 Table 5",
    "stepup_transformers": "Leng 2026 Table S1/S3 / IEA PVPS Table 49–50 / Jasper 2026 / Smith A15",
}


def classify(note: str) -> str:
    note = (note or "").strip()
    if not note:
        return "unaccounted"
    if GRADES.search(note):
        return GRADES.search(note).group(1)
    if LOCATOR.match(note):
        return "own locator"
    return "activity's table"


def rows_of(inv, a):
    for r in list(a.technosphere) + list(a.biosphere):
        key, amount, unit, note = (list(r) + [None] * 4)[:4]
        if isinstance(key, FG):
            tgt = next((x for x in inv.activities if x.code == key.code), None)
            name = f"→ {tgt.name if tgt else key.code}"
        elif key in inv.processes:
            name = inv.processes[key].identity[0] if inv.processes[key].identity else str(key)
        else:
            name = inv.flows[key].identity[0] if inv.flows[key].identity else str(key)
        yield key, name, amount, unit, note or "", classify(note or "")


def build_ledger() -> tuple[str, dict]:
    counts = {"rows": 0, "activity's table": 0, "own locator": 0, "ADDED": 0, "ASSUMED": 0,
              "DERIVED": 0, "TRANSCRIBED": 0, "unaccounted": 0}
    unaccounted = []
    body = []
    for name, inv in build.inventories():
        body += [f"## {name} — {inv.name}", "",
                 f"Database `{inv.database}`; source of the activities' own tables: {SOURCE_OF.get(name, '?')}.", ""]
        for a in inv.activities:
            per = f"; production amount {a.production_amount:g}" if a.production_amount != 1.0 else ""
            sc = f"; scale ×{a.scale:.9g} ({a.scale_note})" if a.scale != 1.0 else ""
            body += [f"### `{a.code}` — {a.name}", "",
                     f"{a.unit}, {a.location}{per}{sc}. Comment: {a.comment[:300]}{'…' if len(a.comment) > 300 else ''}", "",
                     "| Key | Input | Printed amount | Unit | After scale | Note | Located by |", "|---|---|---|---|---|---|---|"]
            for key, inp, amount, unit, note, how in rows_of(inv, a):
                counts["rows"] += 1
                counts[how] += 1
                if how == "unaccounted":
                    unaccounted.append(f"{name} / {a.code} / {key}")
                after = amount * a.scale
                k = f"FG:{key.code}" if isinstance(key, FG) else str(key)
                body.append(f"| `{k}` | {inp} | {amount:g} | {unit} | {after:.6g} | {note.replace('|', '/')} | {how} |")
            body.append("")
    head = ["# Source ledger — every inventory row and where it came from",
            "", f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `scripts/source_ledger.py` from the modules in "
            "`optimiser_lca/`. Regenerate after any inventory edit; do not edit by hand.", "",
            "| Rows | Of the activity's own table | Own locator | ADDED | ASSUMED | DERIVED | TRANSCRIBED | Unaccounted |",
            "|---|---|---|---|---|---|---|---|",
            f"| {counts['rows']} | {counts[chr(97) + 'ctivity' + chr(39) + 's table']} | {counts['own locator']} | "
            f"{counts['ADDED']} | {counts['ASSUMED']} | {counts['DERIVED']} | {counts['TRANSCRIBED']} | {counts['unaccounted']} |",
            "", "A row *of the activity's own table* is located by the source its activity's comment names; a row "
            "with its *own locator* starts with another source, table or figure; a graded row is the module's own "
            "addition or derivation and says so. **Unaccounted** rows have an empty note and must be zero.", ""]
    if unaccounted:
        head += ["### Unaccounted rows", ""] + [f"- {u}" for u in unaccounted] + [""]
    return "\n".join(head + body) + "\n", counts


def main() -> int:
    text, counts = build_ledger()
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {counts}")
    return 1 if counts["unaccounted"] else 0


if __name__ == "__main__":
    sys.exit(main())
