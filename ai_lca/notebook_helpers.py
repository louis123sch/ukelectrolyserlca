"""Helpers shared by the notebooks/*.ipynb pipeline notebooks.

These wrap the same library functions app.py's Streamlit UI calls
(ai_lca.llm, ai_lca.review, ai_lca.brightway_search, ai_lca.brightway_writer)
so the two interfaces stay behaviourally identical. Where app.py resolves an
edit through a widget, the notebook equivalent here resolves it through a
sparse override dict read from ai_lca_config.py instead.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .brightway_search import search_candidates
from .export import process_structure_to_dataframe
from .geography import parse_flow_location_hint
from .models import InventoryExtraction


# =============================================================================
# Persistence between notebooks
# =============================================================================
def run_output_dir(output_dir: str, run_label: str) -> Path:
    d = Path(output_dir) / run_label
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_extraction(path) -> InventoryExtraction:
    return InventoryExtraction.model_validate_json(Path(path).read_text())


def save_extraction(extraction: InventoryExtraction, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(extraction.model_dump_json(indent=2))
    return path


# =============================================================================
# Diagnostics — printed narration of what a cell just did
# =============================================================================
def summarize_extraction(extraction: InventoryExtraction) -> None:
    """Print a narrative summary of an extraction: what was classified, locked, extracted."""
    n_candidates = len(extraction.candidate_activities)
    n_locked = len(extraction.processes)
    n_flows = len(extraction.flows)

    print(f"Process/system:        {extraction.process_name or '(not identified)'}")
    print(f"Functional unit:       {extraction.functional_unit or '(not identified)'}")
    print(
        f"Operational geography: {extraction.study_context.operational_geography or '(not identified)'} "
        f"[{extraction.study_context.geography_basis}]"
    )
    if extraction.provenance:
        print(
            f"Provenance:            extractor v{extraction.provenance.extractor_version} · "
            f"model {extraction.provenance.model} · commit {(extraction.provenance.git_sha or 'unknown')[:10]}"
        )
    print()
    print(
        f"{n_candidates} process-like entities were classified; {n_locked} were locked as foreground "
        "processes (role = assessed_product_system or interconnected_foreground_process)."
    )
    role_counts: dict[str, int] = {}
    for c in extraction.candidate_activities:
        role_counts[c.role] = role_counts.get(c.role, 0) + 1
    locked_roles = {"assessed_product_system", "interconnected_foreground_process"}
    for role, count in sorted(role_counts.items()):
        marker = "  -> LOCKED" if role in locked_roles else ""
        print(f"  {role:<32} {count:>3}{marker}")

    print()
    print(f"{n_flows} flow(s) extracted across {n_locked} locked process(es):")
    flow_counts: dict[str, int] = {}
    for f in extraction.flows:
        flow_counts[f.process_id] = flow_counts.get(f.process_id, 0) + 1
    names = {p.process_id: p.name for p in extraction.processes}
    for pid, count in sorted(flow_counts.items()):
        print(f"  {pid:<10} {names.get(pid, '?'):<50} {count:>3} flow(s)")

    if extraction.assumptions_or_warnings:
        print()
        print(f"{len(extraction.assumptions_or_warnings)} assumption(s)/warning(s) recorded during extraction:")
        for w in extraction.assumptions_or_warnings:
            print(f"  - {w}")


# =============================================================================
# Process review
# =============================================================================
def process_review_dataframe(extraction: InventoryExtraction, overrides: dict) -> pd.DataFrame:
    """Build the review_df apply_process_review() expects, from a sparse override dict.

    ``overrides``: {process_id: {"include": bool, "rename": str, "merge_into": str,
                                  "parent": str, "reference_product": str, "reference_unit": str}}
    Only listed processes/fields change; everything else keeps the AI proposal.
    """
    base = process_structure_to_dataframe(extraction)
    field_map = {
        "include": "include",
        "rename": "process",
        "merge_into": "merge_into",
        "parent": "parent",
        "reference_product": "reference_product",
        "reference_unit": "reference_unit",
    }
    for idx, row in base.iterrows():
        for key, column in field_map.items():
            edits = overrides.get(row["process_id"], {})
            if key in edits:
                base.at[idx, column] = edits[key]

    unknown = sorted(set(overrides) - set(base["process_id"]))
    if unknown:
        print(f"WARNING: PROCESS_REVIEW references unknown process_id(s), ignored: {unknown}")
    return base


# =============================================================================
# Inventory review
# =============================================================================
_INVENTORY_EDITABLE_FIELDS = {
    "include", "amount", "unit", "direction", "notes", "name",
    "linked_process_id", "component_or_stage", "basis", "background_process_hint",
}


def inventory_review_dataframe(inventory_df: pd.DataFrame, overrides: dict) -> pd.DataFrame:
    """Apply a sparse {flow_id: {field: value}} override dict onto the flows dataframe."""
    result = inventory_df.copy()
    known_ids = set(result["flow_id"].astype(int))
    unknown_ids = sorted(set(overrides) - known_ids)
    if unknown_ids:
        print(f"WARNING: INVENTORY_REVIEW references unknown flow_id(s), ignored: {unknown_ids}")

    for flow_id, edits in overrides.items():
        mask = result["flow_id"] == flow_id
        if not mask.any():
            continue
        for field, value in edits.items():
            if field not in _INVENTORY_EDITABLE_FIELDS:
                print(f"WARNING: flow {flow_id}: unknown review field {field!r} ignored "
                      f"(editable fields: {sorted(_INVENTORY_EDITABLE_FIELDS)})")
                continue
            result.loc[mask, field] = value
    return result


# =============================================================================
# Brightway matching
# =============================================================================
def _default_search_text(row) -> str:
    hint = str(row.get("background_process_hint", "") or "").strip()
    if hint and hint.lower() != "nan":
        return hint
    return str(row.get("name", "") or "").strip()


def _row_unit(row) -> str:
    unit = str(row.get("unit", "") or "").strip()
    return "" if unit.lower() == "nan" else unit


def search_query_for_flow(row) -> str:
    """Default search box text: the search query, annotated with the flow's unit."""
    base = _default_search_text(row)
    unit = _row_unit(row)
    if unit and not base.rstrip().endswith(f"({unit})"):
        return f"{base} ({unit})"
    return base


def strip_unit_suffix(query: str, unit: str) -> str:
    """Remove a trailing '(<unit>)' annotation before the text is actually searched."""
    unit = (unit or "").strip()
    if not unit:
        return query
    suffix = f"({unit})"
    stripped = query.rstrip()
    if stripped.endswith(suffix):
        return stripped[: -len(suffix)].strip()
    return query


def search_flow_candidates(
    row,
    *,
    project_name: str,
    database_name: str,
    biosphere_database: str | None,
    candidate_limit: int,
    location_hints: list[str],
) -> list[dict]:
    """Return Brightway candidates for one inventory flow row, or a foreground-link/error marker."""
    direction = str(row.get("direction") or "").strip().casefold()
    linked = str(row.get("linked_process_id") or "").strip()
    if linked and linked.lower() != "nan":
        return [{"foreground_link": linked, "name": f"Foreground process: {linked}"}]

    if direction == "emission":
        if not biosphere_database:
            return [{"error": "No biosphere database available in this Brightway project."}]
        search_db = biosphere_database
        flow_hints: list[str] = []
    else:
        search_db = database_name

    query = search_query_for_flow(row)
    unit = _row_unit(row)
    search_text = strip_unit_suffix(query, unit)
    if direction != "emission":
        flow_hints = list(dict.fromkeys([*location_hints, *parse_flow_location_hint(search_text)]))

    try:
        return search_candidates(
            project_name=project_name,
            database_name=search_db,
            query=search_text,
            preferred_locations=flow_hints,
            limit=candidate_limit,
        )
    except Exception as exc:
        return [{"error": str(exc)}]


def print_candidates(row, candidates: list[dict], chosen_index: int) -> None:
    flow_id = int(row["flow_id"])
    print(f"[{flow_id:>3}] {row.get('name')}  ({row.get('direction')}, {row.get('unit') or 'no unit'})"
          f"  — process {row.get('process_id')}")
    if candidates and "foreground_link" in candidates[0]:
        print(f"       -> explicit foreground link: {candidates[0]['foreground_link']} (no ecoinvent mapping needed)")
        return
    if candidates and "error" in candidates[0]:
        print(f"       ⚠ {candidates[0]['error']}")
        return
    if not candidates:
        print("       ⚠ no candidates returned — edit the flow name or SEARCH_QUERY_OVERRIDE")
        return
    for i, c in enumerate(candidates):
        marker = "  <-- selected" if i == chosen_index else ""
        print(f"       {i:>2} | {c.get('name')} | {c.get('reference_product')} | "
              f"{c.get('location')} | {c.get('unit')} | {c.get('database')}{marker}")
    if chosen_index >= len(candidates):
        print(f"       ⚠ SEARCH_CANDIDATE_INDEX={chosen_index} is out of range ({len(candidates)} candidates found)")


def build_mapping_row(row, candidates: list[dict], chosen_index: int) -> dict | None:
    """Return one selected_mappings row, or None (foreground link / error / out of range)."""
    if not candidates or "foreground_link" in candidates[0] or "error" in candidates[0]:
        return None
    if chosen_index >= len(candidates):
        return None
    direction = str(row.get("direction") or "").strip().casefold()
    chosen = candidates[chosen_index]
    return {
        "flow_id": int(row["flow_id"]),
        "process_id": row.get("process_id"),
        "process_name": row.get("process_name"),
        "flow_name": row.get("name"),
        "mapping_kind": "biosphere" if direction == "emission" else "technosphere",
        **chosen,
    }
