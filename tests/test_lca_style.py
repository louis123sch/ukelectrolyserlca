"""Every inventory module in the approved shape — the rules in bold in
docs/LCA_STYLE.md, held mechanically.

One module per LCA, built from Python literals and arithmetic on them: no
file is opened to get an amount, nothing is read from JSON, CSV or a
spreadsheet. A docstring that states the source and the functional unit; the
sections in order; every ``Process`` with an identity and the query that
found it, and a reason wherever the pick was a choice; every ``Flow`` pinned
with its compartment; every activity's ``code`` from the registry, its
``comment`` naming its source, every row a four-field tuple with a note;
graded parameters; no commented-out code, no TODOs, no line past 140
characters. Outside the package: ``dc_config.py`` holds no inventory, the
reader notebook builds nothing, ``optimisation/data/`` holds evidence only.

No Brightway. Day one (22 Oct 2026) this file is red on the slips the
assurance plan's Part 4 lists; it goes green as 4.4 lands, and stays in the
suite so a module cannot stray again.
"""
from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimiser_lca import build, registry  # noqa: E402

PKG = ROOT / "optimiser_lca"
MODULES = [n for n, _ in build.MODULES]              # the eight inventories
INFRASTRUCTURE = ["common", "registry", "build", "grid", "validate"]

# --- §1: the only file reads in the package are checks, not inputs ------------
# (module, enclosing function) -> why it is allowed. "<module>" is module level.
ALLOWED_IO = {
    ("gb_grid", "check_against_series"):
        "re-derives MIX_2025 and IMPORTS_2025 from the series they were transcribed from",
    ("grid", "<module>"):
        "json.dumps canonicalises basis() for sources_id(); nothing is read",
    ("grid", "show"): "prints the source table",
    ("grid", "source_table"): "scores the sources through lca_helpers; no file",
    ("grid", "source_scores"): "as source_table",
}
DATA_MODULES = {"json", "csv", "yaml", "openpyxl", "pandas", "xlrd", "pickle", "tomllib"}
READ_CALLS = {"open", "read_text", "read_csv", "read_excel", "read_json", "read_parquet",
              "load", "loads", "load_workbook"}
DATA_SUFFIXES = (".json", ".csv", ".xlsx", ".xls", ".yaml", ".yml", ".parquet", ".pkl")
# Module-level string constants that may end in a data suffix, and why.
ALLOWED_DATA_LITERALS = {("gb_grid", "SERIES_CSV"): "the series check_against_series() reads"}
# What optimisation/data/ may hold: source documents as evidence, nothing a module reads.
EVIDENCE_FILES = {"IEA-PVPS-T12-33-2026-LCI-PV-SupplyChains.xlsx", "UPV-DEFERRED-ISSUES.md",
                  "gb_outline.geojson", "smith-nrel-2024-life-cycle-inventory.md"}
EVIDENCE_DIRS = {"sources"}

# --- §3–4: the words that mark a source in a module's text ----------------------
MODULE_SOURCES = {
    "upv": ("Smith", "IEA PVPS", "Z-PV", "Renewables.ninja", "grid"),
    "gb_grid": ("grid", "series", "NESO", "Carbon Intensity"),
    "hydrogen": ("Hermesmann", "Gerloff"),
    "data_centre": ("Zhang",),
    "bess": ("Jasper", "Voß", "Voss"),
    "fuel_cell": ("Babatunde", "Usai", "Gramc", "ecoinvent"),
    "h2_tank": ("Gandiglio",),
    "stepup_transformers": ("Leng", "IEA PVPS", "Jasper", "Smith"),
}
# Processes that may carry an identity without a query, and why.
ALLOWED_NO_QUERY: dict[tuple[str, str], str] = {}
GRADE = re.compile(r"\b(TRANSCRIBED|DERIVED|ASSUMED|transcribed|derived|assumed|"
                   r"constant|conversion|definition|read off)\b")
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
# Keys that mirror an external identifier may keep its case: the grid fuels are
# the Carbon Intensity API's own names (GAS, NUCLEAR, IMPORTS_FR), the basis the
# series id 055e53f4b11b hashes, so they are not renamed.
UPPER = re.compile(r"^[A-Z][A-Z0-9_]*$")
ALLOWED_UPPER_KEYS = {"gb_grid"}
MAX_LINE = 140


def _src(name: str) -> str:
    return (PKG / f"{name}.py").read_text(encoding="utf-8")


def _tree(name: str) -> ast.Module:
    return ast.parse(_src(name))


def _enclosing(tree: ast.Module) -> dict[int, str]:
    """id(node) -> name of the function it sits in, or "<module>"."""
    out = {}

    def walk(node, fn):
        for child in ast.iter_child_nodes(node):
            here = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
            out[id(child)] = here
            walk(child, here)
    walk(tree, "<module>")
    return out


def _docstring_nodes(tree: ast.Module) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


# =============================================================================
# §1 — Python only
# =============================================================================
@pytest.mark.parametrize("name", MODULES + ["grid"])
def test_no_data_loaders(name):
    """No JSON/CSV/spreadsheet module, no file read, no data-file literal, outside the allowlist."""
    tree = _tree(name)
    where = _enclosing(tree)
    docs = _docstring_nodes(tree)
    problems = []
    for node in ast.walk(tree):
        fn = where.get(id(node), "<module>")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for m in mods:
                if m.split(".")[0] in DATA_MODULES and (name, fn) not in ALLOWED_IO:
                    problems.append(f"line {node.lineno}: imports {m} in {fn}()")
        elif isinstance(node, ast.Call):
            f = node.func
            called = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if called in READ_CALLS and (name, fn) not in ALLOWED_IO:
                problems.append(f"line {node.lineno}: calls {called}() in {fn}()")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
            if node.value.lower().endswith(DATA_SUFFIXES):
                problems.append(f"line {node.lineno}: data-file literal {node.value!r} in {fn}()")
    # a module-level constant may name the file its check reads
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if (name, node.targets[0].id) in ALLOWED_DATA_LITERALS:
                problems = [p for p in problems if f"line {node.lineno}:" not in p
                            and not (node.end_lineno and any(f"line {ln}:" in p for ln in range(node.lineno, node.end_lineno + 1)))]
    assert not problems, f"{name}.py reads data (LCA_STYLE.md §1):\n  " + "\n  ".join(problems)


def test_nothing_in_the_package_reads_a_cache():
    hits = [(p.name, m.group(0)) for p in PKG.glob("*.py")
            for m in re.finditer(r"\w+_cache\.json", p.read_text(encoding="utf-8"))]
    assert not hits, f"a module names a coefficient cache: {hits}"


# =============================================================================
# §2 — the module, top to bottom
# =============================================================================
@pytest.mark.parametrize("name", MODULES)
def test_docstring_states_source_and_functional_unit(name):
    doc = ast.get_docstring(_tree(name)) or ""
    assert len(doc) > 300, f"{name}.py: the docstring must say what, whose, and what is out"
    assert re.search(r"functional unit", doc, re.I), f"{name}.py: the docstring does not state the functional unit"
    assert re.search(r"et al\.|doi|NREL|T12-|Table|Carbon Intensity|NESO", doc), \
        f"{name}.py: the docstring cites no source"
    assert re.search(r"\b20\d\d\b", doc), f"{name}.py: the docstring gives no year"


@pytest.mark.parametrize("name", MODULES)
def test_sections_in_order(name):
    lines = _src(name).splitlines()
    heads = {}
    for i, ln in enumerate(lines[1:], start=2):
        if lines[i - 2].startswith("# ===") and ln.startswith("# "):
            title = ln[2:].split(" ")[0].rstrip("—-:")
            heads.setdefault(title, i)
    for want in ("Parameters", "Processes", "Activities"):
        assert want in heads, f"{name}.py has no '# {want}' section under a # === rule"
    assert heads["Parameters"] < heads["Processes"] < heads["Activities"], \
        f"{name}.py sections out of order: {heads}"
    tree = _tree(name)
    names = {n.targets[0].id for n in tree.body if isinstance(n, ast.Assign)
             and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    for want in ("processes", "flows", "activities"):
        assert want in names, f"{name}.py has no module-level {want}"
    assert "inventory" in funcs, f"{name}.py has no inventory()"


# =============================================================================
# §3 — the two tables
# =============================================================================
@pytest.mark.parametrize("name", MODULES)
def test_tables_are_pinned_and_explained(name):
    inv = build.load(name).inventory()
    problems = []
    for k, p in inv.processes.items():
        if not SNAKE.match(k) and not (name in ALLOWED_UPPER_KEYS and UPPER.match(k)):
            problems.append(f"process key {k!r} is not snake_case")
        if p.identity is None:
            problems.append(f"process {k!r} has no identity (run pin())")
        if p.query is None and (name, k) not in ALLOWED_NO_QUERY and p.database is None:
            problems.append(f"process {k!r} has no query (how was it found?)")
        if p.pick and not p.why:
            problems.append(f"process {k!r} takes search hit {p.pick} without a why")
    for k, f in inv.flows.items():
        if not SNAKE.match(k):
            problems.append(f"flow key {k!r} is not snake_case")
        if f.identity is None or len(f.identity) != 2 or not isinstance(f.identity[1], (tuple, list)):
            problems.append(f"flow {k!r} is not pinned as (name, (compartment, ...))")
    assert not problems, f"{name}.py tables (LCA_STYLE.md §3):\n  " + "\n  ".join(problems)


# =============================================================================
# §4 — activities and rows
# =============================================================================
@pytest.mark.parametrize("name", MODULES)
def test_activities_name_their_source_and_rows_have_notes(name):
    inv = build.load(name).inventory()
    tokens = MODULE_SOURCES[name]
    problems = []
    for a in inv.activities:
        if not a.comment or len(a.comment) < 40:
            problems.append(f"{a.code}: comment missing or too short to name its source")
        elif not any(t in a.comment or t in a.name for t in tokens):
            problems.append(f"{a.code}: comment names none of {tokens}")
        if a.scale != 1.0 and not a.scale_note:
            problems.append(f"{a.code}: scale {a.scale} without a scale_note")
        for r in list(a.technosphere) + list(a.biosphere):
            if len(r) != 4:
                problems.append(f"{a.code}: row {r!r} is not (key, amount, unit, note)")
                continue
            key, amount, unit, note = r
            if not isinstance(note, str) or not note.strip():
                problems.append(f"{a.code}: row {key!r} has no note")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                problems.append(f"{a.code}: row {key!r} amount {amount!r} is not a number")
    assert not problems, f"{name}.py activities (LCA_STYLE.md §4):\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("name", MODULES)
def test_codes_come_from_the_registry(name):
    tree = _tree(name)
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Activity":
            code = next((kw.value for kw in node.keywords if kw.arg == "code"), None)
            if code is None and node.args:
                code = node.args[0]
            if isinstance(code, ast.Constant):
                problems.append(f"line {node.lineno}: Activity(code={code.value!r}) is a literal, not registry.*")
    assert not problems, f"{name}.py:\n  " + "\n  ".join(problems)
    # and the registry is the only place a code string is spelled out
    for db, codes in registry.CODES_BY_DATABASE.items():
        for c in codes:
            assert _src(name).count(f'"{c}"') == 0 or name == "registry", \
                f"{name}.py spells out the code {c!r}; use registry"


# =============================================================================
# §2.3 — parameters are graded
# =============================================================================
def _is_numeric(node) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return _is_numeric(node.operand)
    return False


@pytest.mark.parametrize("name", MODULES)
def test_parameters_are_graded(name):
    """A module-level number, or a dict/tuple of numbers, says TRANSCRIBED, DERIVED
    or ASSUMED (or is a physical constant / unit conversion and says so) on its
    line or in the comment block above it. Arithmetic on graded names needs none."""
    lines = _src(name).splitlines()
    tree = _tree(name)
    problems = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        v = node.value
        literal = _is_numeric(v) \
            or (isinstance(v, ast.Dict) and v.values and all(_is_numeric(x) for x in v.values)) \
            or (isinstance(v, (ast.Tuple, ast.List)) and v.elts and all(_is_numeric(x) for x in v.elts))
        if not literal:
            continue
        lo = max(0, node.lineno - 4)
        block = "\n".join(lines[lo:node.end_lineno])
        if not GRADE.search(block):
            problems.append(f"line {node.lineno}: {node.targets[0].id} carries no grade")
    assert not problems, f"{name}.py parameters (LCA_STYLE.md §2.3):\n  " + "\n  ".join(problems)


# =============================================================================
# §5 — clear and concise
# =============================================================================
def _comment_lines(src: str):
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], tok.string


@pytest.mark.parametrize("name", MODULES + INFRASTRUCTURE)
def test_clear_and_concise(name):
    src = _src(name)
    problems = []
    for i, ln in enumerate(src.splitlines(), start=1):
        if len(ln) > MAX_LINE:
            problems.append(f"line {i}: {len(ln)} characters (max {MAX_LINE})")
        if re.search(r"\b(TODO|FIXME|XXX)\b(?!\.md)", ln):
            problems.append(f"line {i}: TODO/FIXME belongs in TODO.md")
    # commented-out code: a comment that parses as a statement (assignment,
    # import, def, call). Dropped source rows are tuples and are allowed.
    for i, c in _comment_lines(src):
        body = c.lstrip("#").strip()
        if not body or body.startswith(("---", "===", "noqa")):
            continue
        try:
            parsed = ast.parse(body)
        except SyntaxError:
            continue
        for stmt in parsed.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Return)) or \
                    (isinstance(stmt, ast.Assign) and isinstance(stmt.targets[0], ast.Name)
                     and not isinstance(stmt.value, ast.Constant)) or \
                    (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
                     and not isinstance(stmt.value.func, ast.Name)):
                problems.append(f"line {i}: commented-out code: {body[:60]!r}")
    assert not problems, f"{name}.py (LCA_STYLE.md §5):\n  " + "\n  ".join(problems)


# =============================================================================
# §1 — outside the package
# =============================================================================
def test_dc_config_holds_no_inventory():
    tree = ast.parse((ROOT / "dc_config.py").read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert not names & {"Activity", "Process", "Flow", "Inventory", "FG"}, \
        "dc_config.py builds inventory objects; they belong in optimiser_lca/"
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(m.startswith("optimiser_lca") for m in mods), \
                "dc_config.py imports an inventory at module level; study settings only"


def test_reader_notebook_builds_nothing():
    nb = ROOT / "2.tech_lca_foreground.ipynb"
    if not nb.exists():
        pytest.skip("no reader notebook")
    text = nb.read_text(encoding="utf-8")
    for bad in ("Activity(", "Database(", ".write(", "to_bw_dict("):
        assert bad not in text, f"the reader notebook contains {bad!r}; it must only read"


def test_data_dir_holds_evidence_only():
    data = ROOT / "optimisation" / "data"
    extra = {p.name for p in data.iterdir()} - EVIDENCE_FILES - EVIDENCE_DIRS
    assert not extra, f"optimisation/data/ holds {sorted(extra)}: inventory data belongs in optimiser_lca/*.py; " \
                      "a new source document goes on the EVIDENCE_FILES list with its reason"
