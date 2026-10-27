"""
The cut-off rule, measured: rules 1 and 2 on the register, every run.
=============================================================================

``optimiser_lca/exclusions.py`` lists every flow the study leaves out with an
upper estimate; this module divides each by its technology's carbon as the
LP charges it and says pass or fail (CUTOFF_RULE_PLAN.md).

    python optimisation/cutoff.py            # the two tables
    python optimisation/cutoff.py --write    # also regenerate ASSUMPTIONS.md §8

* **Rule 1, per flow:** an unsourced flow may stay out only if its upper
  estimate is under 1 % of its technology's coefficient.
* **Rule 2, per technology:** all of a technology's still-excluded flows
  together under 5 %.
* **Rule 3, per decision:** ``sensitivity.CARBON_KNOBS['cutoff']`` re-solves
  the reference cases with every excluded flow added at its upper estimate
  (``dc_inputs.build_tech(cutoff="upper")``); the design must not change.

Denominators are read from the ``Tech`` ``build_tech`` returns, so the test
always uses the number the LP actually charges. The battery (BATTERY_CUTOFF_
ANALYSIS.md §2): an energy-side flow is tested at its ceiling ``f / gwp_batt_e``
(the worst case for any duration); a power-side flow by its break-even
duration ``h* = (g / 0.01 − p) / e`` against ``H_FLOOR_HOURS``, and the rule-2
sum takes power-side shares at the floor. The fuel cell is per MW per year at
calendar replacements only, the strictest denominator. ``audit.run`` prints
the tables and flags any solved battery whose duration sits below the largest
break-even among excluded power-side flows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimiser_lca import exclusions as X  # noqa: E402

ASSUMPTIONS = ROOT / "optimisation" / "ASSUMPTIONS.md"
BEGIN, END = "<!-- cutoff:begin -->", "<!-- cutoff:end -->"


def denominators(tech) -> dict[str, dict]:
    """kg CO2e per unit of each technology per year, as the LP charges it."""
    fc = (tech.gwp_fc_bop_per_mw / tech.fc_bop_calendar_years
          + tech.gwp_fc_stack_per_mw / tech.fc_stack_calendar_years
          + tech.gwp_tx_fc_per_mw)
    return {
        "wind": {"value": tech.gwp_wind + tech.gwp_tx_wind_per_mw, "unit": "kg CO2e/MW/yr"},
        "solar": {"value": tech.gwp_solar + tech.gwp_tx_solar_per_mwp, "unit": "kg CO2e/MWp/yr"},
        "battery": {"p": tech.gwp_batt_p + tech.gwp_tx_batt_per_mw, "e": tech.gwp_batt_e,
                    "unit": "kg CO2e/MW/yr (p) and per usable MWh/yr (e)"},
        # plant + stacks at the calendar floor (Tech defaults the stack term to zero)
        "electrolyser": {"value": tech.gwp_ely + getattr(tech, "gwp_ely_stack_per_mw", 0.0)
                         / getattr(tech, "ely_stack_calendar_years", 25.0 / 3.0),
                         "unit": "kg CO2e/MW/yr"},
        "hydrogen tank": {"value": tech.gwp_tank, "unit": "kg CO2e per kg capacity/yr"},
        "fuel cell": {"value": fc, "unit": "kg CO2e/MW/yr, calendar replacements"},
        "grid connection": {"value": tech.gwp_grid_per_mw, "unit": "kg CO2e/MW/yr"},
        "grid electricity": {"value": None, "unit": "kg CO2e/kWh (series mean; no entries)"},
        "bought hydrogen": {"value": tech.bought_h2_gwp_per_kg, "unit": "kg CO2e/kg"},
        "facility": {"value": tech.dc_fixed_gwp_per_year, "unit": "kg CO2e/yr"},
    }


def _share(e: X.Exclusion, den: dict, which: str, h_floor: float):
    est = e.estimate(which)
    if est is None:
        return None, None
    if e.technology == "battery":
        p, en = den["battery"]["p"], den["battery"]["e"]
        if e.side == "energy":
            return est / en, None                           # the ceiling, any duration
        h_star = (est / X.CUTOFF_FLOW_SHARE - p) / en       # break-even duration
        return est / (p + en * h_floor), h_star             # the share at the floor
    d = den[e.technology].get("value")
    return (est / d if d else None), None


def check(tech, h_floor: float = X.H_FLOOR_HOURS) -> pd.DataFrame:
    """One row per cut-off or sourced entry: estimates, shares, verdicts."""
    X.check()
    den = denominators(tech)
    rows = []
    for e in X.REGISTER:
        if e.kind == "boundary":
            continue
        s_up, h_star = _share(e, den, "upper", h_floor)
        s_c, _ = _share(e, den, "central", h_floor)
        if e.status == "included_inventory":
            # Built as rows in its module: the share of a test estimate means nothing now.
            s_up = s_c = h_star = None
        if e.kind == "sourced":
            verdict = {"included_inventory": "sourced — built as inventory rows",
                       "included_estimate": "sourced — carried as the source's own figure",
                       "excluded": "sourced — left out, stated"}[e.status]
        elif e.status == "included_inventory":
            verdict = "in the inventory"
        elif e.status != "excluded":
            verdict = f"included ({e.status.split('_')[1]})"
        elif s_up is None:
            verdict = "unscored"
        elif e.side == "power":
            verdict = "pass" if h_star < h_floor else f"FAIL below {h_star:.2f} h"
        else:
            verdict = "pass" if s_up < X.CUTOFF_FLOW_SHARE else "FAIL"
        rows.append({
            "technology": e.technology, "flow": e.flow, "kind": e.kind, "status": e.status,
            "side": e.side or "", "method": e.method or "",
            "central": e.estimate("central"), "upper": e.estimate("upper"),
            "unit": X.TECHNOLOGIES[e.technology][1] if e.side is None else
                    ("kg CO2e per usable MWh per year" if e.side == "energy" else "kg CO2e per MW per year"),
            "share_central": s_c, "share_upper": s_up, "break_even_h": h_star,
            "rule_1": verdict, "source": e.source, "basis": e.basis,
        })
    return pd.DataFrame(rows)


def technology_table(df: pd.DataFrame, tech) -> pd.DataFrame:
    """Rule 2: the still-excluded flows of each technology, summed at their worst case."""
    den = denominators(tech)
    out = []
    for t, (_chain, unit) in X.TECHNOLOGIES.items():
        if t == "all":
            continue
        sub = df[(df.technology == t) & (df.kind == "cutoff")]
        exc = sub[sub.status == "excluded"]
        total = exc.share_upper.dropna().sum() if len(exc) else 0.0
        unscored = int(exc.share_upper.isna().sum())
        d = den[t]
        out.append({
            "technology": t, "denominator": d.get("value", d.get("p")), "unit": d["unit"],
            "cutoff_entries": int(len(sub)), "still_excluded": int(len(exc)), "unscored": unscored,
            "sum_share_upper": total,
            "rule_2": ("n/a" if not len(exc) else "unscored" if unscored else
                       "pass" if total < X.CUTOFF_TECHNOLOGY_SHARE else "FAIL"),
        })
    return pd.DataFrame(out)


def failures(tech, h_floor: float = X.H_FLOOR_HOURS) -> list[str]:
    """What still breaks rule 1 or rule 2 among flows with status 'excluded'."""
    df = check(tech, h_floor)
    out = [f"{r.technology}: {r.flow} — {r.rule_1} ({r.share_upper:.1%} at upper)"
           for r in df.itertuples() if r.kind == "cutoff" and r.status == "excluded"
           and isinstance(r.rule_1, str) and r.rule_1.startswith("FAIL")]
    out += [f"{r.technology}: {r.flow} — not yet scored"
            for r in df.itertuples() if r.kind == "cutoff" and r.status == "excluded" and r.rule_1 == "unscored"]
    tt = technology_table(df, tech)
    out += [f"{r.technology}: still-excluded flows sum to {r.sum_share_upper:.1%} (rule 2)"
            for r in tt.itertuples() if r.rule_2 == "FAIL"]
    return out


def power_side_floor(tech) -> float:
    """The largest break-even duration among excluded power-side battery flows;
    a solved battery shorter than this has a flow over 1 %."""
    df = check(tech)
    sub = df[(df.technology == "battery") & (df.side == "power") & (df.status == "excluded")]
    return float(sub.break_even_h.max()) if len(sub) and sub.break_even_h.notna().any() else 0.0


def battery_duration_flags(tech, cap_batt_e_mwh: float, cap_batt_p_mw: float) -> list[str]:
    """For audit: flag a built battery whose duration sits below the break-even of an excluded power-side flow."""
    if not cap_batt_p_mw or cap_batt_p_mw <= 1e-9:
        return []
    h = cap_batt_e_mwh / cap_batt_p_mw
    floor = power_side_floor(tech)
    return ([f"battery built at {h:.2f} h, below the {floor:.2f} h break-even of an excluded power-side flow"]
            if h < floor else [])


# =============================================================================
# Printing and the generated ASSUMPTIONS section
# =============================================================================
def _fmt(x, pct=False):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:.2%}" if pct else f"{x:,.3g}"


def render(tech) -> str:
    df, tt = check(tech), technology_table(check(tech), tech)
    lines = ["## 8. Cut-off rule", "",
             "A flow that is in a held source and inside the boundary is always in; the",
             "boundary excludes only end-of-life, delivery to site and the standby generator",
             "(§6–7). The cut-off test below applies to flows no held source itemises: each",
             f"may stay out only if its upper estimate is under {X.CUTOFF_FLOW_SHARE:.0%} of its technology's",
             f"carbon (rule 1), all of a technology's together under {X.CUTOFF_TECHNOLOGY_SHARE:.0%} (rule 2), and",
             "adding them all back must not change the best design (rule 3, the `cutoff`",
             "sensitivity knob). Criteria after PAS 2050 and Vestas V162 §3.3, applied per",
             "technology; rule 3 is this study's addition under ISO 14044's sensitivity",
             "requirement for comparative assertions. Not ecoinvent's \"cut-off\" system model.",
             f"Battery power-side flows are tested at a {X.H_FLOOR_HOURS:g} h floor; energy-side flows at their",
             "ceiling. A flow that fails is included (status below). Register:",
             "`optimiser_lca/exclusions.py`; this section is generated by",
             "`python optimisation/cutoff.py --write`.", "",
             "### Rule 1 — per flow", "",
             "| Technology | Flow | Kind | Status | Central | Upper | Unit | Share at upper | Verdict |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in df.itertuples():
        lines.append(f"| {r.technology} | {r.flow} | {r.kind} | {r.status} | {_fmt(r.central)} | {_fmt(r.upper)} "
                     f"| {r.unit} | {_fmt(r.share_upper, pct=True)} | {r.rule_1} |")
    lines += ["", "### Rule 2 — per technology", "",
              "| Technology | Denominator | Unit | Cut-off entries | Still excluded | Sum of upper shares | Verdict |",
              "|---|---|---|---|---|---|---|"]
    for r in tt.itertuples():
        lines.append(f"| {r.technology} | {_fmt(r.denominator)} | {r.unit} | {r.cutoff_entries} | {r.still_excluded} "
                     f"| {_fmt(r.sum_share_upper, pct=True)} | {r.rule_2} |")
    lines += ["", "### Boundary items — reported, not tested", "",
              "| Technology | What | Why |", "|---|---|---|"]
    for e in X.boundaries():
        lines.append(f"| {e.technology} | {e.flow} | {e.source}{(' — ' + e.note) if e.note else ''} |")
    rule3 = ROOT / "optimisation_outputs" / "cutoff_rule3.md"
    if rule3.exists():                      # written by the rule-3 run (sensitivity knob "cutoff")
        lines += ["", rule3.read_text(encoding="utf-8").strip(), ""]
    else:
        lines += ["", "### Rule 3 — the design-change test", "",
                  "_Not yet run: `python -m optimisation.sensitivity cutoff`, then "
                  "`python scripts/cutoff_rule3.py`._", ""]
    return "\n".join(lines)


def write_assumptions(tech) -> Path:
    text = ASSUMPTIONS.read_text(encoding="utf-8")
    block = f"{BEGIN}\n{render(tech)}\n{END}\n"
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        text = head + block + tail.lstrip("\n")
    else:
        text = text.rstrip("\n") + "\n\n" + block
    ASSUMPTIONS.write_text(text, encoding="utf-8", newline="\n")
    return ASSUMPTIONS


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    from optimisation import dc_inputs as I
    meta = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
    tech = I.build_tech("london", meta, h2_colour="green")
    df = check(tech)
    with pd.option_context("display.width", 220, "display.max_columns", 20, "display.max_colwidth", 48):
        print(df[["technology", "flow", "status", "central", "upper", "share_upper", "break_even_h", "rule_1"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.4g}"))
        print()
        print(technology_table(df, tech).to_string(index=False, float_format=lambda x: f"{x:,.4g}"))
    fails = failures(tech)
    print(f"\n{len(fails)} failure(s):" + ("".join(f"\n  {f}" for f in fails) if fails else " none"))
    if "--write" in argv:
        print(f"wrote §8 into {write_assumptions(tech).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
