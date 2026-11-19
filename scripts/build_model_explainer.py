#!/usr/bin/env python
"""The model explainer: optimisation_outputs/model_explainer.html.

    python scripts/build_model_explainer.py

The one page that explains the model (user, 19 Nov 2026): it supersedes the
separate maps pages and maps.html. Tabs: Equations, Cost graph, Cost sources,
LCA graph, Energy flow, Code. It is tied to the model: it carries a model
version, a digest of every file it copies (the Python in CODE_DIRS and the
equations page), and tests/test_model_explainer.py fails as soon as the code
differs from what the page was built from. scripts/hooks/pre-commit-model-explainer.sh,
called from the local pre-commit hook, rebuilds it whenever a commit touches
the model, so each new model gets a new page.

What a rebuild cannot refresh without a run: the numbers in the two maps come
from a saved run (scripts/build_cost_map.py, build_lca_map.py). The header says
which run, when the maps were built, and whether the model has changed since.

The cost map and the LCA map stay two pages of their own (their checks read
them), each with two tabs. This wraps both, unchanged, in one file whose tab
bar has all four: Cost graph, Cost sources, LCA graph, Energy flow. Each map
runs in its own frame, so neither's code or styles can touch the other's; the
maps' own tab bars are hidden and the outer bar drives them by message
(the hidden buttons are clicked, since each map's code is private to it).

Both build scripts call ``write()`` after writing their page, so the combined
page is never older than either map. 9 Nov 2026.

Equations tab (19 Nov 2026): ``docs/model_equations_explorer.html`` sits first
in the tab row and opens by default. Clicking a symbol there shows its
explanation; inside this page the panel also offers "Show in cost map" /
"Show in LCA map", which switches tab and opens that box in the map (the
explorer posts ``goToMap``; this page forwards ``mapFocus`` to the map, whose own listener
opens the box: see the end of each map template).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "optimisation_outputs"
COST = OUT_DIR / "cost_map.html"
LCA = OUT_DIR / "lca_map.html"
HTML_OUT = OUT_DIR / "model_explainer.html"
EQ = ROOT / "docs" / "model_equations_explorer.html"
# The Python files copied into the Code tab, so "Show in code" can open them.
# They and the equations page are "the model" the explainer's version names.
CODE_DIRS = ("optimisation", "optimiser_lca")
MODEL_META = re.compile(r'<meta name="model-version" content="([0-9a-f]+)">')

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
<title>Model explainer</title>
<meta name="model-version" content="__VERSION__">
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
.stamp { flex: 0 0 auto; font-size: 12px; line-height: 1.5; color: var(--muted); padding: 4px 16px;
         background: var(--surface); border-bottom: 1px solid var(--line); }
.stamp code { font-size: 11.5px; }
.stamp .old { color: #9a4d12; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) .stamp .old { color: #f0a868; } }
:root[data-theme="dark"] .stamp .old { color: #f0a868; }
.frames { flex: 1 1 auto; position: relative; min-height: 0; }
.frames iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; background: var(--bg); }
.frames iframe[hidden] { display: none; }
</style>
</head>
<body>
<div class="top">
  <h1>Model explainer</h1>
  <nav class="tabs" role="tablist" aria-label="Model explainer">
    <button role="tab" data-tab="eq-main" aria-selected="true">Equations</button>
    <span class="sep" aria-hidden="true"></span>
    <button role="tab" data-tab="cost-tree" aria-selected="false">Cost graph</button>
    <button role="tab" data-tab="cost-flow" aria-selected="false">Cost sources</button>
    <span class="sep" aria-hidden="true"></span>
    <button role="tab" data-tab="lca-tree" aria-selected="false">LCA graph</button>
    <button role="tab" data-tab="lca-flow" aria-selected="false">Energy flow</button>
    <span class="sep" aria-hidden="true"></span>
    <button role="tab" data-tab="code-main" aria-selected="false">Code</button>
  </nav>
</div>
<div class="stamp">__STAMP__</div>
<div class="frames">
  <iframe id="f-eq" title="Model equations"></iframe>
  <iframe id="f-cost" title="Cost map" hidden></iframe>
  <iframe id="f-lca" title="LCA map" hidden></iframe>
  <iframe id="f-code" title="Model code" hidden></iframe>
</div>
<script>
const PAGES = { eq: __EQ__, cost: __COST__, lca: __LCA__, code: __CODE__ };
let codeReady = false, codeWant = null;
const loaded = {}, pending = {}, focus = {};
function frame(map) { return document.getElementById("f-" + map); }
function show(tab) {
  const [map, view] = tab.split("-");
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  ["eq", "cost", "lca", "code"].forEach(m => frame(m).hidden = m !== map);
  const f = frame(map);
  if (map === "eq") {
    if (!f.srcdoc) {
      // Tell the explorer it is inside this page, so it offers the map buttons.
      f.addEventListener("load", () => f.contentWindow.postMessage({ mapsHost: true }, "*"), { once: true });
      f.srcdoc = PAGES.eq;
    }
  } else if (map === "code") {
    if (!f.srcdoc) f.srcdoc = PAGES.code;   // it says codeReady when loaded
  } else if (!loaded[map]) {
    pending[map] = view;                  // sent when the map says it is ready
    if (!f.srcdoc) f.srcdoc = PAGES[map];
  } else {
    f.contentWindow.postMessage({ mapTab: view }, "*");
  }
  try { localStorage.setItem("dc-maps-tab", tab); } catch (e) {}
  // A preview or other sandboxed frame refuses to change the address: skip it there.
  try { if (location.hash !== "#" + tab) history.replaceState(null, "", "#" + tab); } catch (e) {}
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
  // From the Equations tab: open that box in the cost or LCA map.
  if (e.data && e.data.goToMap) {
    const { map, id } = e.data.goToMap;
    if (map !== "cost" && map !== "lca") return;
    focus[map] = id;
    show(map + "-tree");
    if (loaded[map]) { frame(map).contentWindow.postMessage({ mapFocus: id }, "*"); delete focus[map]; }
    return;
  }
  // From the explorer or either map: open the Code tab at that file and line.
  if (e.data && e.data.goToCode) {
    if (codeReady) frame("code").contentWindow.postMessage({ codeGo: e.data.goToCode }, "*");
    else codeWant = e.data.goToCode;      // sent when the Code tab says it is ready
    show("code-main");
    return;
  }
  if (e.data && e.data.codeReady && e.source === frame("code").contentWindow) {
    codeReady = true;
    if (codeWant) { frame("code").contentWindow.postMessage({ codeGo: codeWant }, "*"); codeWant = null; }
    return;
  }
  if (!(e.data && e.data.mapReady)) return;
  ["cost", "lca"].forEach(m => {
    if (e.source === frame(m).contentWindow) {
      loaded[m] = true;
      frame(m).contentWindow.postMessage({ mapTab: pending[m] || "tree" }, "*");
      if (mapPoint) frame(m).contentWindow.postMessage({ mapPoint }, "*");
      if (focus[m]) { frame(m).contentWindow.postMessage({ mapFocus: focus[m] }, "*"); delete focus[m]; }
    }
  });
});
document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => show(b.dataset.tab)));
const TABS = ["eq-main", "cost-tree", "cost-flow", "lca-tree", "lca-flow", "code-main"];
// The Equations tab opens first, unless the address names another tab.
let first = "";
try { first = location.hash.slice(1); } catch (e) {}
show(TABS.includes(first) ? first : "eq-main");
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


def _equations() -> str:
    """The equation explorer as a JS string; a short notice if it is missing."""
    if EQ.exists():
        page = EQ.read_text(encoding="utf-8")
    else:
        page = ("<!doctype html><meta charset='utf-8'><p style='font-family:sans-serif;padding:24px'>"
                "docs/model_equations_explorer.html is missing, so there is no Equations tab content.</p>")
    return json.dumps(page).replace("</", "<\\/")


_CODE_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Model code</title>
<style>
:root { --bg:#f6f8f7; --surface:#fff; --ink:#16201e; --muted:#5b6b66; --line:#d5ddd9; --accent:#0d6670;
  --hl:#fff3c4; --hl-edge:#e0a800; --kw:#8a3ffc; --str:#0a7d3e; --com:#7b8a85; --num:#b5530b; --dec:#0d6670;
  --mono:"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --ui:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; }
@media (prefers-color-scheme: dark) { :root { --bg:#111716; --surface:#1a2220; --ink:#e3ebe8; --muted:#93a29d; --line:#2c3633;
  --accent:#5fb7bf; --hl:#3a3413; --hl-edge:#d4a72c; --kw:#c49bff; --str:#7fd49b; --com:#7d8c87; --num:#f0a868; --dec:#5fb7bf; } }
* { box-sizing:border-box; }
html, body { margin:0; height:100%; }
body { display:flex; background:var(--bg); color:var(--ink); font-family:var(--ui); }
aside { width:250px; flex:0 0 250px; border-right:1px solid var(--line); background:var(--surface); display:flex; flex-direction:column; }
aside input { margin:10px; padding:6px 8px; font:inherit; font-size:13px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); }
#files { overflow:auto; flex:1; padding:0 6px 12px; }
#files h4 { font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:12px 6px 4px; }
#files button { display:block; width:100%; text-align:left; font:12.5px var(--mono); background:none; border:0; color:var(--ink);
  padding:3px 8px; border-radius:4px; cursor:pointer; }
#files button:hover { background:var(--bg); }
#files button[aria-current="true"] { background:var(--accent); color:#fff; }
main { flex:1; min-width:0; display:flex; flex-direction:column; }
header { padding:9px 16px; border-bottom:1px solid var(--line); background:var(--surface); font-size:13px; display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; }
header b { font-family:var(--mono); font-weight:600; }
header .note { color:var(--muted); }
header .clear { margin-left:auto; font:inherit; font-size:12px; background:none; border:1px solid var(--line); color:var(--muted); border-radius:5px; padding:2px 8px; cursor:pointer; }
#code { flex:1; overflow:auto; font:12.5px/1.55 var(--mono); padding:8px 0 40vh; tab-size:4; }
.row { display:flex; white-space:pre; }
.row .no { flex:0 0 56px; text-align:right; padding-right:14px; color:var(--muted); user-select:none; opacity:.7; }
.row .tx { flex:1; padding-right:24px; }
.row.hl { background:var(--hl); box-shadow:inset 3px 0 0 var(--hl-edge); }
.row.hl .no { opacity:1; color:var(--ink); }
.k { color:var(--kw); } .s { color:var(--str); } .c { color:var(--com); font-style:italic; } .n { color:var(--num); } .d { color:var(--dec); }
.empty { padding:40px; color:var(--muted); max-width:560px; line-height:1.5; }
</style>
</head>
<body>
<aside>
  <input id="q" type="search" placeholder="Filter files" aria-label="Filter files">
  <nav id="files"></nav>
</aside>
<main>
  <header id="head"><span class="note">A copy of the model's Python files, taken when this page was built (__STAMP__).</span></header>
  <div id="code"><div class="empty">Pick a file on the left, or use a <b>Show in code</b> button in the Equations tab or in either map. The lines that button points at are highlighted here.</div></div>
</main>
<script>
const FILES = __FILES__;
const KW = new Set("def class return if elif else for while in not and or is None True False import from as with try except finally raise lambda yield pass break continue global nonlocal assert del async await".split(" "));
const RX = /([rbfuRBFU]{0,2}(?:\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'))|(#[^\n]*)|(@[A-Za-z_][\w.]*)|\b([A-Za-z_]\w*)\b|\b(\d[\d_]*(?:\.\d*)?(?:[eE][-+]?\d+)?)\b/g;
const esc = s => s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const cache = {};
function lines(path) {
  if (cache[path]) return cache[path];
  const src = FILES[path], out = [[]];
  const push = (cls, text) => text.split("\n").forEach((p, i) => {
    if (i) out.push([]);
    if (p) out[out.length - 1].push(cls ? `<span class="${cls}">${esc(p)}</span>` : esc(p));
  });
  let last = 0, m; RX.lastIndex = 0;
  while ((m = RX.exec(src))) {
    if (m.index > last) push("", src.slice(last, m.index));
    const cls = m[1] ? "s" : m[2] ? "c" : m[3] ? "d" : m[4] ? (KW.has(m[4]) ? "k" : "") : "n";
    push(cls, m[0]); last = RX.lastIndex;
  }
  push("", src.slice(last));
  return (cache[path] = out.map(a => a.join("")));
}
const $ = id => document.getElementById(id);
let cur = null;
function open(path) {
  if (!FILES[path]) return false;
  if (cur !== path) {
    const L = lines(path);
    $("code").innerHTML = L.map((h, i) => `<div class="row" id="L${i + 1}"><span class="no">${i + 1}</span><span class="tx">${h || " "}</span></div>`).join("");
    cur = path;
    document.querySelectorAll("#files button").forEach(b => b.setAttribute("aria-current", b.dataset.path === path));
  }
  return true;
}
function setHead(path, a, b, label) {
  const h = $("head"); h.innerHTML = "";
  const f = document.createElement("b"); f.textContent = path; h.appendChild(f);
  if (a) { const s = document.createElement("span"); s.textContent = a === b ? "line " + a : "lines " + a + "–" + b; h.appendChild(s); }
  if (label) { const s = document.createElement("span"); s.className = "note"; s.textContent = label; h.appendChild(s); }
  if (a) { const c = document.createElement("button"); c.className = "clear"; c.textContent = "Clear highlight"; c.onclick = () => { clearHl(); setHead(path); }; h.appendChild(c); }
}
function clearHl() { document.querySelectorAll(".row.hl").forEach(r => r.classList.remove("hl")); }
function resolveFile(f) {
  if (FILES[f]) return f;
  const k = Object.keys(FILES).find(p => p.endsWith("/" + f) || p === f);
  return k || null;
}
// Where a statement that starts on line n (1-based) ends: brackets balanced,
// and for a line ending in ":" (def, class, for, if…) the indented block under it.
function extent(src, n) {
  const L = src.split("\n"), cap = Math.min(L.length, n + 150);
  let depth = 0, i = n - 1, q = null;
  for (; i < cap; i++) {
    const s = L[i];
    for (let j = 0; j < s.length; j++) {
      const ch = s[j];
      if (q) { if (ch === "\\") j++; else if (s.startsWith(q, j)) { j += q.length - 1; q = null; } continue; }
      if (ch === "#") break;
      if (ch === '"' || ch === "'") { q = s.startsWith(ch.repeat(3), j) ? ch.repeat(3) : ch; j += q.length - 1; continue; }
      if ("([{".includes(ch)) depth++; else if (")]}".includes(ch)) depth--;
    }
    if (q && q.length === 1) q = null;
    if (depth <= 0 && !q && !/\\\s*$/.test(s)) break;
  }
  let end = Math.min(i, cap - 1);
  if (/:\s*(#.*)?$/.test(L[end].replace(/["'].*["']/g, ""))) {
    const ind = L[n - 1].match(/^\s*/)[0].length;
    let j = end + 1, lastBody = end;
    for (; j < cap; j++) {
      if (!L[j].trim()) continue;
      if (L[j].match(/^\s*/)[0].length <= ind) break;
      lastBody = j;
    }
    end = lastBody;
  }
  return end + 1;
}
function locate(src, find, after) {
  let start = 0;
  for (const a of after || []) { const j = src.indexOf(a, start); if (j >= 0) start = j; }
  for (const f of [].concat(find)) {
    let j = src.indexOf(f, start);
    if (j < 0) j = src.indexOf(f);
    if (j >= 0) return src.slice(0, j).split("\n").length;
  }
  return 0;
}
function go(t) {
  let file = t.file, line = t.line || 0;
  if (t.where) { const m = String(t.where).match(/^(.*?):(\d+)$/); file = m ? m[1] : t.where; line = m ? +m[2] : 0; }
  const path = resolveFile(file);
  if (!path) { $("code").innerHTML = '<div class="empty"></div>'; $("code").firstChild.textContent = file + " is not in this copy of the code."; cur = null; return; }
  open(path); clearHl();
  if (!line && t.find) line = locate(FILES[path], t.find, t.after);
  if (!line) { setHead(path, 0, 0, t.label ? t.label + " (not found in this copy)" : ""); $("code").scrollTop = 0; return; }
  const end = extent(FILES[path], line);
  for (let k = line; k <= end; k++) { const r = $("L" + k); if (r) r.classList.add("hl"); }
  setHead(path, line, end, t.label);
  const first = $("L" + line), box = $("code");
  const h = (end - line + 1) * first.offsetHeight;
  box.scrollTop = first.offsetTop - box.offsetTop - Math.max(40, (box.clientHeight - h) / 2);
}
function list(filter) {
  const nav = $("files"); nav.innerHTML = ""; let dir = null;
  Object.keys(FILES).sort().forEach(p => {
    if (filter && !p.toLowerCase().includes(filter)) return;
    const d = p.split("/").slice(0, -1).join("/");
    if (d !== dir) { dir = d; const h = document.createElement("h4"); h.textContent = d + "/"; nav.appendChild(h); }
    const b = document.createElement("button"); b.type = "button"; b.dataset.path = p; b.textContent = p.split("/").pop();
    b.setAttribute("aria-current", p === cur);
    b.onclick = () => { open(p); clearHl(); setHead(p); $("code").scrollTop = 0; };
    nav.appendChild(b);
  });
}
$("q").addEventListener("input", e => list(e.target.value.trim().toLowerCase()));
list("");
window.addEventListener("message", e => { if (e.data && e.data.codeGo) go(e.data.codeGo); });
if (window.parent !== window) parent.postMessage({ codeReady: true }, "*");
</script>
</body>
</html>
"""


def _code_files() -> dict:
    """{path relative to the repo: text} for every .py file in CODE_DIRS."""
    out = {}
    for d in CODE_DIRS:
        for f in sorted((ROOT / d).glob("*.py")):
            out[f"{d}/{f.name}"] = f.read_text(encoding="utf-8")
    return out


def _check_code_links(files: dict) -> None:
    """Warn about explorer "Show in code" targets this copy of the code no longer has."""
    if not EQ.exists():
        return
    m = re.search(r"const CODELINK = (\{.*?\});\n", EQ.read_text(encoding="utf-8"))
    if not m:
        return
    for key, targets in json.loads(m.group(1)).items():
        for t in targets:
            src = files.get(t["file"], "")
            if t["find"] not in src:
                print(f"  code link {key}: {t['find']!r} not found in {t['file']}")


def _code() -> str:
    """The Code tab: a copy of the model's Python, as a JS string."""
    files = _code_files()
    _check_code_links(files)
    stamp = datetime.now().strftime("%d %b %Y %H:%M")
    page = _CODE_PAGE.replace("__STAMP__", stamp).replace(
        "__FILES__", json.dumps(files).replace("</", "<\\/"))
    return json.dumps(page).replace("</", "<\\/")


def model_version() -> str:
    """A digest of the model as the explainer copies it: every .py file in
    CODE_DIRS and the equations page, line endings normalised. Any edit to the
    model's code or to its equations changes it."""
    import hashlib
    h = hashlib.sha256()
    parts = dict(_code_files())
    if EQ.exists():
        parts["docs/model_equations_explorer.html"] = EQ.read_text(encoding="utf-8")
    for name in sorted(parts):
        h.update(name.encode())
        h.update(parts[name].replace("\r\n", "\n").encode("utf-8"))
    return h.hexdigest()[:12]


def built_version(path: Path = HTML_OUT) -> str | None:
    """The model version a built explainer says it describes."""
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        m = MODEL_META.search(f.read(4000))
    return m.group(1) if m else None


def _map_status() -> str:
    """Which run the map numbers come from, when the maps were built, and
    whether the model's traced code has changed since (map_fingerprint)."""
    from html import escape
    try:
        meta = json.loads((OUT_DIR / "lca_map.json").read_text(encoding="utf-8"))["meta"]
    except (OSError, ValueError, KeyError):
        return "map numbers: no saved map data"
    run = (meta.get("run") or {}).get("label") or "a saved run"
    built = meta.get("generated", "?")
    try:
        built = datetime.strptime(built, "%Y-%m-%d %H:%M").strftime("%d %b %Y")
    except ValueError:
        pass
    text = f"map numbers: {escape(run)}, maps built {escape(built)}"
    try:
        from map_fingerprint import trace_code_digest
        if (meta.get("fingerprint") or {}).get("trace_code") != trace_code_digest():
            return (f'{text} · <span class="old" title="Rebuild the maps from a run made with this model: '
                    f'scripts/build_cost_map.py and build_lca_map.py">made with an earlier model</span>')
    except Exception:                                      # noqa: BLE001 - the stamp is a courtesy
        pass
    return text


def write() -> Path | None:
    """Write the model explainer from the two map pages, the equations page and
    the code; None if either map page is missing."""
    if not (COST.exists() and LCA.exists()):
        return None
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    version = model_version()
    # No commit hash: the pre-commit hook builds this before its commit exists.
    stamp = (f'model <code title="Digest of the code and equations this page shows">{version}</code>'
             f' · built {datetime.now().strftime("%d %b %Y %H:%M")} · {_map_status()}')
    HTML_OUT.write_text(_PAGE.replace("__VERSION__", version).replace("__STAMP__", stamp)
                        .replace("__COST__", _inner(COST)).replace("__LCA__", _inner(LCA))
                        .replace("__EQ__", _equations()).replace("__CODE__", _code()), encoding="utf-8")
    return HTML_OUT


if __name__ == "__main__":
    out = write()
    if out is None:
        sys.exit("both optimisation_outputs/cost_map.html and lca_map.html are needed")
    print(f"wrote {out.relative_to(ROOT)}: {out.stat().st_size / 1e6:.2f} MB, model {built_version(out)}")
