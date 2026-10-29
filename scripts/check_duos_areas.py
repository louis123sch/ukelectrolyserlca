"""Re-read every area's 2026/27 schedule of charges and compare it with
``optimisation.duos_areas``: every 11 kV tariff row, every time band and
super-red window, every EHV quartile (recomputed from the listed sites), every
generic LLF, and the band thresholds and band mapping the model assumes.

    python -I scripts/check_duos_areas.py "<OneDrive>/DC optimiser/connection sources"

Exits 1 on any mismatch. The workbooks are external downloads: run with -I.
"""
import re
import statistics as st
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import duos_areas as D            # noqa: E402
from optimisation import network_charges as nc      # noqa: E402

problems = []


def bad(region, what):
    problems.append(f"region {region:>2} {D.AREA_NAMES[region]}: {what}")


def close(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))


_RANGE = re.compile(r"(\d{1,2})[:.]?(\d{2})\s*(?:-|–|to)\s*(\d{1,2})[:.]?(\d{2})")


def ranges(text):
    if not isinstance(text, str):
        return ()
    out = []
    for h0, m0, h1, m1 in _RANGE.findall(text):
        a, b = int(h0) + int(m0) / 60, int(h1) + int(m1) / 60
        out.append((a, 24.0 if b == 0 else b))
    return tuple(out)


def path_for(base, region):
    name = D.FILES[region]
    p = base / "3 DUoS" / "2026-27 schedules" / name
    return p if p.exists() else base / "3 DUoS" / name


def rows_of(wb, sheet):
    return list(wb[sheet].iter_rows(values_only=True))


def quartiles(v):
    v = sorted(v)
    if len(v) == 1:
        return (v[0],) * 3
    return tuple(st.quantiles(v, n=4, method="inclusive"))


def check_area(base, region):
    wb = openpyxl.load_workbook(path_for(base, region), read_only=True, data_only=True)

    # --- band thresholds and the band mapping ------------------------------------
    rb = rows_of(wb, "Residual Charging Bands")
    def thresholds(label):
        i = next(k for k, r in enumerate(rb) if r[0] and str(r[0]).startswith(label))
        return [float(rb[i + j][4]) for j in range(3)]
    if thresholds("Designated Properties connected at HV") != [t for t, _ in nc.HV_BAND_KVA[:3]]:
        bad(region, "HV band thresholds differ from network_charges.HV_BAND_KVA")
    if thresholds("Designated EHV Properties") != [t for t, _ in nc.EHV_BAND_KVA[:3]]:
        bad(region, "EHV band thresholds differ from network_charges.EHV_BAND_KVA")
    mapping = {str(r[0]).strip(): str(r[1]).strip() for r in rows_of(wb, "TNUoS Mapping") if r[0] and r[1]}
    for n in (1, 2, 3, 4):
        if mapping.get(f"HV Site Specific Band {n}") != f"HV{n}":
            bad(region, f"TNUoS Mapping: HV Site Specific Band {n} is not HV{n}")
        if mapping.get(f"Designated EHV Site Specific Band {n}") != f"EHV{n}":
            bad(region, f"TNUoS Mapping: Designated EHV Band {n} is not EHV{n}")

    # --- Annex 1: 11 kV rows and time bands ---------------------------------------
    a1 = rows_of(wb, "Annex 1 LV, HV and UMS charges")
    th = next(i for i, r in enumerate(a1) if any(isinstance(c, str) and c.startswith("Red Time Band") for c in r))
    jr = next(j for j, c in enumerate(a1[th]) if isinstance(c, str) and c.startswith("Red Time Band"))
    red_wd = amber_wd = amber_we = ()
    for r in a1[th + 1: th + 6]:
        label = str(r[jr - 1] or "")
        if "Monday to Friday" in label:
            red_wd += ranges(r[jr]); amber_wd += ranges(r[jr + 1])
        elif "Saturday" in label:
            amber_we += ranges(r[jr + 1])
    if (red_wd, amber_wd, amber_we) != D.HV_TIME_BANDS[region]:
        bad(region, f"HV time bands: workbook {(red_wd, amber_wd, amber_we)}, "
                    f"module {D.HV_TIME_BANDS[region]}")
    h = next(i for i, r in enumerate(a1) if any(isinstance(c, str) and c.startswith("Tariff name") for c in r))
    hdr = [str(c or "").replace("\n", " ") for c in a1[h]]
    col = lambda key: next(j for j, c in enumerate(hdr) if c.startswith(key))
    cols = [col("Red/black"), col("Amber/yellow"), col("Green unit"), col("Fixed charge"), col("Capacity charge")]
    for r in a1[h + 1:]:
        name = next((c.strip() for c in r[:2] if isinstance(c, str)), "")
        m = re.fullmatch(r"HV Site Specific Band (\d)", name)
        if m:
            got = [float(r[j] or 0) for j in cols]
            want = list(vars(D.HV_ROWS[region][int(m.group(1))]).values())
            if not all(close(g, w) for g, w in zip(got, want)):
                bad(region, f"{name}: workbook {got}, module {want}")

    # --- Annex 2: EHV sites, super-red window --------------------------------------
    a2 = rows_of(wb, "Annex 2 Designated EHV charges")
    sr = ()
    for r in a2[2:10]:
        label = next((c for c in r if isinstance(c, str) and "Monday to Friday" in c), None)
        if label:
            months = (11, 12, 1, 2) if ("November to February" in label or "Nov to Feb" in label) else (6, 7, 8)
            w = ranges(next((c for c in r if isinstance(c, str) and c is not label and _RANGE.search(c)), None))
            if w:
                sr += ((months, w),)
    if sr != D.SUPER_RED[region]:
        bad(region, f"super-red window: workbook {sr}, module {D.SUPER_RED[region]}")
    h = next(i for i, r in enumerate(a2) if any(isinstance(c, str) and "Residual Charging Band" in c for c in r))
    hdr = [str(c or "").replace("\n", " ") for c in a2[h]]
    find = lambda *k: next(j for j, c in enumerate(hdr) if all(x.lower() in c.lower() for x in k))
    jb, js, jf, jc = (find("Residual Charging Band"), find("Import", "Super Red"),
                      find("Import", "fixed"), find("Import", "capacity charge"))
    num = lambda x: float(x) if isinstance(x, (int, float)) else None
    sites = {}
    for r in a2[h + 1:]:
        if len(r) <= jc or (num(r[js]) is None and num(r[jc]) is None):
            continue
        sites.setdefault(str(r[jb]).split(".")[0].strip(), []).append(r)
    for n, band in D.EHV_BANDS[region].items():
        g = sites.get(str(n), [])
        if len(g) != band.n_sites:
            bad(region, f"EHV band {n}: {len(g)} sites in the workbook, module says {band.n_sites}")
            continue
        for j, field in ((js, "super_red_p_per_kwh"), (jf, "fixed_p_per_day"), (jc, "capacity_p_per_kva_day")):
            v = [num(r[j]) or 0.0 for r in g] if j == js else [num(r[j]) for r in g if num(r[j]) is not None]
            q = quartiles(v)
            if not all(close(a, b, 1e-3) for a, b in zip(q, getattr(band, field))):
                bad(region, f"EHV band {n} {field}: workbook {q}, module {getattr(band, field)}")

    # --- Annex 5: generic LLFs -------------------------------------------------------
    if region in D.LLF_FILES:
        f = path_for(base, region).parent / D.LLF_FILES[region]
        a5rows = list(openpyxl.load_workbook(f, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    else:
        a5rows = rows_of(wb, "Annex 5 LLFs")
    labels = {"11 kV": ("high-voltage network", "high voltage network", "11kv"),
              "33 kV": ("33kv generic import", "33kv generic", "greater than 22kv connected - demand",
                        "ehv connected", "33kv"),
              "132 kV": ("132kv generic import", "132kv generic", "greater than 22kv connected - demand",
                         "132kv connected", "132kv")}
    a5 = {}
    for r in a5rows:
        if r and r[0] and str(r[0]).strip().lower() not in a5:
            a5[str(r[0]).strip().lower()] = [x for x in r[1:6] if isinstance(x, (int, float))]
    for v, want in D.LLF[region].items():
        key = next((k for k in labels[v] if k in a5), None)
        if key is None:
            bad(region, f"LLF {v}: no matching row in Annex 5")
        elif not all(close(a, b) for a, b in zip(a5[key], want)) or len(a5[key]) != len(want):
            bad(region, f"LLF {v} ({key}): workbook {a5[key]}, module {list(want)}")


def main(base):
    base = Path(base)
    for region in sorted(D.FILES):
        before = len(problems)
        check_area(base, region)
        print(f"  {region:>2} {D.AREA_NAMES[region]:<62} "
              f"{'ok' if len(problems) == before else f'{len(problems) - before} problem(s)'}")
    print()
    for p in problems:
        print("  PROBLEM", p)
    print(f"{len(problems)} problem(s) across {len(D.FILES)} areas")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  Path.home() / "OneDrive - Imperial College London" / "DC optimiser" / "connection sources"))
