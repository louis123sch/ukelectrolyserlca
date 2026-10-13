"""
Shared Brightway helpers — the project session, exact-identity lookup, and
the LCA calls the inventory and coefficient modules make.
=============================================================================

Settings come from ``dc_config``; inventories live in ``optimiser_lca``.
Typical use::

    import lca_helpers as H
    ei, bio, fg_db, method = H.setup_brightway()

After setup, helpers can be called with or without explicit Brightway handles
(they fall back to the module-level handles populated by setup_brightway()).

What is here: ``setup_brightway`` and the handles; ``resolve_exact`` /
``resolve_flow`` (the one way anything on the build path finds an ecoinvent
activity — by name, location and reference product, refusing zero or several
hits); ``show_candidates`` / ``pick_candidate`` for *exploration*; and the
scoring calls ``run_lca_score`` / ``run_non_electricity_lca``.

What is not: the grid tables (``optimiser_lca.grid``), the foreground codes
(``optimiser_lca.registry``), and the Renewables.ninja client
(``optimisation.profiles``).
"""

from __future__ import annotations

import uuid

import bw2calc as bc
import bw2data as bd
import bw2io as bi

import dc_config as cfg


# =============================================================================
# Module-level Brightway handles, populated by setup_brightway()
# =============================================================================
ei = None       # ecoinvent database
bio = None      # biosphere database
fg_db = None    # hydrogen foreground database (None until built)
method = None   # the GWP100 method tuple _select_gwp_method picks


# =============================================================================
# Brightway project setup
# =============================================================================
def find_database_name(must_contain, prefer=None):
    """Find a Brightway database name containing all the given substrings."""
    names = [str(x) for x in bd.databases]
    must_contain_l = [s.lower() for s in must_contain]
    matches = [n for n in names if all(s in n.lower() for s in must_contain_l)]
    if prefer:
        pref_l = prefer.lower()
        preferred = [m for m in matches if pref_l in m.lower()]
        if preferred:
            return preferred[0]
    if not matches:
        raise ValueError(f"No database found containing: {must_contain}. Available: {names}")
    return matches[0]


def _select_gwp_method():
    """Pick IPCC 2021 GWP100 if available, else any IPCC GWP/climate-change method.

    Note: with ecoinvent 3.9.1's bundled methods the first GWP100 match in
    ``bd.methods`` order is the "no LT" (no long-term emissions) variant, and
    that is what this returns. ``optimiser_lca.grid`` scores the grid with it,
    so every grid series on disk is on that basis; the coefficient modules in
    ``optimisation/`` pick the with-LT variant themselves. Registered as a known
    inconsistency - changing this here would make every grid series stale.
    """
    gwp_methods = [
        m for m in bd.methods
        if "IPCC" in str(m) and ("GWP" in str(m) or "climate change" in str(m).lower())
    ]
    preferred = [
        m for m in gwp_methods
        if "2021" in str(m) and ("GWP100" in str(m).replace(" ", "") or "GWP 100" in str(m))
    ]
    if not gwp_methods:
        raise ValueError("No IPCC GWP/climate change method found in this Brightway project.")
    return preferred[0] if preferred else gwp_methods[0]


def setup_brightway():
    """Set the active project, find ecoinvent + biosphere + foreground + GWP method.

    Populates module-level globals ``ei``, ``bio``, ``fg_db``, ``method`` and
    returns them in that order. Safe to call from any notebook or module.
    """
    global ei, bio, fg_db, method
    from optimiser_lca import registry

    bd.projects.set_current(cfg.PROJECT_NAME)
    print("Current Brightway project:", bd.projects.current)

    if cfg.RUN_IMPORT_ECOINVENT:
        from getpass import getpass
        username = input("ecoinvent username: ")
        password = getpass("ecoinvent password: ")
        bi.import_ecoinvent_release(
            version=cfg.ECOINVENT_VERSION,
            system_model=cfg.SYSTEM_MODEL,
            username=username,
            password=password,
        )

    ei_name = cfg.ECOINVENT_DB if cfg.ECOINVENT_DB in bd.databases else \
        find_database_name(["ecoinvent", cfg.SYSTEM_MODEL])
    bio_name = find_database_name(["biosphere"])

    ei = bd.Database(ei_name)
    bio = bd.Database(bio_name)
    print("Using ecoinvent database:", ei_name)
    print("Using biosphere database:", bio_name)

    if registry.HYDROGEN_DB in bd.databases:
        fg_db = bd.Database(registry.HYDROGEN_DB)
        print("Using foreground database:", registry.HYDROGEN_DB)
    else:
        fg_db = None
        print(f"Foreground database {registry.HYDROGEN_DB!r} not built yet: "
              "run `python -m optimiser_lca.build`.")

    method = _select_gwp_method()
    print("Using LCIA method:", method)

    return ei, bio, fg_db, method


def refresh_foreground():
    """Reload the hydrogen foreground handle after writing/recreating it."""
    global fg_db
    from optimiser_lca import registry
    fg_db = bd.Database(registry.HYDROGEN_DB)
    return fg_db


def ecoinvent_name() -> str:
    """The ecoinvent database name, without needing setup_brightway() first."""
    return ei.name if ei is not None else cfg.ECOINVENT_DB


# =============================================================================
# Exact-identity lookup — the only way the build path finds an activity
# =============================================================================
def resolve_exact(name, location, product=None, unit=None, database=None):
    """The one ecoinvent activity with this name, location and (if given)
    reference product. Refuses zero or several matches.

    Name + location is not a unique key: ecoinvent has multi-output activities
    (``sulfuric acid production`` [RoW] exists twice, producing sulfuric acid
    and producing steam), so pass ``product`` wherever the source records it.
    ``unit`` separates the few activities that exist per kg and per unit.
    """
    from bw2data.errors import MultipleResults, UnknownObject
    kwargs = {"database": database or ecoinvent_name(), "name": name, "location": location}
    if product is not None:
        kwargs["product"] = product
    if unit is not None:
        kwargs["unit"] = unit
    try:
        return bd.get_node(**kwargs)
    except UnknownObject:
        raise ValueError(f"No activity matches {kwargs}. Check the spelling with "
                         "show_candidates().") from None
    except MultipleResults as e:
        raise ValueError(f"{e}: {kwargs} is not unique — give the reference product "
                         "(and unit if needed).") from None


def resolve_flow(name, categories, database=None):
    """The one biosphere flow with this name and categories tuple."""
    from bw2data.errors import MultipleResults, UnknownObject
    kwargs = {"database": database or (bio.name if bio is not None else
                                        find_database_name(["biosphere"])),
              "name": name, "categories": tuple(categories)}
    try:
        return bd.get_node(**kwargs)
    except UnknownObject:
        raise ValueError(f"No biosphere flow matches {kwargs}.") from None
    except MultipleResults as e:
        raise ValueError(f"{e}: {kwargs} is not unique.") from None


def get_exact_activities(identities, database=None):
    """``{key: (name, location, reference product)}`` -> ``{key: activity}``,
    every identity resolved exactly."""
    return {k: resolve_exact(*v, database=database) for k, v in identities.items()}


# =============================================================================
# Exploration helpers — search by rank, for looking, never for building
# =============================================================================
def show_candidates(query, database=None, max_results=100):
    """Print and return the first ``max_results`` ecoinvent search hits for ``query``."""
    database = database or ei
    results = list(database.search(query))[:max_results]
    for i, act in enumerate(results):
        print(
            f"  {i:>3} | name: {act.get('name')}"
            f" | ref: {act.get('reference product')}"
            f" | unit: {act.get('unit')}"
            f" | loc: {act.get('location')}"
        )
    return results


def pick_candidate(query, index=0, database=None, max_results=100):
    """Print candidates and return the one at ``index`` (raising if missing).

    For exploration. Once chosen, record the activity's identity in the
    inventory module (``Process(identity=...)``) - nothing on the build path
    depends on search order.
    """
    database = database or ei
    results = show_candidates(query, database=database, max_results=max_results)
    if not results:
        raise ValueError(f"No candidates found for query: {query!r}")
    picked = results[index]
    print(f"\n  → Selected [{index}]: {picked.get('name')} | {picked.get('location')}")
    print(f"     identity=({picked.get('name')!r}, {picked.get('location')!r}, "
          f"{picked.get('reference product')!r})")
    return picked


def show_biosphere_candidates(query, max_results=100):
    results = list(bio.search(query))[:max_results]
    for i, flow in enumerate(results):
        print(
            f"  {i:>3} | name: {flow.get('name')}"
            f" | unit: {flow.get('unit')}"
            f" | categories: {flow.get('categories')}"
        )
    return results


# =============================================================================
# LCA core helpers
# =============================================================================
def is_any_electricity_exchange(exc):
    """True for direct technosphere kWh exchanges whose input is electricity."""
    if exc["type"] != "technosphere":
        return False
    inp = exc.input
    name = (inp.get("name") or "").lower()
    ref = (inp.get("reference product") or "").lower()
    unit = (inp.get("unit") or exc.get("unit") or "").lower()
    return unit == "kilowatt hour" and ("electricity" in name or "electricity" in ref)


def run_lca_score(activity, method_=None, amount=1.0):
    method_ = method_ or method
    try:
        fu, data_objs, _ = bd.prepare_lca_inputs({activity: amount}, method=method_)
        lca = bc.LCA(demand=fu, data_objs=data_objs)
    except Exception:
        lca = bc.LCA({activity: amount}, method_)
    lca.lci()
    lca.lcia()
    return float(lca.score)


def _new_temp_activity(code_prefix, activity, fg_database=None):
    fg_database = fg_database or fg_db
    temp_code = f"_tmp_{code_prefix}_{activity['code']}_{uuid.uuid4().hex[:8]}"[:240]
    for old in [a for a in fg_database if a.get("code") == temp_code]:
        old.delete()
    tmp = fg_database.new_activity(
        code=temp_code,
        name=f"[TEMP {code_prefix}] {activity['name']}",
        unit=activity.get("unit", "kilogram"),
        location=activity.get("location", "GLO"),
    )
    tmp.save()
    return tmp


def run_non_electricity_lca(activity, method_=None, fg_database=None):
    """LCA of ``activity`` with direct electricity exchanges removed."""
    method_ = method_ or method
    tmp = _new_temp_activity("nonelec", activity, fg_database)
    removed_kwh = 0.0
    removed_count = 0
    try:
        for exc in list(activity.exchanges()):
            if exc["type"] == "production":
                new_input = tmp
            elif is_any_electricity_exchange(exc):
                removed_kwh += float(exc["amount"])
                removed_count += 1
                continue
            else:
                new_input = exc.input
            tmp.new_exchange(
                input=new_input, amount=exc["amount"], type=exc["type"],
                unit=exc.get("unit", ""), comment=exc.get("comment", ""),
            ).save()
        score = run_lca_score(tmp, method_, amount=1.0)
    finally:
        try:
            tmp.delete()
        except Exception:
            pass
    return score, removed_kwh, removed_count


def calculate_source_lca_scores(activities, method_=None):
    """``{key: activity}`` -> ``{key: kg CO2e per unit}``, one LCA each, printed."""
    method_ = method_ or method
    scores = {}
    print("Electricity source scores, one-off Brightway LCAs")
    print("------------------------------------------------")
    for tech_key, act in activities.items():
        try:
            score = run_lca_score(act, method_, amount=1.0)
            scores[tech_key] = score
            print(f"  {tech_key:<18} {score:>12.6f} kg CO2eq/kWh | "
                  f"{act.get('name')} [{act.get('location')}]")
        except Exception as e:
            print(f"  ⚠ {tech_key:<18} failed ({type(e).__name__}: {e})")
    return scores
