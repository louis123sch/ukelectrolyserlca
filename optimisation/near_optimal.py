"""How much the lowest-carbon design can move without giving up more than a little carbon.

The supervisor's ask of 23 Nov 2026: the range of battery and hydrogen sizes within 1 % of the
best carbon. The frontier reports one design at its lowest-carbon end; other designs may come
almost as close with quite different kit (DeCarolis, 2011, "modelling to generate alternatives";
Neumann and Brown, 2021). This finds, for each size asked about, the smallest and largest value
any design can have while its carbon stays within ``slack`` of the minimum:

1. minimise carbon: G*, the study's lowest-carbon total (constants included, as reported);
2. hold carbon at or below G* x (1 + slack);
3. for each size, minimise it and maximise it in turn under that limit, recording every size,
   cost and carbon of each solve, and the cheapest design under the limit as well.

Carbon is the reported total, the data centre's own building included (``dc_model.totals``), so
the slack is a share of what a reader sees. Cost is free inside the band: a design at either end
of a range may cost a great deal more than the lowest-carbon one, and each row says how much.
"""
from __future__ import annotations

import numpy as np

from optimisation import dc_model as M

# The sizes the range is asked for: the battery and the hydrogen chain.
DEFAULT_VARS = ("cap_batt_e", "cap_batt_p", "cap_ely", "cap_tank", "cap_fc")
# Every size, recorded on every row so a reader sees what replaced what.
ALL_SIZES = ("cap_wind", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely", "cap_tank",
             "cap_fc", "cap_ge", "cap_grid")


def _row(tag, V, obj) -> dict:
    tot = M.totals(obj)
    row = {"solve": tag, "cost_GBP_per_year": tot["cost_GBP_per_year"],
           "gwp_kgco2e_per_year": tot["gwp_kgco2e_per_year"]}
    row.update({k: float(V[k].solution) for k in ALL_SIZES})
    return row


def ranges(series, assets, tech, *, slack: float = 0.01, variables=DEFAULT_VARS,
           mip_rel_gap: float | None = None, unserved_fraction: float = 0.0, progress=None) -> dict:
    """The lowest-carbon design and, for each of ``variables`` its asset allows, the smallest and
    largest value within ``slack`` of the lowest carbon. Returns ``{"anchor", "limit_kgco2e_per_year",
    "rows", "ranges"}``; ``rows`` holds every solve."""
    if not 0.0 <= slack < 1.0:
        raise ValueError(f"slack must be in [0, 1), got {slack!r}")
    kw = {} if mip_rel_gap is None else {"mip_rel_gap": float(mip_rel_gap)}

    def say(t):
        if progress:
            progress(t)

    # 1. The lowest carbon, then the cheapest design at it (the frontier's own lexicographic anchor).
    say("min carbon")
    m, V, obj = M.build_model(series, assets, tech, objective="gwp", unserved_fraction=unserved_fraction)
    M.solve(m, **kw)
    g_star = M.totals(obj)["gwp_kgco2e_per_year"]
    say("min carbon, cheapest")
    m, V, obj = M.build_model(series, assets, tech, objective="cost", gwp_limit=g_star * (1 + 1e-6),
                              unserved_fraction=unserved_fraction)
    M.solve(m, **kw)
    anchor = _row("lowest carbon", V, obj)

    # 2-3. One model under the carbon limit; only its objective changes between solves.
    limit = g_star * (1.0 + slack)
    m, V, obj = M.build_model(series, assets, tech, objective="cost", gwp_limit=limit,
                              unserved_fraction=unserved_fraction)
    say(f"cheapest within {slack:.1%}")
    M.solve(m, **kw)
    rows = [anchor, _row("cheapest within the limit", V, obj)]
    out = {}
    for var in variables:
        if float(V[var].upper.max()) <= 0.0:          # the asset is not allowed here
            continue
        ends = {}
        for sense, sign in (("min", 1.0), ("max", -1.0)):
            say(f"{sense} {var}")
            m.add_objective(sign * V[var], overwrite=True)
            M.solve(m, **kw)
            r = _row(f"{sense} {var}", V, obj)
            rows.append(r)
            ends[sense] = r[var]
        out[var] = {"lowest_carbon": anchor[var], "min": ends["min"], "max": ends["max"]}
    for r in rows:
        if r["gwp_kgco2e_per_year"] > limit * (1 + 1e-6) + 1e-6:
            raise AssertionError(f"{r['solve']}: carbon {r['gwp_kgco2e_per_year']:.6g} over the limit {limit:.6g}")
    return {"anchor": anchor, "g_star_kgco2e_per_year": g_star, "slack": slack,
            "limit_kgco2e_per_year": limit, "rows": rows, "ranges": out}
