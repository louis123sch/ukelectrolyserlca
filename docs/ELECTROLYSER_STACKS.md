# Electrolyser stacks against running hours — investigation, 26 Oct 2026

SOURCE_RECHECK_2026-10-23 finding #8. **Option B chosen and implemented, 26 Oct 2026** (see the end).

## What Gerloff assumes

- Plant life 20 years, **operating 8,000 h per year** (§2.1.2): 160,000 running hours.
- Stacks last "**50,000 h or more**" (IndWEDe's 2030 scenario, §2.1.2) and are
  "replaced 3 times during the 20 years": three stacks for 160,000 h, about 53,300 h
  each. The ×3 is applied to the stack rows (§2.1.3).
- Gerloff's unit is per kg of hydrogen: one unit per lifetime output (160 GWh at 1 MW).
  Stack life is a **running-hours** quantity; no calendar stack life is given.
- His literature review gives AE stacks 60,000–90,000 h (§3, ref. 37); Bareiß 2019
  gives PEM stacks 40,000–60,000 h.

## What the model does

`gwp_ely` = the whole unit (plant + three stacks) ÷ 25 years (NESO plant life) per MW
of electrical input, whatever the electrolyser actually runs. Three stacks cover
150,000–160,000 h; 25 years is 219,000 h. So the charge is right at **68–73 %
utilisation**, too high below it and too low above it. The cost side is the same
shape: NESO capex + 2.75 %/yr fixed opex over 25 years, with no separate stack
replacement line.

## How much of the unit is stack (t CO2e per 1 MW unit, 26 Oct inventory)

| | Plant | Three stacks | One stack | Stack share |
|---|---|---|---|---|
| AE | 105 | 712 | 237 | 87 % |
| PEM | 81 | 415 | 138 | 84 % |
| SOEC | 202 | 351 | 117 | 64 % |

Stack includes the stack's share of SI Table 3's manufacturing electricity; the 250 km
lorry leg is negligible.

## What the reference case actually does (islanded_h2, PEM, 2025, solved 26 Oct)

| Strategy | Anchor | Electrolyser | Utilisation | Stacks needed over 25 y (53,300–50,000 h) | Charged | Electrolyser carbon |
|---|---|---|---|---|---|---|
| free (default) | min cost | 4.8 MW | 70.6 % | 2.9–3.1 | 3 | about right |
| free (default) | min carbon | 81.2 MW | 16.9 % | 0.7 | 3 | over-charged, if stacks only wear with use |
| baseload | min cost | 4.8 MW | 85 % | 3.5–3.7 | 3 | 14–20 % low (13–19 t/yr) |
| baseload | min carbon | 80.1 MW | 85 % | 3.5–3.7 | 3 | 14–20 % low (217–319 t/yr, 0.5–0.7 % of the system) |

The baseload floor is exactly 85 % in both baseload solves. The London grid case builds
no electrolyser under any strategy. Under baseload AE would be 14–21 % low and SOEC
10–15 %.

The low-utilisation side is the larger effect. If stacks wore only with running hours,
the min-carbon design's 81 MW electrolyser would carry about 1,000 t/yr less (2.3 % of
the system), and the LP would then likely build a bigger one. Whether that is real
depends on a **calendar** stack life (membranes also age with time and start-stop
cycling), which no held source gives.

## Options

- **A. Keep, and flag.** Leave the charge as it is; have the run summary and `audit.py`
  flag any solution whose electrolyser runs above ~68 % and report the under-charge.
  No number moves; baseload stays under-charged but visible.
- **B. Today's charge as a floor, plus a running-hours top-up (recommended).** Exactly
  the fuel cell's mechanism (`dc_model.py`, `fc_stack_duty`): stack units ≥ 3 per 25 y
  per MW, and ≥ running MWh ÷ 50,000 h. Nothing changes below ~68 %; baseload and any
  hard-run design pays for its extra stacks, and the LP sees it. Needs the unit split
  into plant + one stack (reopens the 23 Oct closure of the stack/BoP split), new `Tech`
  fields, two constraints, and map and test updates. Source: Gerloff's stated 50,000 h.
  Carbon only: NESO gives no stack cost to mirror on the cost side. *(Superseded 20 Nov 2026: stacks are
  charged in cost too, below.)*
- **C. Fully running-hours, with a calendar floor.** Stack units ≥ capacity ÷ calendar
  stack life, and ≥ running MWh ÷ 50,000 h. The most physical, and it would also lower
  the charge on lightly run electrolysers, but it needs a calendar stack life that is
  not in any held source; until one is found, that number would decide the min-carbon
  design.
- **D. A per-strategy constant.** Charge baseload runs at the 85 % floor (3.5–3.7
  stacks). No LP change, but inexact above 85 % and silent for free runs near the edge.

## Implemented: option B (user, 26 Oct 2026)

- `optimiser_lca/hydrogen.py`: each unit is `*_gerloff_plant_1unit` (BoP rows, SI Table 3's
  BoP energy, the assembly leg on the plant's mass) and `*_gerloff_stack_1unit` (one
  stack's rows, a third of Table 3's stack energy, the leg on one stack); the unit is
  plant + 3 × stack and scores exactly as before.
- `optimisation/electrolysers.py`: `plant_kgco2e_per_MW`, `stack_kgco2e_per_MW`;
  `STACK_DUTY_HOURS = 50,000` (Gerloff §2.1.2), `STACK_CALENDAR_YEARS = 25 / 3` (the floor).
- `optimisation/dc_model.py`: `ely_stack_units` ≥ cap_ely ÷ 8.33 y and ≥ running MWh ÷
  50,000 h; carbon term "electrolyser stack replacements". `gwp_ely` is the plant alone.
  Carbon only (audit finding accepted: NESO has no stack cost).
- PEM: plant 3,257 kg/MW/yr, stack 138,248 kg per MW; at the floor 19,847 kg/MW/yr, as before.

Re-solved, islanded_h2, PEM:

| Strategy | Anchor | Before | After |
|---|---|---|---|
| free | min cost | 4.8 MW at 70.6 %, electrolyser 95.7 t/yr | same design, 98.2 t/yr (+2.6 %: 0.124 stacks per MW-year against the 0.120 floor) |
| free | min carbon | 81.2 MW at 16.9 %, 1,611.6 t/yr | unchanged (calendar floor binds) |
| baseload | min cost | 4.8 MW, 95.7 t/yr | same design, 115.0 t/yr (+20 %) |
| baseload | min carbon | 80.1 MW; system 46,181 t/yr | 68.2 MW, battery 200 → 364 MWh; system 46,469 t/yr (+0.6 %) |

## Change of 19 Nov 2026: a one-stack floor

Decided 19 Nov 2026 (docs/CODE_CHECK_FIX_PLAN.md step 3, decision D2, option B).
The calendar floor is now **one stack per 25-year plant life**
(`electrolysers.STACK_CALENDAR_YEARS = PLANT_LIFETIME_YEARS`), not three.

**Why.** The 8.33-year floor (25 y / 3 stacks) had no source of its own: it was
chosen so low-use electrolysers kept the charge they had before the split. The
cost side has no such floor. NESO's capex holds the first stack, and its variable
opex per kg (then read as "stack replacement and water"; since 20 Nov 2026 read as water and
consumables, below) scales replacements with output only.
So the two sides disagreed below about 68 % utilisation. Under option B both
sides mean the same thing: the first stack is always built, and replacements
follow running hours (Gerloff's 50,000 h on carbon, NESO per kg on cost). Every
number is sourced.

**What it changes.** Only electrolysers running below about 6,000 h a year
(68 %). For the islanded PEM min-carbon design above (81 MW at 17 %), the
charge falls from 3 stacks per 25 years to about 1 (duty would give 0.7), so
roughly 1,000 t CO2e a year (about 2.3 % of the system) comes off, and the
min-carbon electrolyser may grow. Not yet re-solved: that is step 5 of the plan.

**What it leaves out.** Calendar ageing of membranes at low use. No held source
quantifies it. The three-stack rule is kept as a named sensitivity,
`electrolysers.STACK_CALENDAR_YEARS_THREE_STACKS`, passed as
`build_tech(ely_stack_calendar_years=...)`, so the paper can report both.

## Change of 20 Nov 2026: stacks charged in cost

Decided 20 Nov 2026 (user; docs/COMPARISON_FIXES_PLAN.md, from the Rozzi 2024 cost comparison,
`Claude outputs/rozzi_cost_comparison.md` item 1).

**What was wrong.** This document said in one place that NESO gives no stack cost and in another
that NESO's per-kg figure is "stack replacement and water". The first was right. NESO's variable
opex is 0.9 % of capital a year over 7,884 h (FES 2025 Economics Inputs v2, H.01 row 13), the same
0.9 % it uses for gas reforming, which has no stacks. The Danish Energy Agency, one of NESO's named
sources, prices no stack replacement in its fixed O&M (note P) and no water (note Q). So the cost
side paid for the first stack inside the capital and for no replacement at all.

**What it is now.** The stack's share of the installed price is the Danish sheets' (2025 central):
membrane 17.7 %, alkaline 14.1 %, solid oxide 13.1 % (`h2_capex.ely_stack_cost_fraction`;
Rozzi's 35 % of equipment is about 21 % installed; tested at x0.5 / x1.5). The cost is split like the
fuel cell's: the plant's annuity, plus the stack's annuity less its calendar replacement, on
capacity (`cost_ely`); each stack at its price on the carbon side's `ely_stack_units`
(`cost_ely_stack_per_mw`). With the stack on its calendar life (one per plant life) this is exactly
the old annuity. NESO's per-kg figure stays, relabelled water and consumables; solid oxide's per-kg
figure is NESO's 0.9 % rule on its own price, no longer the BEIS annex's annuitised stack.

**Effect, before any solve.** Membrane at 6,185 h a year: about +£29k per MW a year (+9 %); nothing
changes below 2,000 h. **Stated limitation:** every type's stack is replaced at the carbon side's
50,000 h; the Danish lives are 60,000 (membrane), 70,000 (alkaline) and 25,000 h (solid oxide), so
solid oxide's stacks are replaced about half as often as they should be.
