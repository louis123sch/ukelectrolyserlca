# Battery cut-off analysis — 20 Oct 2026

> **21 Oct 2026:** the foundation this note found failing is now included,
> not as a cut-off verdict but because it is in Jasper's inventory and inside
> the boundary (`docs/SOURCE_DIFF.md`). The energy coefficient is 7,489 kg
> CO₂e per usable MWh per year (was 7,241); the worked figures below are the
> 20 Oct ones. The method in §2 (ceiling for energy-side flows, break-even
> duration for power-side flows) is unchanged, and the remaining unsourced
> flows still total under 0.9 %.

How the cut-off rule in `docs/CUTOFF_RULE_PLAN.md` applies to the grid battery,
and what it finds.

**Result.** One of the battery's exclusions fails the 1 % test at any duration:
the **container foundations** (up to 2.3 %). Everything excluded together comes
to 3.2 % at most, which passes the 5 % cap. Once the foundations are included,
what's left is under 0.9 %. None of this needs a model run: the 1 % and 5 %
tests are arithmetic on the battery's coefficients.

**Transport to site is a boundary, not a cut-off.** The study is
cradle-to-gate on every input (ASSUMPTIONS §6), so no capital good, hydrogen or
cable is carried to site, for any technology. Delivery transport is therefore
outside the system and is never tested against 1 %, the same as end-of-life.
(An earlier draft of this note tested it as a cut-off and found it failing.
That was wrong.)

## 1. How the battery is charged

The LP sizes the battery as two independent variables (`dc_model.py:343-344`,
`:404-406`):

- **Power, `cap_batt_p` (MW):** the inverter and the step-up transformer.
  Charge and discharge must each stay at or below it.
- **Energy, `cap_batt_e` (MWh usable):** the cells, racks, cooling and
  container. The state of charge must stay at or below it.

Duration, h = MWh ÷ MW, is never chosen directly. The model builds whatever
ratio is best, and has built 4.3 to 19.5 hours on the reference cases
(`sensitivity_stepups_*.csv`).

Carbon per year, from the London `Tech` (19 Oct):

| Part | Coefficient | kg CO₂e/yr |
|---|---|---|
| Inverter (PCS) | `gwp_batt_p` | 2,124 per MW |
| Step-up transformer | `gwp_tx_batt_per_mw` | 1,045 per MW |
| Cells, racks, cooling, container | `gwp_batt_e` | 7,241 per usable MWh |

So a battery of duration h carries, per MW of inverter:

```latex
D(h) = 3{,}169 + 7{,}241\,h \quad \text{kg CO}_2\text{e per MW per year}
```

D(h) is the denominator for every battery flow. It's measured on what's already
included, which is stricter than the Vestas wording ("the whole impact"),
because adding the exclusions back would make D larger and every share
smaller.

## 2. Testing each flow at its worst case

An excluded flow either grows with MW or grows with MWh, and the two behave in
opposite ways.

**Energy-side flows** (foundations, processing materials) add f kg per MWh per
year. Their share is f·h ÷ D(h), which rises with duration towards a ceiling:

```latex
\text{share}_{E}(h) = \frac{f\,h}{3{,}169 + 7{,}241\,h} \;<\; \frac{f}{7{,}241}
```

So **test energy-side flows at the ceiling, f ÷ 7,241.** It is the worst case
for any battery of any duration, so the result never depends on what a run
builds.

**Power-side flows** add g kg per MW per year. Their share is g ÷ D(h), which
falls with duration. The worst case is the shortest battery, so each flow has a
**break-even duration** below which it would fail:

```latex
h^{*} = \frac{g / 0.01 - 3{,}169}{7{,}241}
```

**Test power-side flows by their break-even.** A flow passes if h\* is below
the shortest battery the model builds. The audit checks every run's built
duration against the largest h\* among excluded power-side flows.

The battery has no excluded power-side flows today: the inverter and the
transformer are both included, and their delivery is outside the boundary. So
this half of the method is ready but not yet needed.

## 3. The exclusions and their estimates

From `optimiser_lca/bess.py` (`BESS_SCOPE`, `CSS_EXCLUDED`, the docstring)
and `optimisation/battery.py`. Factors were scored on 20 Oct on this study's
ecoinvent 3.9.1 apos with IPCC 2021 GWP100.

| Flow | Kind | Central | Upper | Upper, per year | Worst-case share | Verdict |
|---|---|---|---|---|---|---|
| Container foundation | cut-off, energy | 1.94 kg/kWh | 2.29 kg/kWh | 169 per MWh | **2.34 %** | **fails** |
| Processing materials (NMP, argon, N₂, air) | cut-off, energy | 0.13 kg/kWh | 0.64 kg/kWh | 47 per MWh | 0.65 % | passes |
| Site installation | cut-off, energy | 0.10 kg/kWh | 0.21 kg/kWh | 16 per MWh | 0.21 % | passes |
| **Cut-off exclusions together** | | | | | **3.2 %** | **passes 5 %** |
| Delivery transport (cells, container, PCS, transformer) | boundary | — | — | — | — | not tested |
| End-of-life | boundary | — | — | — | — | not tested |

kg/kWh is per kWh of nameplate cells. The per-year column divides by the
0.90 usable fraction and the 15-year life, as `battery.embodied_components`
does.

How each was estimated:

- **Foundation.** Jasper's 43.9 t concrete pad per 3,008 kWh container
  (`CSS_EXCLUDED`). At 2,400 kg/m³ and 318.5 kg CO₂e/m³ (ecoinvent `market for
  concrete, normal strength` [RoW]) that's 1.94 kg/kWh. The upper adds 1 %
  rebar by mass at 2.41 kg CO₂e/kg (+18 %). Jasper's own Fig. 4 gives 2.06,
  inside the range. Spread over the battery's 15 years, not the pad's own life
  (see Q2).
- **Processing materials.** NMP make-up only, on ~1.9 kg NMP circulated per kWh
  (about 1:1 with the 1.89 kg/kWh of cathode active material) at 99 %
  recovery (central) or 95 % (upper), at 6.73 kg CO₂e/kg. Argon, nitrogen and
  compressed air are taken as small next to that. The recovery rates are
  ASSUMED, so this needs a source before it's quoted, but it passes even at
  95 % recovery.
- **Site installation.** Crane and commissioning diesel, about 200 L per
  container. ASSUMED. This is site work, not transport, so it stays a cut-off
  item; solar does count its installation diesel (`upv.py`, Smith A14).

## 4. What changes

1. **Include the foundation** in `bess.py` as an inventory row on the
   container (`_CSS`): 18.3 m³ of concrete per container, plus rebar if
   Jasper's SI gives it. Delete its `CSS_EXCLUDED` entry. This adds about
   144 kg per MWh per year, +2.0 % on `gwp_batt_e`.
2. **Leave processing materials and installation excluded.** Together they're
   0.87 % at worst.
3. **Reword the transport exclusion.** `BESS_SCOPE["transport"]` currently reads
   as a cut-off ("EXCLUDED - every delivery row"). It should say outside the
   boundary: cradle-to-gate, no delivery to site.

The foundation lands on the battery and not its competitors. That is a small
version of the case rule 3 (the design-change test) exists for.

## 5. Implementation

1. **Register the battery entries** in `optimiser_lca/exclusions.py` (plan
   step 1), each with `kind` (`cutoff` or `boundary`), `side` (power or
   energy), central and upper per kWh nameplate or per kW, `life_years`, method
   and source. The annualising (÷ usable fraction, ÷ 15 y) happens in the
   check, not the register, so a swept usable fraction or life carries through.
2. **Write the check.** In `optimisation/cutoff.py`:
   - energy side: share = upper per year ÷ `tech.gwp_batt_e`;
   - power side: h\* = (upper ÷ 0.01 − p) ÷ e, with p = `gwp_batt_p +
     gwp_tx_batt_per_mw` and e = `gwp_batt_e`, passing if h\* < `H_FLOOR`;
   - the 5 % test: the energy-side ceilings plus the power-side shares at
     `H_FLOOR`. Their worst cases sit at opposite ends of the duration range,
     so the sum overstates the true worst case, which keeps the test
     conservative.
3. **Add an audit hook.** For each solved run, compute `cap_batt_e /
   cap_batt_p` and flag it if it's below the largest h\* among excluded
   power-side flows. There are none today.
4. **Include the foundation** (section 4). Re-run the battery's fast tests,
   check that `gwp_batt_e` moves by the expected ~2.0 %, and record before and
   after in `SOURCES.md`.
5. **Run rule 3** for the battery as part of the plan's bundled run.

## Questions

- **Q1. Floor for power-side flows (`H_FLOOR`).** Recommended: **1 hour**,
  the shortest commercial grid battery (Modo prices from 1 h). Nothing depends
  on it today, since there are no excluded power-side flows.
- **Q2. Foundation life.** A concrete pad can outlast its battery and be
  reused at repowering. Recommended: **spread it over the battery's 15 years**.
  That's conservative, and it avoids assuming a second battery the study
  doesn't model.
