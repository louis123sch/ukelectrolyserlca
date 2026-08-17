"""
=============================================================================
AI-LCA CONFIG — single source of truth for the paper-reader notebooks.
=============================================================================

Mirrors dashboard_config.py's pattern: edit values here once, save, and every
notebook below picks them up on its next run.

The paper reader turns a source document (or pasted text) into a reviewed
Brightway foreground database, the same way FOREGROUND_DB in
dashboard_config.py already holds the built-in "hydrogen foreground"
processes. Anything it writes becomes selectable on the Setup LCA Streamlit
page (or directly via H.resolve_tech_activity in lca_helpers.py) alongside
the six built-in techs.

Intended workflow:
    1. Edit SOURCE_MODE/SOURCE_TEXT/SOURCE_DOCUMENT_PATHS and RUN_LABEL below.
    2. Run 1.paper_ingest_and_extract.ipynb top to bottom — this is the only
       notebook that calls the LLM. It prints every process_id/flow_id it
       created.
    3. Come back here and fill in PROCESS_REVIEW using the process_id values
       just printed, save, then run 1.1.paper_process_review.ipynb.
    4. Fill in INVENTORY_REVIEW using the flow_id values 1.1 printed, save,
       then run 1.2.paper_inventory_review.ipynb.
    5. Run 1.3.paper_brightway_matching.ipynb, inspect the printed candidate
       lists, adjust SEARCH_CANDIDATE_INDEX / SEARCH_QUERY_OVERRIDE and re-run
       as needed.
    6. Set CONFIRM_WRITE_FOREGROUND = True and run
       1.4.paper_write_foreground.ipynb to create NEW_FOREGROUND_DB_NAME.

This file only ever holds settings and edit instructions — never an OpenAI or
Renewables.ninja key. Put those in this repo's own .env (see .env.example).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# The ai_lca package (paper-extraction library: LLM prompts, document
# ingestion, Brightway search/writer) is vendored in ./ai_lca — no sibling
# repo or sys.path setup needed; it's an ordinary local package next to
# dashboard_config.py/lca_helpers.py.
load_dotenv()

# =============================================================================
# OpenAI / extraction settings
# =============================================================================
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
EXTRA_INSTRUCTIONS = ""   # optional study-specific disambiguation for the LLM

# =============================================================================
# Source material
# =============================================================================
SOURCE_MODE = "documents"          # "text" or "documents"
SOURCE_TEXT = ""                   # used when SOURCE_MODE == "text"
SOURCE_DOCUMENT_PATHS: list[str] = [
    # "papers/my_paper.pdf",
    # "papers/my_paper_supplementary.xlsx",
]
MAX_VISUAL_ASSETS = 24

# =============================================================================
# Run identity / output location
# =============================================================================
RUN_LABEL = "my_paper"             # short slug; outputs go to OUTPUT_DIR/RUN_LABEL/
OUTPUT_DIR = "ai_lca_outputs"

# =============================================================================
# Brightway project / matching — deliberately read from dashboard_config.py
# rather than a separate env var, since that's the actual single source of
# truth: anything written here needs to land in the same project
# dashboard_config.py / lca_helpers.H.resolve_tech_activity read from.
# =============================================================================
import dashboard_config as _dashboard_cfg  # noqa: E402

BRIGHTWAY_PROJECT = _dashboard_cfg.PROJECT_NAME
TECHNOSPHERE_DATABASE = ""         # e.g. "ecoinvent-3.9.1-apos"; blank = auto-pick first non-biosphere db
CANDIDATE_LIMIT = 8

# =============================================================================
# Process review — edits applied on top of the AI-proposed process structure.
# Only list processes you want to change; anything unlisted keeps the AI
# proposal. Fill these in AFTER running notebook 1, using the process_id
# values it printed.
# =============================================================================
PROCESS_REVIEW: dict[str, dict] = {
    # "P1": {"include": True, "rename": "PEM electrolyser operation"},
    # "P2": {"merge_into": "P1"},
    # "P3": {"include": False},
}

# =============================================================================
# Inventory review — edits applied on top of the AI-proposed flow list.
# Keyed by flow_id (printed by notebooks 1/1.1). Only list flows you want to
# change.
# =============================================================================
INVENTORY_REVIEW: dict[int, dict] = {
    # 4: {"include": False},
    # 7: {"amount": 12.3, "unit": "kilogram"},
}

# =============================================================================
# Brightway candidate selection — mirrors GRID_CANDIDATE_INDEX in
# dashboard_config.py. 0 = top search hit. Only list flows where you want
# something other than the top match.
# =============================================================================
SEARCH_CANDIDATE_INDEX: dict[int, int] = {
    # 4: 2,
}
SEARCH_QUERY_OVERRIDE: dict[int, str] = {
    # 4: "market for electricity, low voltage GB",
}

# =============================================================================
# Foreground database write
# =============================================================================
NEW_FOREGROUND_DB_NAME = f"ai_lca_{RUN_LABEL}"
# Safety gate: 1.4.paper_write_foreground.ipynb refuses to write unless this
# is explicitly True, even if the write plan is otherwise ready.
CONFIRM_WRITE_FOREGROUND = False


# =============================================================================
# Derived settings / validation — do not normally edit below this line
# =============================================================================
if SOURCE_MODE not in ("text", "documents"):
    raise ValueError("SOURCE_MODE must be 'text' or 'documents'")

RUN_DIR = Path(OUTPUT_DIR) / RUN_LABEL


def print_config():
    """Print the active configuration. Useful at the top of every notebook."""
    print("AI-LCA Config")
    print("-------------")
    print("Run label:              ", RUN_LABEL, "| outputs ->", RUN_DIR)
    print("Source mode:            ", SOURCE_MODE)
    if SOURCE_MODE == "documents":
        print("Source documents:       ", SOURCE_DOCUMENT_PATHS or "(none set)")
    else:
        print("Source text:            ", f"{len(SOURCE_TEXT)} character(s)")
    print("OpenAI model:           ", OPENAI_MODEL,
          "| key set:", bool(os.getenv("OPENAI_API_KEY")) and os.getenv("OPENAI_API_KEY") != "replace_me")
    print("Brightway project:      ", BRIGHTWAY_PROJECT)
    print("Technosphere database:  ", TECHNOSPHERE_DATABASE or "(auto)")
    print("Candidate limit:        ", CANDIDATE_LIMIT)
    print("Process review entries: ", len(PROCESS_REVIEW))
    print("Inventory review entries:", len(INVENTORY_REVIEW))
    print("Candidate index overrides:", len(SEARCH_CANDIDATE_INDEX))
    print("New foreground DB name: ", NEW_FOREGROUND_DB_NAME)
    print("Confirmed for write:    ", CONFIRM_WRITE_FOREGROUND)
