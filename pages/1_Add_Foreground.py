"""Add Foreground — embeds the ai-lca-starter paper-to-Brightway extractor.

Runs the sibling ai-lca-starter repo's app.py in place (via runpy) so this
page always matches upstream with no forked/duplicated copy. It points the
extractor at this project's own Brightway project by default, so anything it
writes shows up immediately in the Setup LCA page's foreground picker.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dashboard_config as cfg

AI_LCA_STARTER_DIR = Path(
    os.getenv("AI_LCA_STARTER_DIR", Path(__file__).resolve().parent.parent.parent / "ai-lca-starter")
)
APP_PY = AI_LCA_STARTER_DIR / "app.py"

if not APP_PY.exists():
    st.set_page_config(page_title="Add Foreground", layout="wide")
    st.error(
        f"Could not find ai-lca-starter at {AI_LCA_STARTER_DIR}.\n\n"
        "Clone it next to this repo (as a sibling directory named `ai-lca-starter`), "
        "or set the AI_LCA_STARTER_DIR environment variable to its location."
    )
    st.stop()

# ai-lca-starter is a src-layout package (src/ai_lca); make it importable even
# if it hasn't been `pip install -e`'d into this environment.
src_dir = str(AI_LCA_STARTER_DIR / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Default the extractor's Brightway project to this project's own, so a
# written foreground database is immediately visible on the Setup LCA page.
os.environ.setdefault("BRIGHTWAY_PROJECT", cfg.PROJECT_NAME)

# ai_lca.runtime.git_sha() shells out to `git rev-parse HEAD` in the current
# working directory to stamp extraction provenance. Since this page runs
# app.py via runpy, that cwd is this repo, not ai-lca-starter's — without this
# override every extraction would be (mis)labelled with ukelectrolyserlca's
# commit instead of the extractor's own. AI_LCA_GIT_SHA is the override
# ai_lca.runtime.git_sha() already checks first, so this doesn't touch its code.
if "AI_LCA_GIT_SHA" not in os.environ:
    import subprocess
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=AI_LCA_STARTER_DIR,
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        if sha:
            os.environ["AI_LCA_GIT_SHA"] = sha
    except (OSError, subprocess.SubprocessError):
        pass

# ai-lca-starter keeps OPENAI_API_KEY etc. in its own .env; load it explicitly
# since Streamlit's cwd here is this repo, not that one. A local .env (if any)
# is loaded second so it can override without needing to touch the sibling repo.
load_dotenv(AI_LCA_STARTER_DIR / ".env")
load_dotenv()

runpy.run_path(str(APP_PY), run_name="__main__")
