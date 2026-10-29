# Connection tier plan — 19 Oct 2026

A plan for making the grid connection's network charges follow the connection
the optimiser actually builds, and for replacing the assumed 100 MW
transmission threshold with GB's published voltage rule. Raised by the
supervisor's point 4 (19 Oct): if the best connection lands either side of
100 MW, the network charges change a lot.

Effort: XS < 1 h, S ≈ half a day, M ≈ 1–2 days, L > 2 days.

**Status, 28 Oct 2026: steps 1–4 done**, with two departures. The Scottish
boundary is ES216's 33 kV ceiling (120 MVA) as an assumed proxy; no SPEN or
SSEN standard could be opened, and no second DNO standard corroborates the
240 MVA (NGED's Nov 2025 data-centre study does, informally). The post-solve
band check lives in the slow test rather than `audit.py`. Step 5's before/after
is in `docs/COST_PLAN.md`.

## The problem

The optimiser chooses the connection size (`cap_grid`), but only up to a cap
the user sets (`site.connection_limit_mw`), or one derived at 1.5× load
(`sites.CONNECTION_HEADROOM_ASSUMED`). The tier and the fixed band are
currently read from that cap, not from the size chosen
(`dc_inputs.build_series`, lines 139–155):

| Charge | Read from | Code |
|---|---|---|
| Tier: transmission or distribution | the **cap** | `network_charges.is_transmission_connected(conn_mw, …)` |
| TNUoS demand residual (TDR) band, £/site/year | the **cap** | `network_charges.tdr_band_for(conn_mw, …)` |
| DUoS on or off (capacity, unit and fixed charges) | the **tier**, so the cap | `network_charges.import_charges(…, transmission_connected=)` |
| TNUoS locational + DUoS capacity, £/MW/year | the **built size** | `cost_grid_per_mw_year · cap_grid` in `dc_model` |

So the per-MW charges follow what is built, while the tier and the fixed band
follow the cap. Two examples:

- **London, 100 MW IT, PUE 1.5.** The load is 150 MW and the cap is 225 MW, so
  the site is transmission-connected and on T-Demand4 (£4.67 m/year). The
  site keeps both even if the optimiser builds an 80 MW connection.
- **An EHV distribution site.** The cap puts it in EHV3, but the optimiser
  builds a connection small enough for EHV2, so it pays EHV3's £575k instead
  of EHV2's £271k.

The threshold is also a guess. `TRANSMISSION_MW_ASSUMED = 100.0` is graded
ASSUMED in its own comment ("a network-design outcome, not a tariff rule"), and
`SOURCES.md` contradicts it by calling 132 kV distribution "the common case for
a ~100 MW data centre". `DATA_GAPS.md` calls it the most consequential
assumption in the charging stack.

`TODO.md` already lists the band half of this ("TDR is banded on the
connection ceiling while DUoS bills `cap_grid`"). This plan closes that item
together with the threshold.

## The fix, in one sentence

Decide the tier from the GB voltage rule and the band from the cap, then keep
the chosen connection inside that band's MW range, so that every charge matches
what is built, in a single solve.

## 1. Replace the 100 MW threshold with the GB voltage rule (S)

GB defines transmission by voltage, not by size:

- **England and Wales.** 275 kV and 400 kV are transmission. 132 kV and below
  is distribution, owned by the DNOs.
- **Scotland** (CI regions 1 and 2). 132 kV and above is transmission.

Sources: Cornwall Insight for Scottish Renewables, *132 kV charging* (2021);
the ENA, *Connecting community energy* ("if your connection voltage is less than
132 kV then this normally goes through the DNO").

That gives the voltage, but a site has a size, not a voltage. Turning a size
into a voltage needs a DNO design standard. Electricity North West's ES216,
*6.6 kV to 132 kV connections from 9 MVA up to 240 MVA*, says a DNO connects
demand up to **240 MVA**. So the rule becomes:

| Where | Distribution | Transmission |
|---|---|---|
| England and Wales | up to 240 MVA (at up to 132 kV) | above 240 MVA |
| Scotland | up to the size a 33 kV connection can serve | above that (132 kV and up) |

Work:

- [ ] Read ES216 and transcribe two numbers: the 240 MVA upper limit, and the
      size at which ES216 moves a connection from 33 kV to 132 kV. The second
      one is the Scottish boundary. Record both in `SOURCES.md`, graded
      TRANSCRIBED. Note that ES216 Issue 4 is marked as a draft (July 2024),
      and check for a final issue.
- [ ] Look for one corroborating DNO (UKPN, SSEN or Northern Powergrid). If
      none is found, say in `SOURCES.md` that the boundary rests on one DNO.
- [ ] Find a current official source confirming that Scottish 132 kV is still
      transmission. The sources found so far are from 2004–2005 and 2021.
- [ ] In `network_charges.py`, replace `TRANSMISSION_MW_ASSUMED` with
      `E_AND_W_DNO_MAX_MVA` and `SCOTLAND_DNO_MAX_MVA`, and give
      `is_transmission_connected` the site's CI region:
      `is_transmission_connected(peak_mw, region, explicit=None)`.
      Scotland is `region in (1, 2)`.
- [ ] Keep `site.transmission_connected` as the override. A real connection
      offer beats any rule.

## 2. Keep the chosen connection inside its band (S)

The band is a step function of the connection size, so a linear model cannot
let it move with `cap_grid`. Instead of solving twice, fix the band from the cap
and bound `cap_grid` from below by that band's floor:

    band floor  ≤  cap_grid  ≤  cap

The cap already sits inside its own band, so this pins the built connection to
the band whose charges the model applies. The capacity charge still scales with
`cap_grid`, so a battery that flattens imports still shrinks the bill. That is
the point `import_charges` makes in its docstring, and it survives.

Band floors, in MW (at power factor 1.0):

| Tier | Band | Floor |
|---|---|---|
| Distribution | EHV1 | 0 |
| Distribution | EHV2 | 5 |
| Distribution | EHV3 | 12 |
| Distribution | EHV4 | 21.5 |
| Transmission | T-Demand4 | the tier boundary from step 1 |

T-Demand bands are set on annual consumption, not capacity, and only T-Demand4
is used, so on the transmission side the floor is just the tier boundary.

Work:

- [ ] `network_charges.band_floor_mw(tier, band, region)` returning the floor
      above.
- [ ] `dc_inputs.build_series` writes `meta["connection_floor_mw"]` next to
      `connection_limit_mw`.
- [ ] `dc_model.Assets` takes `grid_floor_mw`, and `build_model` uses it as
      `cap_grid`'s lower bound. The three callers that pass
      `grid_limit_mw=meta["connection_limit_mw"]` (`dc_runner.py:205`,
      `sensitivity.py:91`, `thresholds.py:472`) pass the floor too.
- [ ] Report when the floor binds. If `cap_grid` sits at its floor, a lower
      band would probably be cheaper. Flag it in `contributions()` and in the
      UI, and tell the user to re-run with the cap just below the floor. Don't
      re-run automatically: the second solve is a decision for the user, not
      something to hide.

**Edge case.** An islanded architecture has `grid_limit_mw=0.0`, so it must
also get a floor of 0. Otherwise the bounds are infeasible.

## 3. One function, everywhere (XS)

The tier is decided in two places that can disagree.
`pages/2_Data_Centre_Optimiser.py:465` calls `is_transmission_connected(_cmw)`
without the site's explicit setting, while `dc_inputs` passes it.

- [ ] Route the UI preview through the same function as `dc_inputs`, with the
      region and the explicit setting.
- [ ] Rewrite the UI help text at `pages/2_Data_Centre_Optimiser.py:206`, which
      says a 100 MW site is "treated as transmission-connected".

## 4. Tests that pin it (S)

Extend `tests/test_connection_tier.py`, which already solves both sides of the
tier, and add fast tests that need no solve.

- [ ] Fast: `is_transmission_connected` at a Scottish and an English site, each
      either side of its boundary; the explicit override wins in both.
- [ ] Fast: `band_floor_mw` for every band, and the floor is never above the
      cap.
- [ ] Fast: an islanded build still solves with a floor of 0.
- [ ] Slow: London at 150 MW load is now **distribution, EHV4**, and pays DUoS.
      The 300 MW Highland site stays **transmission, T-Demand4**.
- [ ] Slow, and the one that pins the fix: after the solve,
      `tdr_band_for(cap_grid)` equals the band the charges assumed. Add the same
      check to `audit.py`, so every run checks it, not just the test.

## 5. Re-run and record what moved (M)

This changes the London headline numbers. A 100 MW IT London site moves from
transmission to distribution:

| Charge | Now (transmission) | After (distribution, EHV4) |
|---|---|---|
| TDR | £4.67 m/year (T-Demand4) | £1.42 m/year (EHV4) |
| DUoS capacity | £0 | £33,543.50/MW/year × `cap_grid` (~£5.0 m at 150 MW) |
| DUoS unit and fixed charges | £0 | charged |

So the total probably **rises**, and the cost-optimal connection size and
storage may change. That needs a re-run, not an estimate.

- [ ] Re-run the London and Highland reference cases and the sweeps in
      `sensitivity.py`. Regenerate `option_summary.csv`, `VALIDATION.md` and the
      LCA map.
- [ ] Record before and after for cost, carbon, `cap_grid` and battery size in
      `SOURCES.md`.
- [ ] `DATA_GAPS.md`: close the *Transmission-vs-distribution threshold* row.
      Re-open *DUoS regional coverage*, because it now matters. Its line "no
      longer affects transmission-connected ones" stops protecting most
      England and Wales sites, which will now pay DUoS, and only London's
      tariff is transcribed. The existing caveat that the LPN HV tariff stands
      in for an EHV site-specific tariff also gets more weight.
- [ ] `ASSUMPTIONS.md`: state the rule, its sources and the override.
- [ ] Delete the `TODO.md` network-charge-shape clause on TDR banding.

## What this does not change

- **Grid carbon.** `delivery_voltage` already returns "high" for both
  transmission and EHV distribution, so the delivered intensity is unchanged.
- **Connection carbon.** `grid_connection.py` already uses a 110 kV intake
  transformer for every site, which fits a 132 kV distribution connection
  better than before. It still errs low for a 275/400 kV site.
- **TNUoS locational charge.** Distribution-connected demand pays it too, via
  its supplier, so it stays on both tiers.

## Order

1 → 2 → 3 → 4 → 5. Steps 1 and 2 can be written in parallel, but step 2's
floors depend on step 1's boundary. Step 5 waits for the tests. The ES216 read
in step 1 is the only external dependency. If its 33/132 kV boundary can't be
found, keep the Scottish boundary graded ASSUMED and say so, rather than
blocking the rest.
