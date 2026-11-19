"""The model explainer is new whenever the model is new (user, 19 Nov 2026).

optimisation_outputs/model_explainer.html carries the version of the model it
was built from: a digest of every file it copies (the Python in optimisation/
and optimiser_lca/, and docs/model_equations_explorer.html). This fails as soon
as any of those changes and the page has not been rebuilt.
scripts/hooks/pre-commit-model-explainer.sh rebuilds it on every commit that
touches the model, once installed in the local hook; by hand:

    python scripts/build_model_explainer.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_model_explainer as X       # noqa: E402


def test_the_explainer_describes_the_current_model():
    built = X.built_version()
    assert built is not None, f"{X.HTML_OUT.relative_to(ROOT)} is missing or carries no model version: rebuild it"
    live = X.model_version()
    assert built == live, (
        f"the model explainer describes model {built} but the code is now {live}: "
        "rebuild it with python scripts/build_model_explainer.py")


def test_maps_html_is_gone():
    # Superseded by the explainer; a stray copy would be read as current.
    assert not (X.OUT_DIR / "maps.html").exists(), "optimisation_outputs/maps.html is superseded by model_explainer.html"
