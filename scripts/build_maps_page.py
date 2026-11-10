#!/usr/bin/env python
"""One page for both maps: optimisation_outputs/maps.html, four tabs.

    python scripts/build_maps_page.py

The cost map and the LCA map stay two pages of their own (their checks read
them), each with two tabs. This wraps both, unchanged, in one file whose tab
bar has all four: Cost graph, Cost sources, LCA graph, Energy flow. Each map
runs in its own frame, so neither's code or styles can touch the other's; the
maps' own tab bars are hidden and the outer bar drives them by message
(the hidden buttons are clicked, since each map's code is private to it).

Both build scripts call ``write()`` after writing their page, so the combined
page is never older than either map. 9 Nov 2026.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "optimisation_outputs"
COST = OUT_DIR / "cost_map.html"
LCA = OUT_DIR / "lca_map.html"
HTML_OUT = OUT_DIR / "maps.html"

# Hides a map's own tab bar and lets the outer page switch its tab.
_INJECT_HEAD = "<style>nav.tabs{display:none!important}</style>"
_INJECT_BODY = ("<script>window.addEventListener('message',function(e){"
                "var t=e.data&&e.data.mapTab,b=t&&document.getElementById('tab-'+t);if(b)b.click();});"
                "parent.postMessage({mapReady:true},'*');</script>")

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Centre Maps</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root {
  --bg: #eef1ef; --surface: #ffffff; --ink: #16201e; --muted: #5b6b66; --line: #d5ddd9; --accent: #0d6670;
  --font-ui: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #111716; --surface: #1a2220; --ink: #e3ebe8; --muted: #93a29d; --line: #2c3633; --accent: #5fb7bf;
  }
}
:root[data-theme="dark"] {
  --bg: #111716; --surface: #1a2220; --ink: #e3ebe8; --muted: #93a29d; --line: #2c3633; --accent: #5fb7bf;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { background: var(--bg); color: var(--ink); font-family: var(--font-ui); display: flex; flex-direction: column; }
.top { display: flex; align-items: stretch; gap: 16px; padding: 0 16px; background: var(--surface);
       border-bottom: 1px solid var(--line); overflow-x: auto; flex: 0 0 auto; }
.top h1 { font-size: 14px; font-weight: 600; margin: 0; padding: 12px 0; white-space: nowrap; align-self: center; }
.tabs { display: flex; gap: 2px; }
.tabs button { font: inherit; font-size: 13px; color: var(--muted); background: none; border: 0;
               border-bottom: 2px solid transparent; padding: 12px 10px 10px; cursor: pointer; white-space: nowrap; }
.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }
.tabs button:hover { color: var(--accent); }
.tabs .sep { width: 1px; background: var(--line); margin: 10px 6px; }
.frames { flex: 1 1 auto; position: relative; min-height: 0; }
.frames iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; background: var(--bg); }
.frames iframe[hidden] { display: none; }
</style>
</head>
<body>
<div class="top">
  <h1>Data Centre Maps</h1>
  <nav class="tabs" role="tablist" aria-label="Maps">
    <button role="tab" data-tab="cost-tree" aria-selected="true">Cost graph</button>
    <button role="tab" data-tab="cost-flow" aria-selected="false">Cost sources</button>
    <span class="sep" aria-hidden="true"></span>
    <button role="tab" data-tab="lca-tree" aria-selected="false">LCA graph</button>
    <button role="tab" data-tab="lca-flow" aria-selected="false">Energy flow</button>
  </nav>
</div>
<div class="frames">
  <iframe id="f-cost" title="Cost map"></iframe>
  <iframe id="f-lca" title="LCA map" hidden></iframe>
</div>
<script>
const PAGES = { cost: __COST__, lca: __LCA__ };
const loaded = {}, pending = {};
function frame(map) { return document.getElementById("f-" + map); }
function show(tab) {
  const [map, view] = tab.split("-");
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  ["cost", "lca"].forEach(m => frame(m).hidden = m !== map);
  const f = frame(map);
  if (!loaded[map]) {
    pending[map] = view;                  // sent when the map says it is ready
    if (!f.srcdoc) f.srcdoc = PAGES[map];
  } else {
    f.contentWindow.postMessage({ mapTab: view }, "*");
  }
  try { localStorage.setItem("dc-maps-tab", tab); } catch (e) {}
  if (location.hash !== "#" + tab) history.replaceState(null, "", "#" + tab);
}
// The point on the run's cost-carbon curve: switched in either map, kept in step in the other.
let mapPoint = null;
window.addEventListener("message", e => {
  if (e.data && e.data.mapPoint) {
    mapPoint = e.data.mapPoint;
    ["cost", "lca"].forEach(m => {
      if (loaded[m] && e.source !== frame(m).contentWindow) frame(m).contentWindow.postMessage({ mapPoint }, "*");
    });
    return;
  }
  if (!(e.data && e.data.mapReady)) return;
  ["cost", "lca"].forEach(m => {
    if (e.source === frame(m).contentWindow) {
      loaded[m] = true;
      frame(m).contentWindow.postMessage({ mapTab: pending[m] || "tree" }, "*");
      if (mapPoint) frame(m).contentWindow.postMessage({ mapPoint }, "*");
    }
  });
});
document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => show(b.dataset.tab)));
const TABS = ["cost-tree", "cost-flow", "lca-tree", "lca-flow"];
let first = location.hash.slice(1);
if (!TABS.includes(first)) { try { first = localStorage.getItem("dc-maps-tab"); } catch (e) { first = null; } }
show(TABS.includes(first) ? first : "cost-tree");
</script>
</body>
</html>
"""


def _inner(path: Path) -> str:
    # The map pages are fragments (no <head> or <body>; a browser supplies them),
    # so the style goes in after the title and the listener at the very end.
    page = path.read_text(encoding="utf-8")
    page = page.replace("</title>", "</title>" + _INJECT_HEAD, 1) + _INJECT_BODY
    # A JS string inside a script tag: no "</" may survive, or it would close it.
    return json.dumps(page).replace("</", "<\\/")


def write() -> Path | None:
    """Write maps.html from the two map pages; None if either is missing."""
    if not (COST.exists() and LCA.exists()):
        return None
    HTML_OUT.write_text(_PAGE.replace("__COST__", _inner(COST)).replace("__LCA__", _inner(LCA)), encoding="utf-8")
    return HTML_OUT


if __name__ == "__main__":
    out = write()
    if out is None:
        sys.exit("both optimisation_outputs/cost_map.html and lca_map.html are needed")
    print(f"wrote {out.relative_to(ROOT)}: {out.stat().st_size / 1e6:.2f} MB")
