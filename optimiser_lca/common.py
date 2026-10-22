"""
The shape every inventory is written in, and the four verbs that act on it.
=============================================================================

An inventory module declares three tables and the verbs here do the rest:

    processes    {key: Process(...)}   ecoinvent activities it draws on
    flows        {key: Flow(...)}      biosphere (elementary) flows
    activities   [Activity(...), ...]  the foreground activities it writes

A ``Process`` carries both the *search* that found it and the *identity* that
builds it::

    "steel": Process(
        query="market for steel unalloyed GLO", pick=0,
        identity=("market for steel, unalloyed", "GLO", "steel, unalloyed"),
        why="generic unalloyed steel market; Hermesmann lists no grade",
    )

The query and pick are how a choice is made and changed: edit either, run
``show()`` to see the candidates, run ``pin()`` to record the identity. The
identity is how it is *built*: ``resolve()`` matches it exactly - name,
location and reference product - and refuses zero or several hits, so a
ranking shift between ecoinvent or bw2data versions is a loud refusal rather
than a silent swap. ``show()`` also refuses to mark a pick whose identity is
no longer among the search hits for its query.

Verbs:

    show(inv)        print each process's search neighbourhood with the chosen
                     row marked, then one table per activity
    pin(inv)         fill any missing identity from its search pick
    resolve(inv)     {key: Brightway activity} for processes and flows
    to_bw_dict(inv)  the dict ``bw2data.Database.write`` takes
    write(inv)       delete and rewrite the inventory's database
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Units an exchange may carry. A typo here fails the module's own check rather
# than Brightway's.
UNITS = {
    "kilogram", "cubic meter", "kilowatt hour", "megajoule", "unit", "meter",
    "kilometer", "square meter", "square meter-year", "tonne", "megawatt",
    "ton kilometer", "hour", "kilogram day",
    "megavolt ampere",      # transformer rating (stepup_transformers.TX_GRID)
}


# =============================================================================
# The three tables
# =============================================================================
@dataclass
class Process:
    """One ecoinvent activity.

    identity   (name, location) or (name, location, reference product).
               Reference product matters where ecoinvent has multi-output
               activities under one name and location.
    unit       optional extra filter, for activities that exist per kg and
               per unit under the same name.
    query/pick the search that found it, for show() and pin().
    why        the reason this one and not its neighbours.
    database   where to resolve it, when that is a foreground database rather
               than ecoinvent.
    """
    identity: tuple | None = None
    query: str | None = None
    pick: int = 0
    why: str = ""
    unit: str | None = None
    database: str | None = None


@dataclass
class Flow:
    """One biosphere flow: name and the categories tuple that fixes the
    compartment (the two "Water" flows differ only in categories)."""
    identity: tuple | None = None       # (name, (category, subcategory...))
    query: str | None = None
    pick: int = 0
    why: str = ""


@dataclass
class FG:
    """A link to another foreground activity, by registry code. ``database``
    is only needed when the target is in a different database."""
    code: str
    database: str | None = None


@dataclass
class Activity:
    code: str
    name: str
    reference_product: str
    unit: str
    location: str
    comment: str
    # (process key | FG, amount, unit, note)
    technosphere: list = field(default_factory=list)
    # (flow key, amount, unit, note)
    biosphere: list = field(default_factory=list)
    production_amount: float = 1.0
    # Applied to every exchange amount at write time. Lets a table stay as
    # printed in its source while a named correction is applied once.
    scale: float = 1.0
    scale_note: str = ""


@dataclass
class Inventory:
    name: str
    database: str
    processes: dict = field(default_factory=dict)
    flows: dict = field(default_factory=dict)
    activities: list = field(default_factory=list)
    # Optional: filled by the module when some exchanges can only be known
    # with Brightway open (e.g. a distance read out of an ecoinvent dataset).
    # Called by resolve() with the resolved {key: activity} dict.
    on_resolve: Callable | None = None


# =============================================================================
# Static checks - no Brightway needed
# =============================================================================
def check(inv: Inventory) -> str:
    """Every exchange names a known process/flow/code and a known unit; no
    duplicate codes; no key in both the process and the flow table; every
    process has an identity or a query to pin from."""
    problems = []
    codes = [a.code for a in inv.activities]
    dup = {c for c in codes if codes.count(c) > 1}
    if dup:
        problems.append(f"duplicate codes {sorted(dup)}")
    # resolve() returns one {key: node} dict for both tables, so a key in both
    # would silently link a technosphere row to a biosphere flow (or vice versa).
    shared = set(inv.processes) & set(inv.flows)
    if shared:
        problems.append(f"keys in both processes and flows {sorted(shared)}")
    for k, p in inv.processes.items():
        if p.identity is None and p.query is None:
            problems.append(f"process {k!r} has neither identity nor query")
        if p.identity is not None and len(p.identity) not in (2, 3):
            problems.append(f"process {k!r}: identity must be (name, location[, product])")
    for k, f in inv.flows.items():
        if f.identity is None and f.query is None:
            problems.append(f"flow {k!r} has neither identity nor query")
    for a in inv.activities:
        if a.unit not in UNITS:
            problems.append(f"{a.code}: unknown unit {a.unit!r}")
        for key, amount, unit, _note in a.technosphere:
            if unit not in UNITS:
                problems.append(f"{a.code}: unknown unit {unit!r} on {key!r}")
            if isinstance(key, FG):
                if key.database is None and key.code not in codes:
                    problems.append(f"{a.code}: links to unknown code {key.code!r}")
            elif key not in inv.processes:
                problems.append(f"{a.code}: unknown process key {key!r}")
            if not isinstance(amount, (int, float)):
                problems.append(f"{a.code}: non-numeric amount for {key!r}")
        for key, amount, unit, _note in a.biosphere:
            if key not in inv.flows:
                problems.append(f"{a.code}: unknown flow key {key!r}")
            if unit not in UNITS:
                problems.append(f"{a.code}: unknown unit {unit!r} on flow {key!r}")
    if problems:
        raise AssertionError(f"{inv.name}:\n  " + "\n  ".join(problems))
    return (f"OK - {inv.name}: {len(inv.activities)} activities, "
            f"{len(inv.processes)} processes, {len(inv.flows)} flows")


# =============================================================================
# Brightway-backed verbs
# =============================================================================
def _handles():
    import lca_helpers as H
    if H.ei is None:
        H.setup_brightway()
    return H


def search_hits(query: str, database, n: int = 100) -> list:
    return list(database.search(query))[:n]


def _same(act, identity) -> bool:
    if act.get("name") != identity[0] or act.get("location") != identity[1]:
        return False
    if len(identity) == 3 and act.get("reference product") != identity[2]:
        return False
    return True


def _same_flow(flow, identity) -> bool:
    return (flow.get("name") == identity[0]
            and tuple(flow.get("categories") or ()) == tuple(identity[1]))


def resolve_process(p: Process):
    H = _handles()
    if p.identity is None:
        raise ValueError(f"process has no identity - run pin() first ({p.query!r})")
    return H.resolve_exact(*p.identity, unit=p.unit, database=p.database)


def resolve_flow(f: Flow):
    H = _handles()
    if f.identity is None:
        raise ValueError(f"flow has no identity - run pin() first ({f.query!r})")
    return H.resolve_flow(f.identity[0], tuple(f.identity[1]))


def pin(inv: Inventory, verbose: bool = True) -> Inventory:
    """Fill every missing identity from its search pick, and say so."""
    H = _handles()
    for k, p in inv.processes.items():
        if p.identity is None:
            a = search_hits(p.query, H.ei)[p.pick]
            p.identity = (a["name"], a["location"], a.get("reference product"))
            if verbose:
                print(f"pinned {k!r}: {p.identity}")
    for k, f in inv.flows.items():
        if f.identity is None:
            x = search_hits(f.query, H.bio)[f.pick]
            f.identity = (x["name"], tuple(x["categories"]))
            if verbose:
                print(f"pinned flow {k!r}: {f.identity}")
    return inv


def resolve(inv: Inventory, strict_search: bool = True) -> dict:
    """``{key: activity}`` for every process and flow, by exact identity.

    With ``strict_search`` the identity must also be among the first 100
    search hits for its query, so a query that no longer finds what it is
    pinned to is noticed.
    """
    H = _handles()
    check(inv)
    out = {}
    for k, p in inv.processes.items():
        act = resolve_process(p)
        if strict_search and p.query:
            hits = search_hits(p.query, H.ei)
            if not any(_same(h, p.identity) for h in hits):
                raise ValueError(
                    f"{inv.name}: process {k!r} is pinned to {p.identity} but that is "
                    f"not among the search hits for {p.query!r}. The query or the "
                    "identity has moved; look at show() and re-pin.")
        out[k] = act
    for k, f in inv.flows.items():
        out[k] = resolve_flow(f)
    if inv.on_resolve is not None:
        inv.on_resolve(out)
    return out


def show(inv: Inventory, n_hits: int = 8, candidates: bool = True):
    """Print the inventory the way the notebook always has: for each process
    the search neighbourhood with the chosen row marked, then each activity
    as a table. Returns {code: DataFrame}."""
    import pandas as pd
    H = _handles()
    resolved = resolve(inv, strict_search=False)
    if candidates:
        for k, p in inv.processes.items():
            print("\n" + "=" * 96)
            print(f"{k}: {p.query or '(no query - pinned by identity)'}")
            if p.why:
                print(f"  why: {p.why}")
            hits = search_hits(p.query, H.ei, n_hits) if p.query else []
            found = False
            for i, a in enumerate(hits):
                mark = "->" if _same(a, p.identity) else "  "
                found = found or mark == "->"
                print(f"  {mark}{i:>3} | {a.get('name')} | {a.get('reference product')} "
                      f"| {a.get('unit')} | {a.get('location')}")
            if p.query and not found:
                deeper = search_hits(p.query, H.ei)
                rank = next((i for i, a in enumerate(deeper) if _same(a, p.identity)), None)
                if rank is None:
                    print(f"  !! pinned identity is not among the first {len(deeper)} hits "
                          f"for this query: {p.identity} — re-pin or change the query")
                else:
                    print(f"  ->{rank:>3} | {p.identity[0]} | {p.identity[2] if len(p.identity) > 2 else ''} "
                          f"| {p.identity[1]}   (rank {rank}, beyond the {n_hits} shown)")
        for k, f in inv.flows.items():
            print("\n" + "=" * 96)
            print(f"flow {k}: {f.query or '(pinned by identity)'}  ->  {f.identity}")
    tables = {}
    for a in inv.activities:
        rows = []
        for key, amount, unit, note in a.technosphere:
            if isinstance(key, FG):
                rows.append({"key": f"FG:{key.code}", "amount": amount * a.scale, "unit": unit,
                             "input": key.code, "location": key.database or inv.database,
                             "note": note})
            else:
                act = resolved[key]
                rows.append({"key": key, "amount": amount * a.scale, "unit": unit,
                             "input": act.get("name"), "location": act.get("location"),
                             "note": note})
        for key, amount, unit, note in a.biosphere:
            fl = resolved[key]
            rows.append({"key": f"bio:{key}", "amount": amount * a.scale, "unit": unit,
                         "input": fl.get("name"), "location": str(fl.get("categories")),
                         "note": note})
        df = pd.DataFrame(rows, columns=["key", "amount", "unit", "input", "location", "note"])
        tables[a.code] = df
        print("\n" + "-" * 96)
        print(f"{a.code}: {a.name}  [{a.production_amount:g} {a.unit}, {a.location}]"
              + (f"  x{a.scale:.9g} {a.scale_note}" if a.scale != 1.0 else ""))
        with pd.option_context("display.width", 200, "display.max_colwidth", 60,
                               "display.max_rows", 200):
            print(df.to_string(index=False))
    return tables


def to_bw_dict(inv: Inventory, resolved: dict | None = None) -> dict:
    """The ``{(database, code): {...}}`` payload ``Database.write`` takes."""
    resolved = resolve(inv) if resolved is None else resolved
    db = inv.database
    data = {}
    for a in inv.activities:
        key = (db, a.code)
        exchanges = [{"input": key, "amount": a.production_amount, "unit": a.unit,
                      "type": "production", "name": a.name}]
        for pkey, amount, unit, note in a.technosphere:
            if isinstance(pkey, FG):
                exc = {"input": (pkey.database or db, pkey.code), "amount": amount * a.scale,
                       "unit": unit, "type": "technosphere", "comment": note}
            else:
                act = resolved[pkey]
                exc = {"input": act.key, "amount": amount * a.scale, "unit": unit,
                       "type": "technosphere", "name": act.get("name"), "comment": note}
            if a.scale != 1.0:
                exc["comment"] = f"{note} (as printed: {amount:g} {unit})"
            exchanges.append(exc)
        for fkey, amount, unit, note in a.biosphere:
            fl = resolved[fkey]
            exc = {"input": fl.key, "amount": amount * a.scale, "unit": unit,
                   "type": "biosphere", "name": fl.get("name"), "comment": note}
            if a.scale != 1.0:
                exc["comment"] = f"{note} (as printed: {amount:g} {unit})"
            exchanges.append(exc)
        data[key] = {
            "name": a.name, "reference product": a.reference_product,
            "unit": a.unit, "location": a.location, "database": db, "code": a.code,
            "comment": a.comment, "exchanges": exchanges,
        }
    return data


def write(inv: Inventory, resolved: dict | None = None, verbose: bool = True):
    """Delete and rewrite the inventory's database. Prints every activity."""
    import bw2data as bd
    data = to_bw_dict(inv, resolved)
    if inv.database in bd.databases:
        bd.Database(inv.database).delete(warn=False)
    bd.Database(inv.database).write(data)
    if verbose:
        print(f"\n{inv.database!r} written with {len(data)} activities.")
        for a in inv.activities:
            act = bd.get_activity((inv.database, a.code))
            print("=" * 70)
            print(a.code, "->", act)
            for exc in act.exchanges():
                print(f"  {exc['type']:<14} {exc.amount:>14.6g}  {exc.get('unit', ''):<15}  "
                      f"{exc.input.get('name', exc.input)}")
    return data
