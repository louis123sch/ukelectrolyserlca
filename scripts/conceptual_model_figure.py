"""Conceptual-model figure: one source, two outputs.

python scripts/conceptual_model_figure.py jsx OUT.jsx  -> the methodology Claude Doc widget (theme colours)
python scripts/conceptual_model_figure.py svg docs/conceptual_model.svg  -> the report figure (16 Nov 2026)
"""
import sys

MODE = sys.argv[1]
OUT = sys.argv[2]

TOK = {
    "jsx": dict(edge="var(--cds-chart-axis)", rule="var(--cds-chart-grid)", ink="var(--cds-text-primary)",
                quiet="var(--cds-text-secondary)", accent="var(--cds-chart-categorical-1)",
                h2="var(--cds-chart-categorical-2)", gas="var(--cds-chart-categorical-3)",
                tint="var(--cds-chart-reference-tint)", bg=None),
    "svg": dict(edge="#5F5E5A", rule="#B4B2A9", ink="#1F1E1D", quiet="#5F5E5A", accent="#2F6FD0",
                h2="#E0662F", gas="#1E9E6A", tint="#F1EFE8", bg="#FFFFFF"),
}[MODE]

JSX_NAMES = {"stroke-width": "strokeWidth", "text-anchor": "textAnchor", "font-size": "fontSize",
             "font-weight": "fontWeight", "fill-opacity": "fillOpacity", "marker-end": "markerEnd",
             "marker-start": "markerStart", "stroke-dasharray": "strokeDasharray",
             "font-family": "fontFamily", "aria-label": "aria-label"}


def a(**kw):
    out = []
    for k, v in kw.items():
        k = k.rstrip("_").replace("_", "-")
        if k.startswith("data-"):
            if MODE == "svg":
                continue
        elif MODE == "jsx":
            k = JSX_NAMES.get(k, k)
        out.append(f"{k}='{v}'")
    return " ".join(out)


W, H = 760, 800
parts = []
add = parts.append


def text(tid, x, y, words, size=13, weight=None, colour="ink", anchor="middle"):
    kw = dict(data_claude_text_id=tid, x=x, y=y, font_size=size, fill=TOK[colour])
    if anchor != "start":
        kw["text_anchor"] = anchor
    if weight:
        kw["font_weight"] = weight
    add(f"<text {a(**kw)}>{words}</text>")


def box(gid, cx, top, w, name, lines, style="plain", tid=None):
    h = 40 + 16 * len(lines)
    tid = tid or gid
    add(f"<g {a(data_claude_anchor=gid)}>")
    if style == "accent":
        add(f"<rect {a(x=cx - w / 2, y=top, width=w, height=h, rx=8, fill=TOK['accent'], fill_opacity=0.12, stroke=TOK['accent'], stroke_width=2)}/>")
    elif style == "outside":
        add(f"<rect {a(x=cx - w / 2, y=top, width=w, height=h, rx=8, fill=TOK['tint'], stroke=TOK['rule'], stroke_width=1)}/>")
    else:
        add(f"<rect {a(x=cx - w / 2, y=top, width=w, height=h, rx=8, fill='none', stroke=TOK['edge'], stroke_width=1.25)}/>")
    text(f"{tid}-name", cx, top + 24, name, 13, 600)
    for i, line in enumerate(lines):
        text(f"{tid}-l{i + 1}", cx, top + 40 + 16 * i, line, 11.5, None, "quiet")
    add("</g>")
    return h


def path(d, kind="power", both=False):
    col = {"power": TOK["edge"], "h2": TOK["h2"], "gas": TOK["gas"]}[kind]
    mk = {"power": "cm-arrow", "h2": "cm-h2-arrow", "gas": "cm-gas-arrow"}[kind]
    kw = dict(d=d, fill="none", stroke=col, stroke_width=1.5 if kind != "power" else 1.25,
              marker_end=f"url(#{mk})")
    if kind == "h2":
        kw["stroke_dasharray"] = "6 4"
    if kind == "gas":
        kw["stroke_dasharray"] = "2 3"
    if both:
        kw["marker_start"] = f"url(#{mk})"
    add(f"<path {a(**kw)}/>")


# ---- frame ---------------------------------------------------------------
title = "One busbar: the optimiser sizes every box once and runs it hour by hour"
svg_kw = dict(viewBox=f"0 0 {W} {H}", role="img", aria_label=title, font_size=13)
if MODE == "svg":
    svg_kw = dict(xmlns="http://www.w3.org/2000/svg", width=W, height=H, **svg_kw,
                  font_family="Inter, Segoe UI, Helvetica, Arial, sans-serif")
add(f"<svg {a(**svg_kw)}>")
add("<defs>")
for mid, col in (("cm-arrow", TOK["edge"]), ("cm-h2-arrow", TOK["h2"]), ("cm-gas-arrow", TOK["gas"])):
    add(f"<marker id='{mid}' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' markerHeight='6' "
        f"orient='auto-start-reverse'><path d='M0 0L10 5L0 10z' fill='{col}'/></marker>")
add("</defs>")
if TOK["bg"]:
    add(f"<rect x='0' y='0' width='{W}' height='{H}' fill='{TOK['bg']}'/>")

text("title", 24, 28, title, 15, 600, anchor="start")
text("subtitle", 24, 48, "Inside the dashed line: what the optimiser may build (each sized once, zero allowed). "
     "Every arrow is set hour by hour.", 11.5, None, "quiet", "start")

# ---- boundary --------------------------------------------------------------
BX0, BX1, BY0, BY1 = 192, 736, 64, 568
add(f"<g {a(data_claude_anchor='boundary')}>")
add(f"<rect {a(x=BX0, y=BY0, width=BX1 - BX0, height=BY1 - BY0, rx=12, fill='none', stroke=TOK['edge'], stroke_width=1.25, stroke_dasharray='8 5')}/>")
text("boundary-label", BX0 + 16, BY0 + 22, "Site boundary: built, costed and counted for carbon", 11.5, 600, "quiet", "start")
add("</g>")

# ---- inside: left column (into the busbar) ---------------------------------
LX, LW = 310, 180
RX, RW = 610, 200
BUS = 450
rows = dict(wind=128, solar=200, grid=272, gas=344, fc=416)
box("wind", LX, rows["wind"] - 28, LW, "Onshore wind", ["output set by weather"])
box("solar", LX, rows["solar"] - 28, LW, "Ground-mounted solar", ["output set by weather"])
box("grid-connection", LX, rows["grid"] - 28, LW, "Grid connection", ["size + price list chosen"])
box("gas-engines", LX, rows["gas"] - 28, LW, "Gas engines", ["optional, off by default"])
box("fuel-cell", LX, rows["fc"] - 28, LW, "Fuel cell", ["hydrogen to power"])

# ---- inside: right column (out of the busbar) ------------------------------
box("data-centre", RX, 92, RW, "Data centre", ["flat load: IT × PUE", "100 MW IT → 140 MW"], style="accent")
box("battery", RX, 208, RW, "Battery", ["charges and discharges"])
box("electrolyser", RX, 316, RW, "Electrolyser", ["power to hydrogen"])
box("tank", 450, 488, 160, "Hydrogen tank", ["steel, 28 bar"])

# ---- busbar ----------------------------------------------------------------
add(f"<g {a(data_claude_anchor='busbar')}>")
add(f"<line {a(x1=BUS, y1=100, x2=BUS, y2=444, stroke=TOK['ink'], stroke_width=4)}/>")
text("busbar-label", BUS, 464, "site busbar", 11.5, 600, "quiet")
add("</g>")

# ---- outside: left column --------------------------------------------------
OX, OW = 100, 152
box("weather", OX, 136, OW, "Weather, 2025", ["wind and sun, hourly"], style="outside")
box("gb-grid", OX, 244, OW, "GB grid", ["price, carbon hourly"], style="outside")
box("gas-network", OX, 316, OW, "Gas network", ["gas + carbon price"], style="outside")
box("h2-seller", OX, 496, OW, "Hydrogen seller", ["green, as needed"], style="outside")

# ---- flows -----------------------------------------------------------------
add(f"<g {a(data_claude_anchor='flows')}>")
L, R = LX + LW / 2, RX - RW / 2
OR = OX + OW / 2
path(f"M{OR} 164H204V128H{LX - LW / 2}")              # weather -> wind
path(f"M204 164V200H{LX - LW / 2}")                    # weather -> solar
path(f"M{OR} 272H{LX - LW / 2}")                       # grid -> connection
path(f"M{OR} 344H{LX - LW / 2}", "gas")                # gas network -> engines
for y in rows.values():
    path(f"M{L} {y}H{BUS - 2}")                        # each source -> busbar
path(f"M{BUS + 2} 128H{R}")                            # busbar -> data centre
path(f"M{BUS + 10} 236H{R}", both=True)                # busbar <-> battery
path(f"M{BUS + 2} 344H{R}")                            # busbar -> electrolyser
path(f"M{RX} 372V516H530", "h2")                       # electrolyser -> tank
path(f"M370 508H{LX}V444", "h2")                       # tank -> fuel cell
path(f"M{OR} 524H370", "h2")                           # seller -> tank
add("</g>")
text("bought-label", 300, 540, "bought", 11.5, None, "quiet")
text("made-label", RX + 8, 440, "made on site", 11.5, None, "quiet", "start")

# ---- outputs ---------------------------------------------------------------
box("cost", 330, 592, 240, "Annual cost", ["£ per MWh served, 2026 pounds", "kit, upkeep, fuel, grid charges"])
box("carbon", 590, 592, 240, "Life-cycle carbon", ["g CO2e per kWh served", "making the kit, grid, gas, hydrogen"])
box("front", 470, 688, 400, "Front of designs: cheapest → lowest carbon",
    ["each point: sizes, hourly running, £/MWh, g/kWh"])
box("left-outside", 104, 592, 160, "Left outside",
    ["transport to site", "standby diesel set", "end of life", "pipe to gas network", "selling power back"],
    style="outside")
add(f"<g {a(data_claude_anchor='to-objectives')}>")
path(f"M330 {BY1}V592")
path(f"M590 {BY1}V592")
path("M330 664V688")
path("M590 664V688")
add("</g>")
text("money-label", 338, 584, "money", 11.5, None, "quiet", "start")
text("carbon-label", 598, 584, "carbon", 11.5, None, "quiet", "start")

# ---- key -------------------------------------------------------------------
add(f"<g {a(data_claude_anchor='key')}>")
ky = 776
add(f"<line {a(x1=24, y1=ky - 4, x2=56, y2=ky - 4, stroke=TOK['edge'], stroke_width=1.25)}/>")
text("key-power", 64, ky, "electricity", 11.5, None, "quiet", "start")
add(f"<line {a(x1=160, y1=ky - 4, x2=192, y2=ky - 4, stroke=TOK['h2'], stroke_width=1.5, stroke_dasharray='6 4')}/>")
text("key-h2", 200, ky, "hydrogen", 11.5, None, "quiet", "start")
add(f"<line {a(x1=288, y1=ky - 4, x2=320, y2=ky - 4, stroke=TOK['gas'], stroke_width=1.5, stroke_dasharray='2 3')}/>")
text("key-gas", 328, ky, "natural gas", 11.5, None, "quiet", "start")
text("key-note", 736, ky, "Cost and carbon gather every box", 11.5, None, "quiet", "end")
add("</g>")
add("</svg>")

body = "".join(parts)
if MODE == "jsx":
    body = "export default () => " + body + ";"
else:
    body = '<?xml version="1.0" encoding="UTF-8"?>\n' + body.replace("'", '"') + "\n"
open(OUT, "w", encoding="utf-8").write(body)
print(len(body))
