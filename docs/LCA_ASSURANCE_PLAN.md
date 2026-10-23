# LCA assurance plan — 22 Oct 2026

> **Status, end of 22 Oct 2026.** Built the same day, in this order: the map
> checker's fingerprint and pytest (3.1), the style test and sheet (4.1–4.2),
> the register, `cutoff.py`, the rule-3 knob and the audit hook (1.1–1.4),
> ten source ledgers and three style read-throughs by independent readers
> (2.4, 4.3; kept in `docs/source_ledgers/` and `docs/STYLE_SWEEP.md`), the
> corrections they demanded (three stacks per Gerloff unit, the 250 km leg,
> the SMR-CCS capture and closure, the dropped electricity credits, Voß's
> graphite legs, Leng's installation rows and switchyard civils, two solar rows
> back out, nineteen zero-GWP rows back in, the tank's forming), the rule-1
> failures carried as estimates or built as rows (1.5), every database rebuilt
> and every coefficient re-scored, the grid series re-scored, ASSUMPTIONS §8
> generated, the map rebuilt with the register under every functional unit
> (3.2–3.3). Rule 3 was solved on 23 Oct (both reference cases, both anchors,
> every still-excluded flow at its upper estimate) and **passes**: the same
> technologies are built and no capacity moves by more than 3 %
> (ASSUMPTIONS §8; `scripts/cutoff_rule3.py`). The booster station's
> construction machinery, first left out as not separable, is carried as
> Leng's own figure pro-rated to the switchyard, because it is sourced and
> inside the boundary. Open: D3 iridium (parked), Hunziker 2020 not held, a
> switchgear EPD (TODO.md).

Four jobs, asked for together on 22 Oct: test the cut-off rule, check every
LCA against its source documents so nothing is left out, bring the LCA map
back to the model and prove it, and sweep every inventory for the approved
structure — clear, concise, exclusively in the Python modules. They are one
job in four parts, because the rule stated on 20 Oct (`CUTOFF_RULE_PLAN.md`)
has two halves and each half is tested differently:

- **Sourced, in-boundary flows are always in.** That is a completeness claim,
  and the only way to test it is to read each source again and account for
  every row. Part 2.
- **Unsourced flows stay out only if they pass 1 % / 5 % / no design change.**
  That is arithmetic on a register that does not exist yet. Part 1.

The map (Part 3) then has to show both halves, and be checked against the
live model rather than trusted. The structure sweep (Part 4) is what makes
Parts 1–3 checkable at all: the source ledger parses the modules, the register
ties to their scope dicts, and the map reads their rows, so every module has
to be in the one shape those tools expect. The shape is written down in
`docs/LCA_STYLE.md` (22 Oct).

Effort: XS < 1 h, S ≈ half a day, M ≈ 1–2 days, L > 2 days.

## Where things stand (measured 22 Oct)

**Cut-off rule.** The rule is written, the boundary is settled (end-of-life,
delivery to site, the genset), and the 21 Oct restores are built. Nothing
measures the rule: there is no register (`optimiser_lca/exclusions.py` does
not exist), no checker (`optimisation/cutoff.py` does not exist), no rule-3
run. `CUTOFF_RULE_PLAN.md` §2B holds a hand-made estimate table with two known
failures (tank forming 12–50 %, grid-connection switchgear and civils) and
several rows marked "to score" or "to confirm".

**Sources.** `docs/SOURCE_DIFF.md` (21 Oct) is one pass by five parallel
readers over the eight inventory modules' documents. It found twelve dropped
rows and nine substitutions; the restores were built the same day. Three
limits: the restores were implemented *after* the read, so their printed
amounts have not been checked back against the documents; the readers'
row-by-row working files lived in a session scratchpad and are gone, so the
diff cannot be re-run or audited; and the diff covered only the transcribed
inventories, not wind (an ecoinvent dataset plus Vestas and DESNZ parameters),
the grid (`gb_grid.py`, `grid.py`), the bought-hydrogen assembly
(`h2_prices.py`), or the scalar parameters every coefficient module carries
(lives, load factors, duty hours, usable fraction, replacement fractions).
Open from the diff: D2 (Leng's booster-station civils), #11 (SOEC La₂O₃ and
SrCO₃ amount), S3 (iridium, parked), and the Hunziker 2020 check behind S1.

**Map.** Built 15 Oct (v17, 597 checks clean). Running
`scripts/check_lca_map.py --no-brightway` today gives **568 checks passed, 29
problems**:

| Section | Problems | What |
|---|---|---|
| 1 LP terms | 9 | every coefficient the restores moved: battery energy 7,241 → 7,489; fuel-cell BoP 44,325 → 50,807; solar step-ups 273 → 420; wind step-ups 279 → 329; solar plant +1.4 %; both facility constants; the two container step-ups by 0.15 % |
| 3 Foreground exchanges | 19 | activities whose rows changed: the Jasper block and in-China lorry legs (11 battery activities), the Z-PV-239 and Z-PV-238 rows (mounting, plant, solar step-ups), Leng's pads (wind step-ups), Zhang's construction phase, the two nitrogen rows, the AE steel correction, the fibreboard fix |
| 8 Every activity shown | 1 | `solar_inverter_stepup_replacements_30y_per_mwp` (Smith A15, built 21 Oct) has no box |

Two smaller things the run showed: the checker crashes on a cp1252 console
(`UnicodeEncodeError` on "→") before it prints its first failure — run it with
`PYTHONUTF8=1` until fixed — and the published artifact
(`https://claude.ai/artifact/NrzMeByK24RpbGosfc5aSE`) is the 15 Oct snapshot.
The staleness test offered on 15 Oct was never built, which is why nothing
went red when the inventories changed.

**Repository.** 39 modified and 17 untracked files since the last commit
(`70d0f0c`), including every plan, the source diff, the map scripts and the
restores. **Step 0 of this plan is a commit checkpoint** (no push), so the
work below has a base to diff against.

## Part 1 — Test the cut-off rule

Steps 1, 3, 4, 5 and 6 of `CUTOFF_RULE_PLAN.md`, made concrete. Step 2 of
that plan (estimate every exclusion) is largely done; what is left of it is
1.3 below.

### 1.1 The register (S)

- [ ] `optimiser_lca/exclusions.py`, Python only, one `Exclusion` per flow:
      `technology` (a `dc_model.CHAINS` key, or `"facility"`, `"grid
      electricity"`, `"bought hydrogen"`), `flow`, `kind` (`cutoff` tested;
      `boundary` reported), `side` (`energy` or `power`, battery only; see
      `BATTERY_CUTOFF_ANALYSIS.md` §2), `central` and `upper` in the
      technology's denominator unit, `unit`, `method` (`transcribed`,
      `mass_x_factor`, `assumed`), `factor_identity` (the ecoinvent dataset
      the factor was scored on, as a `Process` identity, so it can be
      re-scored), `scored_on` (date), `source`, `note`, `status` (`excluded`,
      `included_estimate`, `included_inventory`), and `where` — the module
      and scope-dict key or docstring that currently states the exclusion.
- [ ] Seed it from `CUTOFF_RULE_PLAN.md` §2 and `SOURCE_DIFF.md`. The
      unsourced list as it stands:

      | Technology | Flow | Kind |
      |---|---|---|
      | battery | processing materials (NMP make-up, argon, N₂, air) | cutoff, energy |
      | battery | site installation (crane, commissioning diesel) | cutoff, energy |
      | battery | container switchgear | cutoff, power |
      | fuel cell | container switchgear | cutoff |
      | fuel cell | BoP assembly energy (Usai give none) | cutoff |
      | hydrogen tank | forming of the vessel steel (rolling, welding) | cutoff — expected to fail |
      | hydrogen tank | valves, pipework, compressor hardware | cutoff |
      | wind | step-up switchgear | cutoff |
      | wind | step-up transformer replacement rate (Leng publish none) | cutoff |
      | wind | step-up transformer factory energy (Leng publish none) | cutoff |
      | solar | step-up switchgear | cutoff |
      | grid connection | switchgear, protection, bay | cutoff — expected to fail |
      | grid connection | bay civils | cutoff — expected to fail; D2 decides what Leng's venue covers |
      | grid connection | intake transformer factory energy (Leng publish none) | cutoff |
      | facility | internal MV/LV distribution | cutoff |
      | electrolyser (SOEC) | La₂O₃ and SrCO₃ in the electrolyte layer — sourced, amount not held, so estimated and tested like an unsourced flow (#11) | cutoff |
      | electrolyser | anything else `hydrogen.py` leaves out of Gerloff — walk it | to list |
      | all | end-of-life | boundary |
      | all | delivery to site, per technology (Jasper's China–Germany rows, Smith A14 rail/lorry/sea, Zhang's transportation phase, Leng's to-site transport, bought-H₂ haulage) | boundary |
      | facility | standby generator (Zhang's 8.6e6 MJ, scored and reported by `data_centre.py`) | boundary |

      Confirm before adding: the TODO line says "wind/battery transformer
      factory energy (unsourced)". The battery and fuel-cell container unit is
      the IEA PVPS recipe taken whole, process energy included
      (`DATA_GAPS.md`, *Balance of plant judged negligible*), so only the two
      Leng units lack factory energy. Fix the TODO wording with the register.
- [ ] A test that ties register and modules together both ways: every scope
      value containing `EXCLUDED` (`bess.BESS_SCOPE`, `upv.UPV_PV_SCOPE`,
      `bess.CSS_EXCLUDED`) and every "Excludes …" / "Still missing" sentence
      the docstrings carry (`h2_tank`, `fuel_cell`, `stepup_transformers`,
      `data_centre`) is named by an entry's `where`, and every `where`
      resolves. A new exclusion cannot be written without a register row.
- [ ] Leave the scope dicts and docstrings as they are; they describe, the
      register measures.

### 1.2 Score what is still estimated (S, Brightway)

- [ ] `scripts/score_exclusions.py`: for every `mass_x_factor` entry, resolve
      `factor_identity` and score it on IPCC 2021 GWP100; print the table.
      Numbers go into the register as literals with `scored_on`, the way every
      other inventory figure is written, not into a cache file.
- [ ] Rows to score rather than reason from Teffera's masses: switchgear
      (battery, fuel cell, wind, solar, grid connection); tank forming
      (`market for sheet rolling, chromium steel` on the vessel mass as the
      lower bound, `market for metal working, average for chromium steel
      product manufacturing` as the upper); tank valves and pipework (mass ×
      factor on a stated valve count); grid bay civils (concrete and rebar for
      a bay, or Leng's outdoor venue per MW under D2); facility distribution
      (the 4 Sep bound re-expressed per facility-year); SOEC La₂O₃/SrCO₃ (a
      stack composition from the literature, graded ASSUMED).
- [ ] A Brightway-backed test (skipped without the project) that re-scores
      every `factor_identity` and holds the register's literal within 1 %, so
      a database move cannot leave a stale factor.

### 1.3 Rules 1 and 2, automatically (S)

- [ ] `optimisation/cutoff.py`: `check(tech, series=None) -> DataFrame`, one
      row per `cutoff` entry (technology, flow, denominator, upper share,
      verdict) and one row per technology (summed share against 5 %).
      Denominators from the `Tech` as `CUTOFF_RULE_PLAN.md` tabulates them;
      battery energy-side flows at the ceiling `f / gwp_batt_e`, power-side by
      break-even duration against `H_FLOOR = 1 h` (Q1 of the battery note);
      fuel cell at calendar replacements only (Q2).
- [ ] Wire it into `audit.py` so every audit run prints it, and add the
      per-run battery duration hook: flag any solved `cap_batt_e / cap_batt_p`
      below the largest break-even among excluded power-side flows.
- [ ] `tests/test_cutoff.py`, fast: no entry with `status="excluded"` fails
      rule 1, and no technology's excluded total fails rule 2. Red on day one
      (tank forming, grid connection) by design; green once 1.5 is done.
- [ ] `python optimisation/cutoff.py --write` regenerates `ASSUMPTIONS.md`
      *8. Cut-off rule*: the rule, its sources, the boundary list, the table,
      and the rule-3 result from 1.4. Generated, like `VALIDATION.md`.

### 1.4 Rule 3, in the optimiser (S, plus solve time)

- [ ] `build_tech(..., cutoff=None | "upper" | "central")`: adds each
      `cutoff` entry's estimate onto its technology's coefficient
      (`gwp_wind`, `gwp_tx_*`, `gwp_batt_e`/`gwp_batt_p`, `gwp_ely`,
      `gwp_tank`, `gwp_fc_bop_per_mw`, `gwp_grid_per_mw`,
      `dc_fixed_gwp_per_year`). `None` is today's model, bit for bit.
- [ ] `sensitivity.CARBON_KNOBS["cutoff"] = ["upper"]`; run `islanded_h2` and
      `london_grid` at both anchors (four extra solves). Write
      `sensitivity_cutoff_*.csv`.
- [ ] The design-change test (Q4 of the cut-off plan): at both anchors the
      same technologies are built and no capacity moves by more than 5 %.
      Record pass/fail per case in ASSUMPTIONS §8.

### 1.5 Resolve what fails (M)

A flow that fails is included; it is not argued away.

- [ ] **Tank forming**: build it as an inventory row in `h2_tank.py` (sheet
      rolling on the vessel mass, graded ASSUMED; metal working kept as the
      sensitivity), delete the register entry's `excluded` status. Rebuild
      `h2_tank`, refresh coefficients, update the pinned numbers in
      `tests/test_coefficients.py`.
- [ ] **Grid connection**: Q7 is the user's call. Recommended: carry
      switchgear and bay civils as `included_estimate` at the central
      estimate (Teffera's masses × scored factors, ASSUMED), take Leng's
      outdoor venue per MW of connection if D2 goes that way, state in
      ASSUMPTIONS that the connection is a floor, and let the rule-3 run show
      it cannot change a design. The alternative (fold the connection into
      "grid electricity" as one technology) hides the failure rather than
      resolving it.
- [ ] **Facility distribution**, if it fails rule 1: include at the central
      estimate.
- [ ] Anything rule 3 turns up: the entries that drive the design change go in
      the same way.
- [ ] Record each in `DATA_GAPS.md` (status) and `SOURCES.md` (where a number
      moved); regenerate ASSUMPTIONS §8.

### 1.6 Close (XS)

- [ ] Delete the cut-off item from `TODO.md`; move its open sub-items (D2,
      #11, Hunziker) to Part 2's list if still open.
- [ ] One methods paragraph for the paper: the rule, PAS 2050 / Vestas §3.3 /
      ISO 14044 (check the PAS 2050 and ISO wording at the primary before
      citing), the three boundary choices, the rule-3 result.
- [ ] The map shows the register (Part 3).

## Part 2 — Every LCA against its source, so nothing is left out

The guarantee wanted is: *every row of every held source is either in the
module at its printed amount, or listed as a boundary item, a substitution, or
not applicable — and every row in a module says where it came from.* The 21 Oct
diff asserted this once by hand. This part makes it regenerable, extends it to
the inventories the diff did not cover, and keeps the evidence.

### 2.1 The documents (XS)

All held, on OneDrive under `DC optimiser/`:

| Source | File | Machine-readable |
|---|---|---|
| Jasper 2026 (battery container, racks, cooling, fire suppression, container transformer) | `sources/jasper grid storage lca.xlsx` (+ pdf) | yes |
| Voß 2025 (LFP cell) | `sources/voss supplementary materials/d5ee00415b1_suppl.txt`, two pdfs | partly |
| Smith 2024 (utility PV, A1–A16) | `sources/smith life-cycle-inventory.md` = `optimisation/data/smith-nrel-2024-life-cycle-inventory.md` (+ pdf) | yes |
| IEA PVPS T12-33:2026 (mounting Z-PV-239, transformer Z-PV-276, station Z-PV-238) | `optimisation/data/IEA-PVPS-T12-33-2026-LCI-PV-SupplyChains.xlsx` (shipped) | yes |
| Usai 2021 (fuel-cell BoP) | `sources/usai supplementary materials/*.pdf`, `*.xlsx` | partly |
| Babatunde 2024 (fuel-cell stack) | `data centre reading/fuel cell/hydrogen-3005656-supplementary.pdf` | no |
| Gerloff 2021 (AE / PEM / SOEC bills) | `sources/gerlof electrolysis lca bop 200.docx`, pdf; the user's SimaPro exports in `Documents\brightway\*.XLSX` | partly |
| Hermesmann & Müller 2022 (SMR, SMR-CCS, pyrolysis) | SimaPro exports `smr ccs.XLSX`, `ccs.XLSX`, …; paper | partly |
| Zhang 2025 (facility) | `data centre reading/zhang virginia dat/*-mmc1.xlsx` (S1 inventory), mmc2, mmc3 | yes |
| Gandiglio 2022 (tank) | `sources/gangliano fuel cell hydrogen tank*.pdf` | no |
| Leng 2026 (wind step-ups, grid intake; S1 materials, S2 transport, S3 civils) | `sources/Leng supplementary.pdf`, paper | no |
| Mehmeti 2018 (SOEC heat) | `sources/mehmeti soec heat.xlsx`, pdf | yes |
| Vestas V162 (wind parts fraction, cut-off wording), Teffera 2021 (switchgear masses) | `sources/vestas lca 6.2MW wind.pdf`, `sources/teffera ethiopia wind farm LCA.pdf` | no |

- [ ] `dc_config.SOURCE_DOCS_DIR` (default the OneDrive `DC optimiser/sources`
      folder, overridable by environment variable). Tests and scripts that
      read a document skip when it is absent, and say so.
- [ ] Decision for the user: copy the machine-readable files that may be
      redistributed (Jasper's SI is on Zenodo; the IEA workbook is already
      shipped) into `optimisation/data/sources/` as evidence, or leave all on
      OneDrive. Journal supplementary files (Zhang's mmc1, Usai's) have no
      clear licence to redistribute, so the default is: leave them, reference
      them.

### 2.2 The row ledger, generated from the modules (S)

- [ ] A locator convention for every exchange `note`: it begins with where
      the row is in the source — `"Jasper SI liquid r17"`, `"Smith A12"`,
      `"Z-PV-276 Table 49"`, `"Usai Table 1"`, `"Zhang S1 construction"`,
      `"Leng S1"`, `"Gerloff SI Fig. 1"` — or with `ADDED`, `ASSUMED`,
      `DERIVED` for rows that are not a source row. Most notes already do
      this informally; make it the rule and fix the ones that don't.
- [ ] `scripts/source_ledger.py` walks `build.inventories()` and writes
      `docs/SOURCE_LEDGER.md`: one table per activity, every row with its
      locator, printed amount, unit, module amount (after `scale`) and grade.
      Rows with no locator are listed at the top as *unaccounted*. This is the
      module → source direction: nothing in a module without a stated origin.
- [ ] A fast test: zero unaccounted rows.

### 2.3 Source → module, where the source is machine-readable (M)

- [ ] `tests/test_sources.py`, skipped without `SOURCE_DOCS_DIR`: parse the
      source table and assert, row by row, that each source row has a
      **disposition** — in the module at its printed amount (within rounding),
      `boundary`, `substituted` (naming the substitute), or `not applicable`
      (with a reason) — and that no source row is missing one. Dispositions
      live in the module as Python (`SOURCE_ROWS_OUT = {...}` beside the
      existing scope dicts), never in a data file.
- [ ] Sources covered this way: Jasper's liquid sheet (`bess.py` and the
      container transformer in `stepup_transformers.py`), Zhang's S1
      (`data_centre.py`), IEA Tables 49 and 50 and Z-PV-239
      (`stepup_transformers.py`, `upv.py`), Smith A1–A16 (`upv.py` and the
      20 deferred rows, each with its zero-GWP reason), Mehmeti Table 1
      (`electrolysers.py` heat row), Usai's results workbook, Voß's text
      tables where they parse.
- [ ] Where a module already reconciles to a printed total (the IEA bill to
      5,670 kg, Leng's box unit to 282,343 kg, the main unit to 71,458.6 kg,
      Smith's 290 scientific-notation values), keep those tests and point the
      ledger at them.

### 2.4 Source → module, where the source is a PDF (M, parallel readers)

- [ ] One independent reader per document, each given the PDF and the
      module, each producing a row-by-row ledger in the same format as 2.3
      and saving it to `docs/source_ledgers/<source>.md` — the evidence the
      21 Oct pass did not keep. Documents: Leng S1/S2/S3 (both transformers,
      the pads, the booster station), Babatunde Table S1, Gandiglio Table 5,
      Gerloff SI Figs 1–5 and Tables 3–6 (against the SimaPro exports as
      well), Hermesmann Tables 2–3 and §3.2.3–3.2.4, Usai Table 1, Voß S5,
      S31, S32, S35–S37 and §3.1.3, Smith's appendix against the
      transcription, Vestas §3.3 (the rule's wording), Teffera Table 5.
- [ ] Reconcile each ledger against 2.2's module ledger; every difference is
      a restore, a substitution to state, or a wrong claim to fix.
- [ ] Re-check the 21 Oct restores at their printed amounts (#1–#10, #12,
      S4–S7 of `SOURCE_DIFF.md`): they were written after the read.

### 2.5 Parameters and the three untranscribed inventories (S)

The diff checked rows. Coefficients also depend on scalars, and three
inventories are not transcriptions at all.

- [ ] Every scalar graded `transcribed` in `optimisation/*.py` and
      `optimiser_lca/*.py` (lives, load factors, duty hours, usable fraction,
      `FC_KW_PER_CONTAINER`, replacement fractions, Reg. 548/2014 losses,
      Z-PV counts, `H2_GWP100`, `VOLL_KGCO2E_PER_MWH`, Smith's A15 30.2 %)
      checked against its `SOURCES.md` row and the document, in the same
      ledgers.
- [ ] **Wind** (`renewables.py`): the ecoinvent dataset decomposed, the
      Vestas servicing and overhaul shares, DESNZ/Arup life and load factor —
      every in-boundary component of the source present (foundation, road,
      cabling, step-up handled by `stepup_transformers`), nothing dropped by
      the restatement.
- [ ] **Grid** (`gb_grid.py`, `grid.py`): each source's ecoinvent dataset and
      the import-attribution fit against what the basis id `055e53f4b11b`
      fixes; the delivery terms against ecoinvent's own network datasets.
- [ ] **Bought hydrogen** (`h2_prices.py`, `hydrogen.py`): the green
      assembly's bases and the trailer compression; grey, blue and turquoise
      from Hermesmann with the D1 decision (no credit, full allocation)
      stated where the number is.

### 2.6 Open items from the 21 Oct diff (XS–S, decisions)

- [ ] **D2** Leng's booster station: user decision. Recommended in
      `SOURCE_DIFF.md`: the outdoor venue per MW of connection, the three
      buildings treated as covered by Zhang's facility building (a stated
      substitution). Lands in `stepup_transformers.py` as civils on the
      intake, scored apart.
- [ ] **#11** SOEC La₂O₃/SrCO₃: estimate from a stack composition source,
      graded ASSUMED, on the register (1.1) until Gerloff's sheet is found.
- [ ] **S3** iridium: stays parked by the user; the platinum proxy stated in
      `hydrogen.py` and `SOURCES.md`.
- [ ] **Hunziker et al. 2020**: get the paper; confirm the on-load tap changer
      behind Jasper's electronics row, which is what S1's representativeness
      argument rests on.

### 2.7 The guarantee, written down (XS)

- [ ] `SOURCE_DIFF.md` gets a dated header block, regenerated by
      `source_ledger.py`: sources held, rows in each, rows in / boundary /
      substituted / not applicable, unaccounted module rows (must be 0), and
      the test that holds each count. The 21 Oct narrative stays below it as
      history.
- [ ] `DATA_GAPS.md` rows for anything 2.3–2.5 turn up.

## Part 3 — The map, current and proven

### 3.1 Make staleness visible (S)

- [ ] Fix the checker's console encoding (`sys.stdout.reconfigure(encoding=
      "utf-8")` at the top of `check_lca_map.py`) so it prints on Windows
      without `PYTHONUTF8=1`.
- [ ] A fingerprint in `lca_map.json["meta"]`: a hash over every inventory's
      static tuples (what `common.check()` sees, no Brightway), the
      coefficient CSV, `grid.sources_id()`, the register (Part 1) and the
      git `HEAD`. The checker recomputes it and fails with "rebuild the map"
      when it differs — a single check that would have gone red on 20 Oct.
- [ ] `tests/test_lca_map.py`: runs the checker's no-Brightway sections (1,
      2, 2b, 3, 5, 6, 7, 8 and the fingerprint) as one pytest, skipped if
      `lca_map.json` is absent. The map is then held by the suite, not by
      memory.
- [ ] The HTML must carry the JSON it claims: a check that the blob inlined
      at `__DATA__` in `lca_map.html` hashes to `lca_map.json`.

### 3.2 Show what changed since 15 Oct, and what Parts 1–2 add (S)

- [ ] `solar_inverter_stepup_replacements_30y_per_mwp` as its own box under
      the solar step-up stage, with the A15 fraction and the per-year charge.
- [ ] Civils shown apart where the modules score them apart: Jasper's block
      on the container, the Z-PV-238 station building, Leng's pads, and
      Leng's venue if D2 takes it — each a `part` with its own contribution,
      not folded into the unit.
- [ ] Zhang's construction phase as a stage under the facility; the two
      nitrogen rows; the AE steel and fibreboard corrections appear through
      the exchange re-read.
- [ ] Substitutions as notes carrying their sensitivity value: S1 (Jasper's
      recipe, +72 % on the unit; battery +2 %, fuel cell +4 %), Smith's A11
      (solar step-up ×3–4), fixed tilt for the tracker, the Chinese cell
      factory. One line each, on the box substituted.
- [ ] **The cut-off register** under every functional unit: a group "Left
      out, and how big" listing each register entry with kind, upper share
      and verdict, boundary items last; `included_estimate` entries shown as
      a `part` with grade ASSUMED. This is `CUTOFF_RULE_PLAN.md` step 6.
- [ ] **The source ledger** on every foreground box: a badge "N source rows:
      n in, b boundary, s substituted" from 2.2–2.4, and the locator on
      every exchange row in the side panel.
- [ ] The one-box-per-process rule (15 Oct) as a permanent checker section
      rather than a one-off scan.

### 3.3 Checker additions (S)

- [ ] 9: every register entry appears under its technology's functional unit
      with the share `cutoff.check()` computes; every boundary item is listed
      once.
- [ ] 10: one-box scan — no `part`/`stage`/`fu`/`foreground` with exactly one
      child of the same kind.
- [ ] 11: fingerprint (3.1).
- [ ] 12: HTML blob equals JSON (3.1).
- [ ] 13: after publishing, read the artifact back and compare its embedded
      `meta.generated` and fingerprint with the local file. Manual, recorded
      in the run log.

### 3.4 Rebuild and republish (XS each, ~10 min of machine time each)

Twice. Once now, so the map stops showing 15 Oct numbers while Parts 1–2 run;
once at the end, after the last inventory change. The sequence is the same:

1. `python -m optimiser_lca.build` if any inventory changed (not needed for
   the interim rebuild: the 21 Oct restores are built).
2. `python optimisation/coefficients.py`.
3. Re-run the reference cases: `scripts/run_dc_scenarios.py` for
   `option_summary.csv`, and the sensitivity sweeps for the CSVs the TODO
   calls stale (`sensitivity_stepups_*.csv`, plus `sensitivity_cutoff_*.csv`
   from 1.4).
4. `python scripts/build_lca_map.py` (~7 min, Brightway, `MKL_THREADING_LAYER=TBB`).
5. `python scripts/check_lca_map.py` with Brightway: 0 problems, or stop.
6. Republish to the same artifact URL (read it first, then publish with
   `url`), read it back (3.3 §13).
7. Update the lca-map notes with the version and check count.

The ecoinvent sharing caveat is unchanged: the page embeds ~455 dataset
scores, so it stays private until a stripped version is built.

## Part 4 — The structure sweep: every LCA in the approved shape

The approved shape is the one `optimiser_lca/common.py` defines and the
modules follow: one module per LCA, a docstring that states source, functional
unit and boundary, graded parameters, `processes` and `flows` tables with
pinned identities, one `Activity` per source table with rows as printed, an
`inventory()` — and nothing read from a JSON, CSV, YAML or spreadsheet to build
an exchange. `docs/LCA_STYLE.md` writes it down, with the rules a test can
hold in bold and a review checklist for the rest.

**Why it belongs in this bundle.** The source ledger (2.2) parses each
exchange's note for its locator; the register (1.1) ties to the modules' scope
dicts; the map (3.2) shows the note beside every number. If a module strays
from the shape, those tools silently see less of it. The sweep runs first so
the rest measures a known structure.

**What the survey found (22 Oct), to seed the sweep:**

| Module | Slip | Rule |
|---|---|---|
| `data_centre.py` | the activity `comment` still says construction energy and water are "excluded by scope choice"; the three rows have been in since 21 Oct | §4, comments describe the activity as it is |
| `data_centre.py` | several `Process` entries have no `why` where the pick is a choice (`reinforcing_steel` GLO, `structural_steel` hot-rolled for "structural steel") | §3, `why` where the pick is not the source's row |
| `registry.py`, `hydrogen.py` | codes `ae_hermesmann_1unit`, `pem_con_hermesmann_1unit`, `soec_con_hermesmann_1unit` and the `*_op_hermesmann_*` codes name the wrong author (Gerloff's bills) | §5, names say what the thing is; renaming is a rebuild (decision below) |
| `upv.py` | rows to 159 characters; the 20 deferred Smith rows are listed in `optimisation/data/UPV-DEFERRED-ISSUES.md` as well as (or instead of) at the foot of their activities | §4–5, dropped rows at the foot; one place |
| all | exchange notes are locator-first by habit, not by rule; some start with the description | §4, locator-first |
| `optimiser_lca/` | two file reads (`gb_grid.check_against_series`, `grid.py`'s basis record) — both checks, both to be allowlisted explicitly | §1 |

### 4.1 The style sheet (XS — done 22 Oct)

- [x] `docs/LCA_STYLE.md`: where things live, the module order, the two
      tables, activities and rows, clarity rules, the checks a module must
      pass, a review checklist.
- [ ] Link it from `optimiser_lca/__init__.py`'s docstring and `README.md`
      so a new module starts from it.

### 4.2 The mechanical sweep, as a test (S)

`tests/test_lca_style.py`, AST-based, no Brightway, over every module in
`build.MODULES` plus `registry.py` and `common.py`:

- [ ] **No data loaders.** No import of `json`, `csv`, `openpyxl`, `yaml`;
      no `pandas.read_*`; no `open(` or `.read_text(` — except the two
      allowlisted check functions, named in the test with their reason. No
      string literal ending `.json`, `.csv`, `.xlsx`, `.yaml` outside
      docstrings and comments, except the allowlist.
- [ ] **Module order and parts.** A module docstring with a `Source and
      scope` section and a bold functional unit; module-level `processes`,
      `flows`, `activities`, `inventory()`; the `# ===` section rules in the
      order of `LCA_STYLE.md` §2.
- [ ] **Tables.** Every `Process` has `identity` and `query`; `why` present
      whenever `pick != 0` or the identity name differs from the key's
      family (heuristic, with a per-module allowlist for the source's own
      names); every `Flow` has a two-element identity with a categories
      tuple; keys `snake_case`.
- [ ] **Activities and rows.** `code=R.<NAME>` (an attribute of `registry`,
      never a literal); every technosphere and biosphere row a four-element
      tuple with a non-empty note; the note begins with a locator from a
      per-module list (`Jasper SI`, `Smith A`, `Z-PV-`, `Table S`, `Usai`,
      `Zhang S1`, `Leng S`, `Gerloff`, `Hermesmann`, `Gandiglio`, `IEA`) or
      with `ADDED`, `ASSUMED`, `DERIVED`; `scale != 1` only with a non-empty
      `scale_note`; one `Activity` constructor per source table, loops only
      inside a named helper with named parameters.
- [ ] **Parameters.** Every module-level numeric constant's line or
      preceding comment block carries `TRANSCRIBED`, `DERIVED` or `ASSUMED`
      (or is derived by arithmetic from ones that do).
- [ ] **Outside the package.** `dc_config.py` defines no `Activity`,
      `Process` or `Flow` and no numeric constant that an `optimiser_lca`
      module reads into an exchange (import graph check); the notebook
      `2.tech_lca_foreground.ipynb` contains no `Activity(`, `Database(` or
      `.write(`; `optimisation/data/` holds only the allowlisted evidence
      files; no `*_cache.json` is imported by `optimiser_lca/`.
- [ ] **Clarity.** No `TODO`/`FIXME` in a module; no commented-out code
      (lines that parse as Python after stripping `#`, excluding the
      dropped-row foot comments, which carry an amount and a reason); prose
      lines ≤ 100 characters, row lines ≤ 140; no module-level constant
      defined twice with the same value in two modules (`check()` holds them
      equal instead).
- [ ] Red on day one for the slips above; green once 4.4 is done.

### 4.3 The read-through (S, one module at a time)

- [ ] Each of the eight modules, plus `registry.py` and `common.py`, read
      against the checklist in `LCA_STYLE.md` §7 by someone who did not
      write it (a reader per module, in parallel with Part 2's PDF read,
      which is already opening the same modules). Findings go in one table
      in `docs/STYLE_SWEEP.md`: module, line, rule, fix.
- [ ] The read-through also judges what no test can: does the docstring say
      what a reader of the numbers needs and no more; is every substitution
      stated once, where the substituted row is; does the module read top
      to bottom without the notebook.

### 4.4 Fixes (S–M)

- [ ] Apply every finding from 4.2 and 4.3 that does not change a number:
      comments, `why`s, note locators, line wraps, duplicated constants,
      the deferred-rows duplication (foot comments win; the `.md` becomes a
      pointer or goes).
- [ ] **Code renames** (the Hermesmann/Gerloff codes) are a user decision:
      renaming an activity code rewrites its database and every cache and
      test that names it. Recommended: rename in the same rebuild as Part
      1's inventory changes, so the databases are rebuilt once.
- [ ] Nothing in 4.4 may change an exchange amount. Run
      `tests/test_optimiser_lca.py` after each module: `check()` and the
      written-database comparison must pass unchanged (a style fix that
      alters what Brightway holds is not a style fix).
- [ ] Regenerate the source ledger (2.2) afterwards; the locator rule is
      what it parses.

### 4.5 Keep it held (XS)

- [ ] `tests/test_lca_style.py` stays in the suite; `python -m
      optimiser_lca.build --check` calls the same checks so a build refuses
      a module that strays.
- [ ] `LCA_STYLE.md` gets a line in `optimiser_lca/__init__.py` and in the
      LCA map's method box, so the shape is stated where the LCAs are read.

## Order

0. Commit checkpoint (user's call; no push).
1. **3.1 and the interim rebuild** (3.4): half a day; the map is honest again
   and the suite goes red if it drifts. **4.2** (the style test) the same
   day: it is small and everything after it reads the modules.
2. **4.3–4.4** (the read-through and the no-number fixes) in parallel with
   **1.1–1.3** (register, scoring, checker) and **2.1–2.2** (documents dir,
   module ledger). The ledger is generated after 4.4, so the locator rule is
   in force when it first runs.
3. **2.3–2.5** (the source re-read) in parallel with **1.4** (rule-3 run).
   The readers and the sweeps can run at the same time; the readers take the
   style checklist with them (4.3).
4. **2.6** decisions (D2, #11) and **1.5** resolution, which depend on each
   other for the grid connection. The code renames (4.4) go in this rebuild.
5. **2.7**, **1.6**, **3.2–3.3**, **4.5**.
6. Final rebuild and republish (3.4).

Roughly: Part 1 three to four days, Part 2 two to three with parallel
readers, Part 3 one to two plus two rebuilds, Part 4 one to two with the
readers. Steps 2 and 3 are where parallel work pays.

## Decisions for the user

- **D2** (Leng's booster station) and **Q7** (how the grid connection carries
  switchgear and civils): recommendations above; they decide what 1.5 builds.
- **Q1** `H_FLOOR` = 1 h and **Q4** (same technologies, capacities within 5 %)
  as recommended in the cut-off plan, unless you want them different.
- **Where the source files live**: OneDrive by reference (default) or
  copied into `optimisation/data/sources/` where the licence allows.
- **The PDF re-read** (2.4) is a second parallel read of about a dozen
  documents. It is the only way to re-establish the 21 Oct claim with
  evidence that persists; say if you would rather it be done one source at a
  time.
- **Code renames** (4.4): the `*_hermesmann_*` codes for Gerloff's
  electrolysers. Rename in the Part 1 rebuild, or leave and note it in the
  registry.
- **Commit** before starting (step 0).
