# Cut-off rule plan — 20 Oct 2026

> **Built 22 Oct 2026** (`docs/LCA_ASSURANCE_PLAN.md` Part 1): the register is
> `optimiser_lca/exclusions.py`, the test `optimisation/cutoff.py` (ASSUMPTIONS.md
> §8, generated), the rule-3 knob `dc_inputs.build_tech(cutoff="upper")` /
> `sensitivity.CARBON_KNOBS["cutoff"]`, the audit hook `audit.check_cutoff_rule`,
> and `tests/test_cutoff.py` holds it. What failed rule 1 on day one — the
> tank's forming (built as a row), its valves, the battery's and fuel cell's
> container switchgear, the grid connection's switchgear and factory energy
> (carried as estimates) — is included; what passed stays out and is shown
> with its share under each technology in the LCA map. Step 2's restore list
> was re-read against every source the same day (`docs/SOURCE_DIFF.md`, second
> read), which found more: three stacks per Gerloff unit, Leng's electrical
> installation, and the booster-station venue (D2 taken).

> **Numbers refreshed 21 Oct 2026** after the source diff's restores were
> built (`docs/SOURCE_DIFF.md`, *Implemented*): battery energy term 7,241 →
> **7,489** kg CO₂e per usable MWh per year; fuel-cell BoP 44,325 → **50,807**
> kg per MW per replacement (the shared container pad); wind step-ups 279 →
> **329** and solar step-ups 296 → **448** kg per MW per year (civils, and
> Smith's transformer replacements); solar plant +1.5 %; facility IT-side
> +1.0 % (Zhang's construction phase). The
> denominators quoted below are the 20 Oct ones; the shares move by under a
> twentieth of themselves and no verdict changes.

A plan for stating one cut-off rule and testing every exclusion in the study
against it, technology by technology. Raised by the supervisor's point 1
(19 Oct): the step-up transformers were in for wind and solar but closed as
"negligible" for the battery and fuel cell, with no shared rule behind either
call. The transformers are now in everywhere (15 Oct). This plan is for the rest.

Effort: XS < 1 h, S ≈ half a day, M ≈ 1–2 days, L > 2 days.

## The rule

**First principle (user, 20 Oct).** If a flow is in the underlying source LCA
and sits inside the study's boundary, it is included. No threshold applies:
size never licenses dropping a sourced flow. The boundary excludes exactly
three things: end-of-life, delivery to site (the site is not known), and the
standby generator. Everything else a source carries comes with it.

A deviation from a source that is not an exclusion (fixed tilt for Smith's
tracker, a Chinese cell factory for Voß's German one) is a **substitution**,
documented as such, with what replaced the dropped rows.

**When a sourced item may be substituted (22 Oct).** Only on a stated check
against the real thing, never because a substitute is cheaper or more
convenient:

- *Physical plausibility* — the source's row cannot describe the item. Smith's
  A11 transformer: 53 t for 2.7 MVA (~9× a real unit), 21 t of oil, a ferrite
  core.
- *Technological representativeness* (ISO 14044 data quality) — the source's
  row describes a different machine. Jasper's container transformer: a
  Hunziker 2020 recipe for a 630 kVA unit with an on-load tap changer, scaled
  by mass, against a current 2.5 MVA 20/0.4 kV distribution transformer.

The substitute comes whole: every in-boundary row it carries is taken (so the
IEA unit's factory energy comes with it). The set-aside source value is
reported as a **sensitivity**, so the choice is visible in either direction
(Smith's A11: solar step-up ×3–4; Jasper's recipe: battery +2 %, fuel cell
+4 %).

Substitution does not touch the cut-off test. A substituted item is sourced
(by its substitute), so it is never on the 1 %/5 % list; the list only ever
holds flows that no held source itemises.

**The cut-off rule applies only to flows with no source**: things the study
knows a real build has, that no source it holds itemises (switchgear for the
intake, forming of the tank steel, Voß's untabulated processing materials). For
those, the test decides whether a source or an estimate must be found, or the
flow can stay out and be documented. The study assesses GWP100 only, so it
uses the impact criteria of PAS 2050 and Vestas V162 §3.3, applied per
technology, not their mass and energy screens.

1. **Per flow.** An unsourced flow may stay out only if it is under **1 %** of
   its own technology's carbon.
2. **Per technology.** All of a technology's unsourced flows together must be
   under **5 %** of its carbon.
3. **Per decision.** Adding every unsourced flow back at its upper estimate
   must not change the optimiser's best design.

A flow that fails is estimated (mass × factor, or a published figure) and
included, and the estimate is graded ASSUMED in the register until a source
replaces it.

"Its technology's carbon" is the coefficient the LP charges, per unit of the
asset (see *Denominators*). Each exclusion is tested at its **upper** estimate.
A flow with no carbon figure gets one from mass × a generic factor (steel
~2 kg CO₂e/kg, concrete ~0.1–0.15).

Rules 1 and 2 are the per-technology tests PAS 2050 and Vestas set. Rule 3 is
this study's addition, under ISO 14044's sensitivity requirement for comparative
studies. A cut-off rule asks whether a flow matters to a product's footprint;
an optimiser also needs to know whether it changes a choice.

**Not ecoinvent's "cut-off" system model.** That is an allocation choice for
recycled content, and an unrelated use of the same word. Say so wherever the
rule is written down.

**Boundary choices are not cut-offs.** End-of-life (ASSUMPTIONS §6),
**delivery to site** (§6, since 20 Oct: the site is not known, so no capital
good, cable or hydrogen is carried to it; upstream transport is in) and the
standby generator (§7) are scope decisions, not flows inside the boundary.
They're listed in the register as `boundary`, reported but not tested against
1 %. Their justification stays in ASSUMPTIONS.

**Two exclusions were made by policy, not by test, and the rule now reaches
them.** *Civils* ("outside every capital inventory") and *manufacturing
energy* ("materials only, like every other foreground") were consistency
policies adopted while the inventories were built (commits `15db683`,
`5b1b9b9`), not scope decisions of the study: the only stated boundaries are
end-of-life, delivery to site and the genset. Neither depends on the site,
so neither can borrow the transport argument. Under this rule each is an
ordinary cut-off item, tested per technology and included where it fails.
Section 2 shows both fail wherever they are large enough to matter. "Civils
out" was never applied evenly anyway: wind carries its foundation, road and
excavation through ecoinvent's turbine, and the tank its pad since 14 Oct.

Sources: Vestas, *LCA of Electricity Production from an onshore EnVentus
V162-6.2 MW wind plant*, §3.3 (read in full, 20 Oct). PAS 2050 and ISO 14044
are cited from secondary summaries so far, so check their wording before the
paper cites them.

## Technologies and their denominators

One per chain in `dc_model.CHAINS`, plus the facility. Each is read from the
`Tech` that `dc_inputs.build_tech` returns, so the denominator is always the
number the LP actually uses.

| Technology | Denominator | From `Tech` |
|---|---|---|
| Wind | kg CO₂e per MW per year, turbine + step-up | `gwp_wind + gwp_tx_wind_per_mw` |
| Solar | per MWp per year, plant + step-up | `gwp_solar + gwp_tx_solar_per_mwp` |
| Battery | per MW per year; energy-side flows at their ceiling, power-side flows by break-even duration (`BATTERY_CUTOFF_ANALYSIS.md` §2, replaces Q1) | `gwp_batt_p + gwp_tx_batt_per_mw + h × gwp_batt_e` |
| Electrolyser | per MW per year | `gwp_ely` |
| Hydrogen tank | per kg of capacity per year | `gwp_tank` |
| Fuel cell | per MW per year, **calendar** replacements (see Q2) | `gwp_fc_bop_per_mw / bop_years + gwp_fc_stack_per_mw / stack_years + gwp_tx_fc_per_mw` |
| Grid connection | per MW per year | `gwp_grid_per_mw` |
| Grid electricity | per kWh delivered, the year's mean | `series.grid_gwp_per_mwh.mean()` |
| Bought hydrogen | per kg delivered | `bought_h2_gwp_per_kg` |
| Facility | per year | `dc_fixed_gwp_per_year` |

The facility is the same in every design, so rule 3 cannot apply to it. Rules 1
and 2 still do, because its total feeds every headline g/kWh.

## 1. One register of exclusions (S)

Today exclusions are written as free text inside each module
(`bess.CSS_EXCLUDED`, `bess.BESS_SCOPE`, `upv.UPV_PV_SCOPE`, and docstrings in
`stepup_transformers`, `h2_tank`, `fuel_cell`, `data_centre`) plus rows in
DATA_GAPS.md. Nothing measures them.

- [x] New `optimiser_lca/exclusions.py`, Python only like every other
      inventory. One entry per excluded flow:
      - `technology`: a `CHAINS` key or `"facility"`;
      - `flow`: what is left out;
      - `kind`: `cutoff` (tested) or `boundary` (reported only);
      - `upper`, `central`: kg CO₂e in the technology's denominator unit;
      - `method`: `transcribed` (a published figure), `mass_x_factor` (with
        mass, factor and both sources), or `assumed`;
      - `source` and `note`.
- [x] A test that every `EXCLUDED` value in the modules' scope dicts has a
      register entry, so a new exclusion can't be added without one.
- [x] Leave the scope dicts in place. They describe each inventory; the register
      measures it.

## 2. Estimate every exclusion (M)

Re-sorted on 20 Oct, after the transport boundary was settled and the battery
was worked through (`docs/BATTERY_CUTOFF_ANALYSIS.md`). Shares are against the
technology's own carbon, at the worst case the denominator allows; factors
were scored on this study's ecoinvent 3.9.1 apos, IPCC 2021 GWP100.

**Boundary, reported but not tested**

| Technology | Flow | Why |
|---|---|---|
| All | End-of-life | ASSUMPTIONS §6 |
| All | Delivery to site: Jasper's China-to-Germany rows, Smith A14, fuel cell, bought-H₂ haulage, Zhang's transportation phase, Leng's to-site transport | ASSUMPTIONS §6, site unknown |
| Facility | Standby generator | ASSUMPTIONS §7 |

**A. In a source and inside the boundary, currently dropped: restore, no test**

The source diff was run on 21 Oct (`docs/SOURCE_DIFF.md`): every inventory
against its source, row by row. This is its restore list. **Correction to the
first draft of this table:** Leng publish no factory electricity for either
transformer, so there is nothing to restore there; the "342 t with, 275 t
without" reading was a database difference, not a dropped flow.

| Technology | Flow | Source row | Dropped as | Size, for information |
|---|---|---|---|---|
| Battery | Container concrete block, 43.9 t per 3,008 kWh | Jasper SI, liquid sheet row 17 | "civils out" policy | 2.3 % of the battery |
| Fuel cell | The same pad, via the shared container | Jasper, as above | inherited | 2.3 % of a calendar-life fuel cell |
| Battery | Voß's 1,000 km in-China lorry leg on every cell material (kept on natural graphite only) | Voß ESI S5, S31, S35, S36, §3.1.3 | half-done on 20 Oct | < 1 % |
| Solar | Land occupation | Smith A14 | zero GWP100 | 0 |
| Solar mounting | Z-PV-239 upstream transport, packaging waste, land rows (10 rows) | IEA PVPS | not carried over | small |
| Solar step-ups | Transformer station building, 10 m² per 2.5 MVA unit | IEA PVPS Z-PV-238 | not carried over | to score |
| Facility | Construction-phase diesel, electricity, water | Zhang S1 (mmc1 on OneDrive) | "scope choice" | ~237 t over 25 y |
| Wind step-ups | Box-transformer foundations and electrical installation | Leng S3 | not taken | ~3.4 m³ concrete + 196 kg rebar per MW |
| Grid intake | Booster-station civils | Leng S3 | not taken | large; applicability is decision D2 in `SOURCE_DIFF.md` |
| Electrolyser (SOEC) | La₂O₃ and SrCO₃ in the electrolyte layer | Gerloff SI Fig. 5 | amount not held | small |

Each is a one-row change in its module, except Leng's civils, which need a
decision first. `SOURCE_DIFF.md` also lists nine substitutions worth a
decision (Jasper's own container-transformer split, the MP-E carbon credit,
iridium → platinum, …) and six claims in the code and docs that the sources
do not support.

**B. No source: cut-off, tested**

| Technology | Unsourced flow | Estimate | Worst-case share | Verdict |
|---|---|---|---|---|
| Battery | Processing materials (NMP make-up, argon, N₂, air) | 1.9 kg NMP/kWh at 95 % recovery, 6.73 kg/kg; ASSUMED | 0.65 % | passes |
| Battery | Site installation (crane, commissioning) | ~200 L diesel per container; ASSUMED | 0.2 % | passes |
| Battery | Container switchgear | Teffera 0.61 t/MW, scaled; to score | small | to confirm |
| Fuel cell | Container switchgear | as battery | small | to confirm |
| Hydrogen tank | Forming of the vessel steel (rolling, welding) | sheet rolling 0.64 to average metal working 2.71 kg/kg, on steel at 5.10 | **12–50 %** | **fails** |
| Hydrogen tank | Valves, compressor hardware | compressor ~0.01 % (4 Sep); valves mass × factor | small | to confirm |
| Wind | Step-up switchgear | Teffera 0.61 t/MW vs ~2.8 t/MW of step-ups | ~0.25 % | passes |
| Solar | Step-up switchgear | as wind | small | passes |
| Grid connection | Switchgear, protection, bay | Teffera: 0.61 t/MW switchgear vs 1.08 t/MW transformer | **~55 %** | **fails** |
| Grid connection | Civils | bay foundations, mass × factor | large | **fails** |
| Facility | Internal electrical distribution | 4 Sep bound, re-expressed per technology | to estimate | open |
| Electrolyser | none listed | walk `hydrogen.py` (Hermesmann) | — | open |
| Grid electricity | none of this study's own | ecoinvent's cut-offs only | — | n/a |
| Bought hydrogen | none beyond haulage | seller's compression is in | — | n/a |

What the sorting shows:

- **Foundations fail in both containers** (battery 2.3 %, fuel cell 2.3 %),
  while wind and the tank already carry theirs. Including them is cheap: the
  same 18.3 m³ pad row on the battery container, which the fuel cell's BoP
  reads through `FC_KW_PER_CONTAINER`.
- **The tank's forming is the largest miss in the study** by share. Gandiglio
  count only the steel; a pressure vessel is rolled and welded, and on
  ecoinvent's factors that is at least 12 % on top of the steel. Score it with
  `sheet rolling, chromium steel` on the vessel mass (the lower bound), with
  average metal working as the upper, and include it.
- **The grid connection fails everything**, because its denominator is a
  materials-only transformer at 137.7 kg CO₂e/MW/yr. Switchgear, factory
  energy and civils are each a large share of that, and a trivial share of the
  system (the connection is ~20 t/yr of ~11,000 at London). This is the rule
  biting hardest on the smallest technology. Factory energy is easy (Leng gives
  it); switchgear and civils need an EPD and a bay count, parked in DATA_GAPS
  since 4 Sep. See Q7.
- **Manufacturing energy** is excluded from the wind step-ups and the grid
  intake by policy. It passes on wind (0.27 %) and fails on the connection. It
  is not site-dependent, so the policy has no boundary argument; Leng publish
  both figures, so including it is a one-line change in each.

- [ ] Walk `hydrogen.py` and `data_centre.py` for the two open rows.
- [ ] Score the "to confirm" rows (switchgear, valves) rather than reasoning
      from Teffera's masses.
- [ ] Decide Q6 and Q7 before step 5.

## 3. Check rules 1 and 2 automatically (S)

- [x] `optimisation/cutoff.py`: `check(tech, series)` returns one row per
      exclusion (technology, flow, share at upper, pass/fail) and one row per
      technology (summed share, pass/fail against 5 %).
- [x] Wire it into `audit.py`, so every audit run reports it.
- [x] A fast test that fails if any `cutoff` entry breaks rule 1 or 2. It will
      fail on day one (battery foundations, solar transport). That's intended:
      it stays red until each failure is resolved (step 5).
- [x] Print the table into a new ASSUMPTIONS.md section, *8. Cut-off rule*,
      generated, as VALIDATION.md is.

## 4. Check rule 3 in the optimiser (S)

- [x] `build_tech(..., cutoff="upper")` adds each `cutoff` entry's upper
      estimate onto its technology's coefficient. Default `None` leaves today's
      model unchanged.
- [x] A `sensitivity.py` knob, `"cutoff": ["upper"]`, run on the two reference
      cases (`london_grid`, `islanded_h2`) at both anchors (min cost, min GWP).
      One bundled run per case adds about four solves in all.
- [x] Compare against the central run with the test defined in Q4. Record the
      result in ASSUMPTIONS §8. (23 Oct 2026: passes in both cases at both anchors.)

## 5. Resolve failures (M, depends on what fails)

A flow that fails rule 1, or a technology that fails rule 2, is **included**.
It's not argued away.

- [x] Include it as the register's central estimate, added to the coefficient
      (step 4's mechanism with `cutoff="central"` for that entry only), and mark
      it `included` in the register with its method.
- [x] Where a proper inventory row is cheap (battery foundations are 43.9 t of
      concrete), build it in the module instead and delete the register entry.
- [ ] If rule 3 fails, the exclusions that drive it are included the same way.
- [x] Log each one in DATA_GAPS.md, and in SOURCES.md where a number moved.

## 6. Close out (XS)

- [x] Delete the `TODO.md` cut-off item.
- [x] Re-run the reference cases if anything was included. Regenerate the LCA
      map so each technology's tree shows its exclusions and their shares.
- [ ] One paragraph for the paper's methods: the rule, its sources, the
      boundary choices, and the rule-3 result.

## Order

1 → 2 → 3 → 4 → 5 → 6. Step 2 is the bulk of the work. Steps 3 and 4 are small
once the register exists, and can be written while step 2's estimates are
gathered.

## Open questions

- **Q1. Battery reference duration.** Battery carbon per MW depends on
  duration, and the transformer share is ~3 % at 4 h and ~6 % at 2 h.
  Recommended: test at **2 h**, the strictest plausible duration for most
  flows (power-side flows are a larger share at short duration). State it, and
  report the share at the built duration too.
- **Q2. Fuel-cell denominator.** Carbon per MW depends on running hours through
  duty-driven replacements. Recommended: **calendar replacements only**, the
  smallest denominator and so the strictest test.
- **Q3. What a failure costs.** Recommended: include at the central estimate
  now, and build a proper inventory row later only where it's cheap.
- **Q4. What counts as "changing the best design".** Recommended: at both
  anchors, the same technologies are built, and each capacity moves by under
  5 %. A looser test (same technologies only) would pass more easily but say
  less.
- **Q5. Should the facility be in scope?** It never changes the design, so only
  rules 1 and 2 apply. Recommended: yes, because it is part of every headline
  g/kWh.
- **Q6. Civils** — settled 20 Oct: civils are in scope and were never
  excluded by the study. The pads go in (battery, fuel cell; wind and tank
  already have theirs), as Jasper's own row. Delete the "civils are outside
  every capital inventory" wording from `bess.py`, `transformers.py` and
  `grid_connection.py`.
- **Q7. The grid connection.** Per technology it fails on three counts; per
  system it is 0.2 %. Factory energy goes in now (Leng gives it). Switchgear
  and civils are in scope but have no source yet (a switchgear EPD and a bay
  count, DATA_GAPS 4 Sep row), so the choice is how to carry them meanwhile:
  an upper estimate from Teffera's masses in the register, with ASSUMPTIONS
  saying the connection is a floor and the rule-3 run showing it cannot change
  a design; or fold the connection into "grid electricity" as one technology,
  where all three pass easily, which is how a conventional LCA would see it.
