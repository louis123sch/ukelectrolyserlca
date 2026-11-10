"""
How each LP coefficient is made, recorded by the code that makes it.
=============================================================================

The LCA map used to restate every coefficient's arithmetic by hand in
``scripts/build_lca_map.py`` - a second copy of the model that a checker then
had to hold to the first. This module removes the copy. The modules that derive
a number wrap it in ``step()`` where they compute it::

    from optimisation import trace as T

    capital = T.step("onshore_wind.capital", eco * (1.0 + parts), "kg CO2e per MW",
                     "Turbine capital grossed up for the parts a 35-year life needs",
                     uses=["onshore_wind.ecoinvent_capital", "onshore_wind.parts"],
                     inputs={"parts": parts}, grade="assumed")

``step`` returns ``value`` unchanged. With no recording open it does nothing
else, so the optimiser pays nothing for it. Inside ``with recording() as rec``
(the map's builder) each call is kept as a ``Step``: its value, what it used,
the file and line, and the expression that computed it, read from the source.
The map is drawn from those records, so it shows the numbers the model used
and the code that made them, and cannot drift from either.

``uses`` names what a step is made from: another step's key, or a Brightway
activity (``activity(db, code)``, ``ecoinvent(name, location, product)``). A
step whose value *is* one unit of an activity's score - a pinned figure, a
cached decomposition - says so with ``scores=``; the map's builder rescores it
and reports any drift.

Nothing here needs Brightway.
"""
from __future__ import annotations

import ast
import contextvars
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADES = ("transcribed", "derived", "assumed", "proxy")


# =============================================================================
# References to Brightway activities
# =============================================================================
def activity(database: str, code: str) -> dict:
    """A foreground (or any) Brightway activity, by key."""
    return {"database": database, "code": code}


def ecoinvent(name: str, location: str, product: str | None = None,
              database: str | None = None) -> dict:
    """An activity by the identity the inventories pin it with: ecoinvent's,
    unless ``database`` names a foreground one."""
    ref = {"ecoinvent": [name, location, product]}
    if database:
        ref["database"] = database
    return ref


# =============================================================================
# The record
# =============================================================================
@dataclass
class Step:
    key: str
    value: float | None
    unit: str
    title: str
    uses: list = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    grade: str = "derived"
    source: str = ""
    note: str = ""
    scores: dict | None = None
    factor: float = 1.0
    side: str = ""           # "cost" for a pound figure; "" is the carbon side
    cites: list = field(default_factory=list)   # [{"source": register key, "at": table / page}]
    where: str = ""          # "optimisation/renewables.py:412"
    function: str = ""       # "apply_case"
    code: str = ""           # the expression that computed the value
    # The value of each name in ``code`` when it ran ({"row['x']": 1.2}): what
    # lets the workbooks (scripts/build_workbooks.py) link each name to the
    # step it came from and write the expression as an Excel formula.
    leaves: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, "", [], {})}


class Recorder:
    """The steps one recording saw, by key. A key recorded twice with two
    different values is kept as a conflict rather than overwritten: it means
    two different numbers went by one name, which the map must not hide."""

    def __init__(self):
        self.steps: dict[str, Step] = {}
        self.conflicts: dict[str, list[Step]] = {}

    def add(self, s: Step):
        old = self.steps.get(s.key)
        if old is not None and not _same(old.value, s.value):
            self.conflicts.setdefault(s.key, [old]).append(s)
            return
        self.steps[s.key] = s


_CURRENT: contextvars.ContextVar[Recorder | None] = contextvars.ContextVar("trace", default=None)


@contextmanager
def recording():
    """Record every ``step`` called inside the block."""
    rec = Recorder()
    token = _CURRENT.set(rec)
    try:
        yield rec
    finally:
        _CURRENT.reset(token)


@contextmanager
def quiet():
    """Record nothing inside the block. For a function that builds a table of
    every case from the one-case function that records: the table's other
    cases would otherwise reach the record under the same keys."""
    token = _CURRENT.set(None)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def active() -> bool:
    return _CURRENT.get() is not None


# A sweep's "push": one recorded number times a factor, through the real code.
# (key, factor, hits) - hits records, per call under that key, whether the value
# was a number that could be scaled.
_PUSH: contextvars.ContextVar[tuple | None] = contextvars.ContextVar("trace_push", default=None)


@contextmanager
def pushed(key: str, factor: float):
    """Inside the block, every ``step`` recorded under ``key`` returns its value
    times ``factor`` - so everything the code makes from it moves with it. Yields
    the list of hits: empty if no step by that key ran, False where the value was
    not a number (a flag, a label, a table). Used by the input screen
    (``scripts/screen_inputs.py``) and by a sweep's ``push`` knob
    (``optimisation/sensitivity.py``). A step the code only records, going on
    with another figure, moves nothing when pushed."""
    hits: list[bool] = []
    token = _PUSH.set((key, float(factor), hits))
    try:
        yield hits
    finally:
        _PUSH.reset(token)


def _scaled(v, f):
    """``v`` times ``f`` for a number or an array of numbers; None otherwise."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        import numpy as np
    except ImportError:                                         # pragma: no cover
        np = None
    if isinstance(v, (int, float)) or (np is not None and isinstance(v, (np.integer, np.floating))):
        return v * f
    if np is not None and isinstance(v, np.ndarray) and np.issubdtype(v.dtype, np.number):
        return v * f
    try:
        import pandas as pd
        if isinstance(v, pd.Series) and pd.api.types.is_numeric_dtype(v):
            return v * f
    except ImportError:                                         # pragma: no cover
        pass
    return None


def step(key: str, value, unit: str, title: str, *, uses=(), inputs: dict | None = None,
         grade: str = "derived", source: str = "", note: str = "", scores: dict | None = None,
         factor: float = 1.0, side: str = "", cites=(), depth: int = 0):
    """Return ``value``; while recording, keep how it was made.

    key      a unique, dotted name: ``"<owner>.<what>"``
    unit     the value's unit, in words
    title    one line saying what the number is
    uses     the step keys and activity references it is computed from
    inputs   the constants it is computed with, by name, as plain numbers
    grade    transcribed / derived / assumed / proxy (SOURCES.md)
    scores   an activity this value is the score of, times ``factor``
    side     "cost" for a pound figure (the cost map's); "" for the carbon side
    cites    where the number was read: ``(register key, "Table 3, p.6")``
             pairs, keys of ``optimisation.source_register.SOURCES``
    depth    frames to skip when a module wraps ``step`` in its own helper, so
             the record points at the helper's caller
    """
    push = _PUSH.get()
    if push is not None and key == push[0]:
        scaled = _scaled(value, push[1])
        push[2].append(scaled is not None)
        if scaled is not None:
            value = scaled
    rec = _CURRENT.get()
    if rec is None:
        return value
    if grade not in GRADES:
        raise ValueError(f"trace step {key!r}: grade {grade!r} is not one of {GRADES}")
    frame = sys._getframe(1 + depth)
    path, line = frame.f_code.co_filename, frame.f_lineno
    code = _value_source(path, line)
    rec.add(Step(key=key, value=_num(value), unit=unit, title=title, uses=list(uses),
                 inputs={k: _num(v) if not isinstance(v, str) else v for k, v in (inputs or {}).items()},
                 grade=grade, source=source, note=note, scores=scores, factor=float(factor),
                 side=side, cites=[{"source": c[0], "at": c[1] if len(c) > 1 else ""} for c in cites],
                 where=f"{_rel(path)}:{line}", function=frame.f_code.co_name,
                 code=code, leaves=_leaf_values(code, frame)))
    return value


def cost(key: str, value, unit: str, title: str, *, depth: int = 0, **kw):
    """``step`` on the cost side: a pound figure, or a number only the cost
    objective uses (a discount rate, a cost life). Kept out of the LCA map and
    drawn on the cost map (``scripts/build_cost_map.py``)."""
    return step(key, value, unit, title, side="cost", depth=depth + 1, **kw)


# =============================================================================
# Helpers
# =============================================================================
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def _rel(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).name


_SOURCES: dict[str, tuple[str, list]] = {}


def _value_source(path: str, line: int) -> str:
    """The source of the ``value`` argument of the ``step(...)`` call at ``line``.

    Read from the file, not from a hand-written formula, so the map shows the
    expression the model evaluates. Falls back to "" for anything unreadable.
    """
    try:
        if path not in _SOURCES:
            src = Path(path).read_text(encoding="utf-8")
            calls = [n for n in ast.walk(ast.parse(src))
                     if isinstance(n, ast.Call) and _is_step(n.func) and len(n.args) >= 2]
            _SOURCES[path] = (src, calls)
        src, calls = _SOURCES[path]
        hits = [c for c in calls if c.lineno <= line <= c.end_lineno]
        if not hits:
            return ""
        call = min(hits, key=lambda c: c.end_lineno - c.lineno)
        return " ".join((ast.get_source_segment(src, call.args[1]) or "").split())
    except Exception:                                   # noqa: BLE001
        return ""


_LEAVES: dict[str, list] = {}


def leaf_nodes(expr) -> list:
    """The names an expression reads: bare names, attributes (``ely.LIFE``) and
    subscripts by a constant (``row["x"]``), outermost first. Calls and
    arithmetic are walked into, never evaluated."""
    out = []

    def visit(n):
        if isinstance(n, (ast.Name, ast.Attribute)) or (
                isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)):
            out.append(n)
            return
        for c in ast.iter_child_nodes(n):
            visit(c)
    visit(expr)
    return out


def _leaf_values(code: str, frame) -> dict:
    """The numeric value of each name ``code`` reads, in the frame that ran it.

    Only names, attributes and constant subscripts are evaluated - never a call -
    so reading them cannot change anything. Anything that is not one number (an
    array, a table, a string) is left out."""
    if not code:
        return {}
    try:
        if code not in _LEAVES:
            tree = ast.parse(code, mode="eval")
            _LEAVES[code] = [(ast.unparse(n), compile(ast.Expression(n), "<leaf>", "eval"))
                             for n in leaf_nodes(tree.body)]
        out = {}
        for src, compiled in _LEAVES[code]:
            try:
                v = eval(compiled, frame.f_globals, frame.f_locals)   # noqa: S307 - names only
                if isinstance(v, (bool, str)):
                    continue
                out[src] = float(v)
            except Exception:                                         # noqa: BLE001
                pass
        return out
    except Exception:                                                 # noqa: BLE001
        return {}


def _is_step(func) -> bool:
    return (isinstance(func, ast.Attribute) and func.attr in ("step", "cost")) or \
           (isinstance(func, ast.Name) and func.id in ("step", "cost"))
