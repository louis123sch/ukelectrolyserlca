"""The cost and carbon workbooks keep the layout people read them by.

``scripts/build_workbooks.py`` writes them (layout: ``scripts/workbook_layout.py``):
a Summary first, one sheet per technology, then shared and other figures, the
hourly series and the sources. ``scripts/check_workbooks.py`` recalculates them
in Excel; this checks, without Excel, that a built workbook still has that
shape: every named cell the checker reads exists, and the formulas are written
with cell references a reader can follow (Ctrl+[), not leftover names.

Skipped when the workbooks have not been built.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "optimisation_outputs"
BOOKS = ("cost_workbook.xlsx", "carbon_workbook.xlsx")
FUNCTIONS = {"IF", "ROUND", "SUM", "SUMPRODUCT", "MIN", "MAX", "ABS"}


@pytest.mark.parametrize("book", BOOKS)
def test_workbook_layout(book):
    path = OUT / book
    if not path.exists():
        pytest.skip(f"no {book} - run scripts/build_workbooks.py")
    openpyxl = pytest.importorskip("openpyxl")
    from workbook_layout import CHAIN_NAMES, SUMMARY, TOKEN
    wb = openpyxl.load_workbook(path)
    names = wb.sheetnames
    assert names[0] == SUMMARY, f"{book}: the first sheet is {names[0]!r}, not the summary"
    tech = [n for n in names if n in CHAIN_NAMES.values()]
    assert len(tech) >= 5, f"{book}: only {tech} as technology sheets"
    assert names.index(tech[-1]) < names.index("Sources"), f"{book}: technology sheets after the sources"
    if book.startswith("carbon"):
        assert "Inventory" in names and "Ecoinvent scores" in names

    summary = [r[0].value for r in wb[SUMMARY].iter_rows()]
    assert "Total, the parts added" in summary and "The run's own total" in summary
    for n in tech:
        firsts = [r[0].value for r in wb[n].iter_rows()]
        for heading in ("What it adds to the total", "How each figure is made"):
            assert heading in firsts, f"{book}: sheet {n!r} has no {heading!r}"

    expected = json.loads(path.with_suffix(".expected.json").read_text(encoding="utf-8"))
    defined = set(wb.defined_names.keys()) if hasattr(wb.defined_names, "keys") else \
        {d.name for d in wb.defined_names.definedName}
    missing = [n for n in expected if n not in defined]
    assert not missing, f"{book}: {len(missing)} checked cells have no name, e.g. {missing[:5]}"

    leftover = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    body = re.sub(r"'[^']*'!", "", c.value)
                    words = [m for m in TOKEN.findall(body) if m.upper() not in FUNCTIONS
                             and not re.fullmatch(r"\$?[A-Z]{1,3}\$?\d+", m)]
                    if words:
                        leftover.append(f"{ws.title}!{c.coordinate}: {words[:3]}")
    assert not leftover, f"{book}: formulas still written with names: {leftover[:5]}"
