# Streamlit in this project — and how to use it for one like it

This note is in two halves. The first explains what Streamlit *is* and the
mental model you need to write anything non-trivial in it. The second walks
through how this repo uses it, page by page, and the handful of patterns that
took real effort to get right — the ones you would want to copy into a
similar project (a research model with a UI on top) rather than rediscover.

Streamlit version at time of writing: 1.61.

---

## Part 1 — How Streamlit works

### It is a script, re-run from the top

A Streamlit app is an ordinary Python file. `streamlit run Home.py` starts a
web server that executes the file top to bottom and turns every `st.*` call
into a widget on the page, in the order the calls happen. There is no
callback graph, no component tree, no routing — just a script.

The one idea that makes it all work: **every time the user touches a widget,
the whole script runs again from the top**, and the widget calls return the
new values. So

```python
mw = st.number_input("Rating (MW)", 0.1, 1000.0, 10.0)
st.write(f"Annual energy: {mw * 8760:,.0f} MWh")
```

is a live calculator. Change the number, the script re-runs, `mw` is the new
value, the second line prints the new answer. You write it as if it were a
one-shot script and Streamlit supplies the interactivity.

Everything else in Streamlit is a consequence of that model — or a tool for
coping with it.

### Consequence 1: local variables do not survive a rerun

Each rerun is a fresh execution. A result you computed on the previous run is
gone unless you put it somewhere that persists. The place is
`st.session_state`, a dict scoped to one browser tab:

```python
if st.button("Run"):
    st.session_state["result"] = expensive_solve(...)

r = st.session_state.get("result")
if r:
    show(r)          # still shown on later reruns, e.g. after moving a slider
```

Without the `session_state` line, the result would appear on the rerun the
button click triggered and vanish on the next one, because `st.button`
returns `True` only on that single rerun.

`session_state` is also where widget values live if you give the widget a
`key=`. `st.number_input("Lat", key="lat")` and `st.session_state["lat"]`
are the same thing, which is how you set a widget *from code* (a preset that
fills in coordinates, say). One rule bites everyone: you cannot write to a
widget's key on the same rerun *after* that widget has already been rendered.
Set it before, or in an `on_change` callback, which runs before the rerun.

### Consequence 2: expensive things must be cached

If the script reruns on every keystroke, anything slow in it makes every
keystroke slow. Two decorators solve this:

- `@st.cache_data` — memoises a function on its arguments and returns a
  *copy* of the result. For data: DataFrames, dicts, numbers. The cache is
  shared across sessions and survives reruns.
- `@st.cache_resource` — memoises once and returns the *same object* every
  time. For connections and handles: a database, a model, a Brightway
  project.

```python
@st.cache_resource
def connect():
    H.setup_brightway()          # slow, once per server lifetime
    return True

@st.cache_data
def load_profiles(lat, lon, start, end):
    return profiles.build(lat, lon, start, end)   # slow, once per site/window
```

Arguments must be hashable (strings, numbers, tuples — not DataFrames unless
you tell it how), and the function should be pure.

### Consequence 3: the script belongs to the browser session

The script runs inside a session tied to one browser tab. Close the tab or
navigate away and the run is abandoned. A ten-second computation is fine to
run inline with `st.spinner`. A twenty-minute one is not — see Part 2 for
what this project does about that.

### Layout is procedural

There is no template. Layout primitives are context managers or objects you
call methods on:

```python
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Wind", "120 MW")
c2.metric("Solar", "80 MWp")          # same thing, method style

with st.expander("Details"):
    st.dataframe(df)

box = st.container(border=True)
box.progress(0.4, text="LP 4 of 10")
```

`st.sidebar`, `st.tabs`, `st.form` (batch several inputs behind one submit
so they do not each trigger a rerun) round out the set. `st.stop()` ends the
script early — the usual way to say "nothing below makes sense until you fix
the thing above".

### Multipage apps

Put extra scripts in a `pages/` directory next to the entry script and
Streamlit builds a sidebar from them. The filename is the label: leading
digits sort, underscores become spaces, so `pages/2_Data_Centre_Optimiser.py`
appears as "Data Centre Optimiser" in position 2. Each page is its own
script with its own reruns; `session_state` is shared across pages within a
tab.

### Charts and other outputs

`st.line_chart`, `st.bar_chart` etc. draw quickly from a DataFrame. For
anything with control over encodings, `st.altair_chart` (Vega-Lite) is the
best-integrated option and, since 1.35, its selections can drive reruns
(`on_select="rerun"`), which is how a click on a chart becomes an input.
`st.pyplot`, `st.plotly_chart` and `st.image` are there too.
`st.dataframe` is an interactive table; `st.download_button` hands the user
a file.

### Running it

```bash
streamlit run Home.py
```

Serves on `http://localhost:8501`. `--server.headless true` stops it opening
a browser; `--server.port` changes the port. Editing a page and saving shows
a "rerun" prompt in the browser. Note that imported modules are *not*
reloaded on rerun — only the page script is (see the reload trick in Part 2).

### What Streamlit is and is not good for

Good: a UI over a Python model for a small audience, built in an afternoon by
the person who wrote the model. Dashboards, parameter explorers, internal
tools.

Poor fit: many concurrent users, fine-grained UI state, anything that needs
to react without a full rerun, long-running jobs (natively), authentication.
It is a research-tool framework, and it is excellent at exactly that.

---

## Part 2 — How this repo uses it

### The shape

```
Home.py                          entry point; project status, latest results
pages/
  1_Setup_LCA.py                 configure and run the electrolyser LCA
  2_Data_Centre_Optimiser.py     the data-centre sizing study, one page
  3_Size_Optimiser.py            cheapest wind/solar/battery for a fixed electrolyser
backend/runner.py                runs the LCA notebook as a subprocess (no Streamlit)
optimisation/                    the science (no Streamlit)
lca_helpers.py                   Brightway helpers (no Streamlit)
```

`.claude/launch.json` holds the run configurations (`streamlit-win` on port
8502 uses the `brightway` conda env's `streamlit.exe`).

### Rule zero: Streamlit never holds the science

Only the four page scripts `import streamlit`. Every number the pages show
comes from a function in `optimisation/`, `lca_helpers.py` or a notebook,
and the page's job is to collect settings, call the function, and display
what comes back. The page-2 docstring says it directly: "there is never a
second implementation to keep in sync."

This is the single most transferable decision. It means:

- the model is testable without a browser (`tests/` exercises
  `optimisation/` directly);
- notebooks and the app produce the same answer because they call the same
  code;
- the page can be rewritten, or replaced with a different framework, without
  touching a coefficient.

The concrete test for a new project: can you run the whole calculation from
a plain Python prompt? If a page contains a formula that exists nowhere else,
move it out.

### Page 1 — Setup LCA: run the existing notebook, don't reimplement it

The LCA pipeline already existed as `1.dashboard_lca_adaptive.ipynb`, driven
by `dashboard_config.py`. Rather than port that into Python callable from the
page, the page **patches the config file and runs the notebook** via
`jupyter nbconvert` in a subprocess (`backend/runner.py`). The results are
whatever CSVs and figures the notebook wrote; the page reads them off disk
and displays them.

Streamlit-wise this is plain: widgets collect settings, a button triggers
`run_lca(...)`, `st.spinner` while it runs, `st.dataframe` / `st.line_chart`
/ `st.image` on what came back, `st.expander` for the log. Because it edits
a shared file, only one LCA can run at a time — the README says so.

The lesson: when a working pipeline exists in notebook form, wrapping it is
often the right first move. The port can come later, once the UI has proved
what people actually want to change.

### Page 3 — Size Optimiser: the textbook inline pattern

This is the simplest page to learn from, because the search is short enough
to run inside the script. The pattern is exactly the one from Part 1:

1. `@st.cache_resource` for the Brightway connection.
2. `@st.cache_data` for the electrolyser coefficients (a Brightway lookup
   that would otherwise repeat on every slider notch).
3. `st.button("Find the optimal build")` guards the solve.
4. A progress callback: the optimiser in `optimisation/sizing.py` accepts a
   `progress=` function, and the page passes one that updates
   `st.progress`. The science module knows nothing about Streamlit; it just
   calls a function it was handed.
5. The result goes into `st.session_state["sizing_result"]` so it stays on
   screen while the user reads the coefficients, downloads the CSV, or
   adjusts an input.

If you are building a similar tool and the solve takes under a minute, copy
this page's structure.

### Page 2 — Data Centre Optimiser: the hard patterns

This page is 1,700 lines and has most of the Streamlit knowledge in the repo.
Four patterns are worth understanding.

#### (a) A solve that outlives the browser tab

The Pareto sweep takes tens of minutes. Run inline, a refresh or a mis-click
would kill it and lose everything. So `optimisation/dc_job.py` launches the
solve as a **detached child process** and the page becomes a *viewer of
files*:

```
page                          child (own process group)
----                          -------------------------
write request.json   ---->    read request.json
launch, then forget           run_one(..., progress=tick)
poll status.json     <----    write status.json each LP
read summary.json    <----    run_one writes it at the end
```

Nothing about the run is held in `session_state`. `dc_job.active()` reads a
pointer file, so a second tab, a refresh, or Streamlit restarted an hour
later all find the same run. The page shows `st.progress` from
`status.json`, a Stop button that calls `dc_job.cancel`, a Refresh button
that does nothing except cause a rerun (which re-reads the file), and on
`state == "done"` copies the summary into `session_state` for display.

This is the pattern for *any* Streamlit app whose work takes longer than a
user's patience. The general recipe: the page writes a request, spawns a
process, and thereafter only reads status from disk. Liveness is checked
(`_alive`) rather than assumed, so a crashed child shows as "lost" rather
than a bar frozen at 40 %. Platform differences (POSIX vs Windows process
groups, `CREATE_NO_WINDOW`) are confined to that one module.

#### (b) Making a chart click into an input

The site map is an Altair chart with `on_select="rerun"`. Two subtleties:

- The click arrives as the chart's widget state on the rerun it triggers,
  and Streamlit refuses to let you write a widget's key after that widget
  has rendered. So the click is consumed *above* the latitude/longitude
  inputs it feeds (`_map_click()` near the top of the section), not next to
  the chart.
- The chart's `key` includes the current coordinate (`_map_key()`). With a
  fixed key, clicking the same point twice produces no state change, so no
  rerun, so a dead click. A key that moves with the coordinate hands every
  rerun a fresh chart with an empty selection. Stale keys are swept from
  `session_state` each run.

The result is that the map and the two number inputs are literally the same
input — `st.session_state["dc_lat"]` / `["dc_lon"]` — whichever way the user
sets it.

#### (c) Widgets that depend on each other

The infrastructure tick-boxes have enforced dependencies (wind or solar
requires a battery; any hydrogen source requires a fuel cell and tank).
Rather than warn, the page sets the dependent box's `session_state` key to
`True` *before* rendering it and renders it `disabled=`. Same rule as (b):
write the key first, render the widget second. Presets use `on_change=`
callbacks for the same reason — a callback runs before the rerun, so it may
write keys freely.

One small compatibility habit is visible here: when a control changed from
single-select to multi-select, a session created before the change could
have a bare string in its state where a list now belongs. The page coerces
it. Worth remembering for any app people keep open across code changes.

#### (d) Reloading the science modules during development

Streamlit reruns the page script on edit but keeps imported modules in
`sys.modules`, so editing `optimisation/dc_model.py` would need a full
restart to show up. Page 2 calls `importlib.reload` on every module in its
dependency closure, leaves first. The comment in the file spells out the
trap: reloading `dc_runner` alone leaves it bound to a stale `dc_pareto`,
which surfaces as a confusing `TypeError`. Fine for small, pure modules
during development; drop it for deployment.

### Smaller habits worth copying

- **Anchor paths to the repo, not the working directory.** Streamlit does
  not `chdir` to the script; launching from a shortcut or another folder
  silently found no results until `Home.py` switched to `REPO_DIR / folder`.
- **`sys.path.insert(0, REPO_DIR)`** at the top of each page so pages can
  import repo modules regardless of how the app was launched.
- **Capture module output.** `_capture()` on page 2 redirects stdout while
  a science function runs and shows it in an expander, so the cross-checks
  and caveats the modules print are visible without polluting the page.
- **Results describe the run, not the current widgets.** After a solve, the
  page labels the answer using the settings *stored with the result*, not
  the tick-boxes as they are now — changing a box without re-optimising must
  not relabel an old answer.
- **`st.stop()` early** when a precondition fails (Brightway unavailable, no
  foreground databases) rather than guarding everything below.
- **Coefficients next to the answer.** Page 2 puts the assumptions tables
  at the bottom of the same page as the result, "because reading the two
  apart is how a wrong number survives." A layout decision, but one Streamlit
  makes cheap.

---

## Starting a similar project: a checklist

1. Write the model as importable functions with a `progress=` callback
   parameter and no UI imports. Get it working from a notebook or `python -c`.
2. `Home.py` plus `pages/` with numbered filenames. One page per question
   the tool answers.
3. `@st.cache_resource` for connections, `@st.cache_data` for anything that
   reads data or hits an API. Keep cached functions pure and their arguments
   hashable.
4. Guard solves with a button; store results in `st.session_state`.
5. If a solve can exceed a minute or so, do not run it inline. Copy the
   detached-job pattern from `optimisation/dc_job.py`: request file, spawned
   process, status file, page polls.
6. Set widget keys before rendering the widget, or in `on_change`. Never
   after.
7. Anchor all paths to the repo root.
8. Put a `launch.json` or a one-line `streamlit run` in the README so the
   next person can start it.
