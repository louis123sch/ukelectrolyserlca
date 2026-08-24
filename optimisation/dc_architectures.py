"""
The power options, and the scenario matrix.
=============================================================================

An architecture is a set of upper bounds — which assets the optimiser may build.
Nothing is ever *required*: an unlocked asset is set to zero whenever it is not
worth building, which is itself a result.

The five options, plus two references
-------------------------------------
``grid_only`` and ``grid_battery`` are references rather than proposals.
``grid_only`` reproduces the 16,006 t CO2e/yr baseline every other number is
quoted against. ``grid_battery`` — grid plus a battery and no new generation —
is the structural counterpart to ``grid_h2`` on bought hydrogen: both do exactly
one job, shifting grid electricity in time from clean half-hours to dirty ones.
Isolating it from ``grid_res_battery`` is what makes the battery-versus-hydrogen
comparison apples-to-apples, because it takes the renewables out of both sides.

Why the battery is locked in the core hydrogen rows
---------------------------------------------------
A deliberate experimental choice, not an oversight. Unlock it and the min-cost
answer in every hydrogen row becomes "build a battery, skip the hydrogen" —
true, but it destroys the measurement, because the hydrogen chain's own cost and
carbon can no longer be read off. Locked, each row is a clean statement about
one technology, ``grid_battery`` is the battery's own clean statement, and the
two ``free`` control rows are where everything competes at once. Reversible in
one line; ``battery_unlocked`` is on the sensitivity list either way.

Expect the islanded rows to be expensive
----------------------------------------
``res_h2`` is islanded, has no battery, and must hold zero unserved load through
a 29 % round trip. That is the honest cost of *renewables + hydrogen* as
specified, and the battery-unlocked sensitivity shows how much of it is
avoidable.

Run:  python optimisation/dc_architectures.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M

# Hydrogen bought rather than built. Colours map to h2_prices_recommended.csv.
BOUGHT_COLOURS = ("grey", "blue", "turquoise", "green")
ONSITE_TECHS = ("PEM operation", "AE operation", "SOEC operation")
STRATEGIES = ("baseload", "flexible", "free")


def architecture(name: str, *, grid_limit_mw=None, offshore=False,
                 allow_export=False) -> M.Assets:
    """Asset bounds for one named power option."""
    base = dict(grid_limit_mw=grid_limit_mw, allow_export=allow_export)
    if name == "grid_only":
        return M.Assets(grid=True, **base)
    if name == "grid_battery":
        return M.Assets(grid=True, battery=True, **base)
    if name == "grid_res_battery":
        return M.Assets(grid=True, wind=True, solar=True, offshore_wind=offshore,
                        battery=True, **base)
    if name == "grid_h2":
        return M.Assets(grid=True, electrolyser=True, tank=True, fuel_cell=True, **base)
    if name == "grid_h2_bought":
        return M.Assets(grid=True, fuel_cell=True, buy_h2=True, **base)
    if name == "res_h2":
        assets = M.Assets(grid=False, wind=True, solar=True, offshore_wind=offshore,
                          electrolyser=True, tank=True, fuel_cell=True)
        return replace(assets, grid_limit_mw=0.0, allow_export=False)
    if name == "res_h2_grid":
        return M.Assets(grid=True, wind=True, solar=True, offshore_wind=offshore,
                        battery=True, electrolyser=True, tank=True, fuel_cell=True,
                        buy_h2=True, **base)
    raise ValueError(f"Unknown architecture {name!r}")


@dataclass(frozen=True)
class Scenario:
    n: int
    architecture: str
    label: str
    ely_tech: str | None = None
    h2_colour: str | None = None
    strategy: str = "free"
    tank_design: str | None = None
    note: str = ""

    @property
    def key(self) -> str:
        bits = [f"{self.n:02d}", self.architecture]
        if self.ely_tech:
            bits.append(self.ely_tech.split()[0].lower())
        if self.h2_colour:
            bits.append(self.h2_colour)
        if self.strategy != "free" or not self.h2_colour:
            bits.append(self.strategy)
        return "_".join(bits)


def core_matrix() -> list[Scenario]:
    """The 21 configurations. 18 involve hydrogen; all six pathways appear."""
    S, n = [], 0

    def add(**kw):
        nonlocal n
        n += 1
        S.append(Scenario(n=n, **kw))

    add(architecture="grid_only", label="Grid only", note="reference — the 16,006 t/yr baseline")
    add(architecture="grid_battery", label="Grid + battery",
        note="time-shift only, no new generation — the battery's clean statement")
    add(architecture="grid_res_battery", label="Grid + renewables + battery")

    for tech in ONSITE_TECHS:
        for strat in ("baseload", "flexible"):
            add(architecture="grid_h2", label=f"Grid + H2 ({tech.split()[0]})",
                ely_tech=tech, strategy=strat)
    for tech in ONSITE_TECHS:
        for strat in ("baseload", "flexible"):
            add(architecture="res_h2", label=f"Renewables + H2 ({tech.split()[0]}), islanded",
                ely_tech=tech, strategy=strat,
                note="baseload uses the annual CF floor only — a per-step floor is "
                     "degenerate without a grid" if strat == "baseload" else "")
    for colour in BOUGHT_COLOURS:
        add(architecture="grid_h2_bought", label=f"Grid + bought H2 ({colour})",
            h2_colour=colour, note="just-in-time, no storage")

    add(architecture="grid_h2", label="Grid + H2 (PEM) — control",
        ely_tech="PEM operation", strategy="free", note="control: what the LP would do")
    add(architecture="res_h2_grid", label="Everything available — control",
        ely_tech="PEM operation", strategy="free",
        note="control: the configuration anyone would actually build")
    return S


def table() -> pd.DataFrame:
    rows = []
    for s in core_matrix():
        a = architecture(s.architecture)
        rows.append({
            "n": s.n, "key": s.key, "architecture": s.architecture,
            "label": s.label, "ely": s.ely_tech.split()[0] if s.ely_tech else "-",
            "h2_colour": s.h2_colour or "-", "strategy": s.strategy,
            "grid": a.grid, "wind_solar": a.wind or a.solar, "battery": a.battery,
            "electrolyser": a.electrolyser, "tank": a.tank, "fuel_cell": a.fuel_cell,
            "bought_h2": a.buy_h2, "note": s.note,
        })
    return pd.DataFrame(rows)


def run():
    df = table()
    print("=" * 112)
    print("SCENARIO MATRIX — what each configuration may build")
    print("=" * 112)
    tick = lambda b: "Y" if b else "."
    print(f"  {'#':>3} {'configuration':<38}{'grid':>5}{'w/s':>5}{'batt':>5}"
          f"{'ely':>5}{'tank':>5}{'fc':>4}{'buy':>5}  strategy")
    for _, r in df.iterrows():
        name = r.label + ("" if r.ely == "-" else "")
        print(f"  {r.n:>3} {name[:38]:<38}{tick(r.grid):>5}{tick(r.wind_solar):>5}"
              f"{tick(r.battery):>5}{tick(r.electrolyser):>5}{tick(r.tank):>5}"
              f"{tick(r.fuel_cell):>4}{tick(r.bought_h2):>5}  {r.strategy}")
    h2 = df[(df.electrolyser) | (df.bought_h2)]
    print(f"\n  {len(df)} configurations, {len(h2)} involving hydrogen.")
    print(f"  Every pathway in lca_helpers.H2_CODES appears: AE / PEM / SOEC as built")
    print("  assets whose emissions follow the electricity feeding them, and")
    print("  SMR / SMR-CCS / MP-E as bought commodities at a price with a fixed burden.")
    print(f"\n  With a 13-point Pareto sweep each, that is {len(df) * 13} LP solves.")
    for _, r in df[df.note != ""].iterrows():
        print(f"    {r.n:>3}  {r.note}")
    return df


if __name__ == "__main__":
    run()
