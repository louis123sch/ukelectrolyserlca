# Source check — levies and losses, 9 Nov 2026

The first group of the source check (the pilot). Two independent passes:

1. **Blind re-read.** A reader was given each document and where to look, but not the model's
   values, and read every figure fresh. Its readings were then compared with `optimisation/levies.py`.
2. **Search.** A second reader looked for newer editions of the same 2026/27 documents and for more
   direct official sources, under the rules: same charging year (a later year is listed apart, not
   as a replacement); UK government and regulators first; a stated figure beats a calculated one.

Key findings were then confirmed by hand from the downloaded files (EMR Settlement Revision 13,
Ofgem's Annex 4 workbook, the FiT levelisation report, the bank-holiday list, the legislation).
**Applied the same day (user's go-ahead):** the CfD and Nuclear RAB rates of Revision 13, the
Capacity Market window without England and Wales bank holidays, the FiT from Ofgem's Annex 4 (the
quarterly-report mean kept as `levies.fit_rolling_year`, a cross-check), Issue 64's fund corrected
to .28, and the TLMO note. Levies on a flat 2025 load: £72.75 → £71.70/MWh.

New documents are in OneDrive, `DC optimiser/cost sources/9 levies and losses (checked 9 Nov 2026)`.

## 1. Read correctly?

Every figure the model uses matches its document.

| Figure | Document says | Model | |
|---|---|---|---|
| Renewables Obligation buy-out, 2026/27 | £69.34 per ROC | 69.34 | ✓ |
| Obligation, GB, 2026/27 | 0.472 ROC/MWh | 0.472 | ✓ |
| FiT quarters, Issues 62–65 (fund, supply, EII-exempt) | all twelve numbers | same | ✓ (Issue 64's fund is £358,081,232.28: the printed ".287" ends in footnote marker 7; the model has .287, a £0.007 difference) |
| CfD interim levy rates and dates; operational levy £0.1463 | as model, **up to Revision 12** | same | ✓ — but see §2 |
| Nuclear RAB rates by quarter; operational levy £0.0063 | as model, **up to Revision 12** | same | ✓ — but see §2 |
| Capacity Market, delivery year 2026/27 | £3,474,489,734.79 over 11,291,571.95 MWh; 4–7 pm, working days, Nov–Feb | same | ✓ (both provisional until March 2027 and January 2028) |
| AAHEDC | 0.044269 p/kWh | same | ✓ |
| Climate Change Levy, from 1 Apr 2026 | £0.00801/kWh electricity and gas; 92 % / 89 % off under an agreement; gas £0.00775 in 2024/25 and 2025/26 | same | ✓ (live page unchanged since 27 Nov 2025) |
| DESNZ 2025 extra-large electricity excl. CCL; large gas incl. CCL | 20.927 / 4.149 p/kWh (sheet 3.4.1 H29; 3.4.2 M29) | same | ✓ |
| CMA supplier margin | 2.0 % EBIT, industrial & commercial, six large firms | 2.0 % | ✓ — the figure is **electricity and gas together**; no electricity-only figure is published |
| Offtaking TLM | 1 + TLF + TLMO−, losses 45 / 55 % | same | ✓ |
| Estimated TLMO−, 2026/27 by season | 0.00948, 0.01068, 0.00991, 0.00671 | same | ✓ |
| Zonal seasonal TLFs | charts only; read off the bars, within ±0.0002–0.00035 of the model's five-decimal values except zone 7 winter (0.0006) | interactive-report values | ✓ (the model's are the more precise) |

Documentation errors found (no number affected):
- `levies.py` and the `elexon_tlf_guidance` register note say the guidance's worked example gives
  TLMO− = 0.011. It gives **0.00398** (0.78 / 196). The model stopped using a flat TLMO on 4 Nov, so
  only the wording is wrong.

## 2. Newer or better sources

| Item | Finding | Effect on the import price | Recommendation |
|---|---|---|---|
| **CfD levy** | EMR Settlement *Key Figures 2026/27* **Revision 13 (6 Nov 2026)**: rate **£0.000/MWh from 5 Nov 2026** to 31 Dec ("elevated market prices"); Jan–Mar 2027 £2.979 unchanged | day-weighted £6.45 → **£5.58/MWh** (−£0.86) | **Replace** with Revision 13 |
| **Nuclear RAB levy** | Same revision: Oct–Dec rate rises to **£5.151/MWh from 6 Dec 2026** (lower demand forecast) | £4.16 → **£4.26/MWh** (+£0.10) | **Replace** with Revision 13 |
| **Capacity Market working days** | *Electricity Capacity Regulations 2014*, reg. 2(1): a working day excludes "a bank holiday or public holiday in **England and Wales**". The model charges every weekday. Official list: GOV.UK `bank-holidays.json` (2019–2028) | for 2025: 1 Jan, 25 and 26 Dec are not charged; mean CM on a flat load about £8.82 → **£8.5/MWh** | **Fix**: take England-and-Wales bank holidays out of the window |
| **FiT levelisation** | Ofgem's price-cap *Annex 4* workbook (v1.25, Oct–Dec 2026) states the FiT cost per MWh directly: **£7.70 (Apr–Sep 2026), £8.05 (Oct 2026–Mar 2027)**, same method (fund ÷ supply less EII exemption; the overseas-renewables exemption is zero since 2023/24, so the model's denominator is right) | model's rolling year £7.96 → about **£7.87/MWh** (−£0.09) | **Replace** (a regulator's figure for the year itself) — or keep, the gap is 1 % |
| Supplier margin | No regulator-wide figure since 2015. Suppliers' Consolidated Segmental Statements (an Ofgem licence requirement), non-domestic EBIT margins: EDF 2025 2.66 %, British Gas 2024 1.98 %, Drax 2024 1.01 %, SmartestEnergy FY2025 1.56 %; revenue-weighted about 2.0 % (search agent's arithmetic, not re-derived here) | none | **Keep 2.0 %; add** the statements as current corroboration |
| Renewables Obligation | No correction. The 75 % Exchequer funding is households only (DESNZ supplier guidance §1.3) | none | Keep. Watch: Ofgem's 2025/26 mutualisation decision (an extra charge in 2026/27 if triggered) |
| AAHEDC | Issue 21 Revision 1 (15 Jul 2026) is the latest | none | Keep |
| Climate Change Levy | No change for 2026/27 in the 28 Oct 2026 Budget. No official list of which data-centre sites hold an agreement; the new scheme began 1 Jan 2026 | none | Keep; the agreement stays a tickbox |
| DESNZ non-domestic prices | Sep 2026 release is current; next on 17 Dec 2026 | none | Keep; re-pull after 17 Dec |
| Zonal TLFs | No public table; exact values only on the Elexon Portal (login) | none | Keep the interactive-report values |

**Net effect of the three replacements and the fix**, on a flat load: about **−£1.1/MWh** on a levy
total of about £72.8/MWh (CfD −0.86, nuclear +0.10, Capacity Market −0.3, FiT −0.09).

## 3. Policy changes (none alters 2026/27)

- **British Industrial Competitiveness Scheme**: manufacturing only (Department for Business and
  Trade, government response, Apr 2026); data centres are not eligible. Exempts the RO and FiT from
  April 2027 and the Capacity Market from October 2027 for those who are.
- **AI Growth Zones discount**: not in force; "from April 2027, subject to legislative timetables",
  up to £24/MWh (Scotland), £16 (Cumbria), £14 (North East) for a 500 MW site.
- **Energy Independence Bill** (4 Nov 2026): a power to remove certain supply charges from
  re-exported electricity; no charges named, no date.

## 4. For when the model moves year (not replacements)

Renewables Obligation 2027/28: 0.394 ROC/MWh. Climate Change Levy 2027/28 £0.00827/kWh; from
April 2028 electricity frozen at £0.00827, gas £0.00853. Carbon Price Support ends April 2028.
The BICS exemptions and the AI Growth Zones discount above.

## 5. Saved (OneDrive, `cost sources/9 levies and losses (checked 9 Nov 2026)`)

EMRS Key Figures 2026/27 Revision 13 (PDF and XLSX); Ofgem Annex 4 policy cost workbooks for
Apr–Jun, Jul–Sep and Oct–Dec 2026; Ofgem FiT levelisation report Apr–Jun 2026; Ofgem's 2021 FiT
allowance decision; GOV.UK bank holidays (JSON); the Electricity Capacity Regulations 2014 and the
Supplier Payment Regulations 2014, regulation 2; Consolidated Segmental Statements of EDF (2025),
Centrica (2024), Drax (2024) and SmartestEnergy (FY to Mar 2025); the BICS eligibility response and
code list.

Not downloaded, link only: the Elexon Portal TLF file (needs an Elexon Portal account:
https://elexonportal.co.uk/TLFDETERMINATION_BSCYEAR2026_27 — sign in, open BSC year 2026/27, download
TLFA-I009); LCCC's forecast data portal (refused automated access:
https://dp.lowcarboncontracts.uk/dataset/forecast-ilr-tra — open in a browser and use "Download").
