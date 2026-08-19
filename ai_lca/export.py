from __future__ import annotations

import json
import math
import re

import pandas as pd

from .models import InventoryExtraction, InventoryFlow


_DIGIT_RE = re.compile(r"\d")


def _unquantified_flag(flow: InventoryFlow) -> str:
    """Return a short warning if a flow looks like descriptive prose rather than a
    quantified inventory item, else "".

    Purely a UI safety net on top of the extraction prompt: defaults such flows to
    excluded in the review table so a human consciously re-includes them, instead of
    e.g. every bare name in a "the system includes chillers, pumps, ..." scope
    sentence silently flowing into Brightway search looking like real LCI data.
    """
    if flow.amount is not None:
        return ""
    if flow.background_process_hint:
        return ""  # an explicit background-process export entry backs this one
    if flow.linked_process_id:
        return ""  # explicit foreground-to-foreground link, not a background search
    evidence_text = flow.evidence.evidence_text or ""
    if not _DIGIT_RE.search(evidence_text):
        return "No amount, and no quantity anywhere in the evidence -- looks like descriptive text, not a modeled exchange. Verify before mapping."
    if flow.direction == "output":
        return "Output with no amount or mapping hint -- check this isn't just restating the functional unit/reference product."
    return ""


_REVIEWED_FIELDS = (
    "include",
    "process_id",
    "name",
    "amount",
    "unit",
    "direction",
    "linked_process_id",
    "component_or_stage",
    "basis",
    "background_process_hint",
    "uncertainty_lower",
    "uncertainty_upper",
    "notes",
)


def _comparable(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def ensure_flow_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with unique integer flow IDs, including human-added editor rows."""
    result = df.copy()
    if "flow_id" not in result.columns:
        result.insert(0, "flow_id", pd.NA)

    used: set[int] = set()
    next_id = 0
    normalized: list[int] = []
    for raw in result["flow_id"].tolist():
        parsed: int | None = None
        try:
            if raw is not None and not pd.isna(raw):
                candidate = int(raw)
                if candidate >= 0 and candidate not in used:
                    parsed = candidate
        except (TypeError, ValueError, OverflowError):
            parsed = None

        if parsed is None:
            while next_id in used:
                next_id += 1
            parsed = next_id
        used.add(parsed)
        next_id = max(next_id, parsed + 1)
        normalized.append(parsed)

    result["flow_id"] = normalized
    return result


def extraction_to_dataframe(extraction: InventoryExtraction) -> pd.DataFrame:
    rows = []
    process_names = {p.process_id: p.name for p in extraction.processes}
    for i, flow in enumerate(extraction.flows):
        flag_reason = _unquantified_flag(flow)
        rows.append(
            {
                "include": not flag_reason,
                "flow_id": i,
                "review_status": "ai_proposed",
                "review_flag": flag_reason,
                "process_id": flow.process_id,
                "process_name": process_names.get(flow.process_id, ""),
                "name": flow.name,
                "amount": flow.amount,
                "unit": flow.unit,
                "direction": flow.direction,
                "linked_process_id": flow.linked_process_id,
                "component_or_stage": flow.component_or_stage,
                "basis": flow.basis,
                "background_process_hint": flow.background_process_hint,
                "uncertainty_lower": flow.uncertainty_lower,
                "uncertainty_upper": flow.uncertainty_upper,
                "document": flow.evidence.document,
                "page": flow.evidence.page,
                "paragraph": flow.evidence.paragraph,
                "table": flow.evidence.table,
                "evidence_text": flow.evidence.evidence_text,
                "notes": flow.notes,
            }
        )
    return pd.DataFrame(rows)


def normalize_inventory_review(
    df: pd.DataFrame,
    *,
    extraction: InventoryExtraction,
    original_extraction: InventoryExtraction,
) -> pd.DataFrame:
    """Normalize editor rows and label source-derived, human-edited and user-added flows.

    Source evidence columns are never used to determine edit status and should be
    read-only in the UI. This records edits without overwriting the original AI/source
    extraction preserved separately in the review bundle.
    """
    result = ensure_flow_ids(df)
    process_names = {p.process_id: p.name for p in extraction.processes}
    if "process_name" not in result.columns:
        result["process_name"] = ""
    result["process_name"] = [
        process_names.get(str(pid).strip(), "") if _comparable(pid) is not None else ""
        for pid in result.get("process_id", pd.Series([None] * len(result))).tolist()
    ]

    original_df = extraction_to_dataframe(original_extraction)
    original_rows = {
        int(row["flow_id"]): row
        for _, row in original_df.iterrows()
    }

    statuses: list[str] = []
    for _, row in result.iterrows():
        flow_id = int(row["flow_id"])
        original = original_rows.get(flow_id)
        if original is None:
            statuses.append("user_added")
            continue
        changed = any(
            _comparable(row.get(field)) != _comparable(original.get(field))
            for field in _REVIEWED_FIELDS
        )
        statuses.append("human_edited" if changed else "ai_proposed")
    result["review_status"] = statuses
    return result


def process_structure_to_dataframe(extraction: InventoryExtraction) -> pd.DataFrame:
    rows = []
    for process in extraction.processes:
        evidence = process.evidence[0].evidence_text if process.evidence else ""
        rows.append(
            {
                "include": True,
                "process_id": process.process_id,
                "process": process.name,
                "merge_into": "",
                "parent": process.parent_process_id or "",
                "role": process.role,
                "reference_product": process.reference_product or "",
                "reference_unit": process.reference_unit or "",
                "classification_rationale": process.classification_rationale or "",
                "stage": process.stage,
                "evidence": evidence,
            }
        )
    return pd.DataFrame(rows)


def _slugify_process_id(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_").upper()
    return slug or "PROCESS"


def _process_id_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def normalize_process_review(df: pd.DataFrame, *, extraction: InventoryExtraction) -> pd.DataFrame:
    """Assign a stable, unique process_id to any human-added row from the dynamic editor.

    Mirrors ensure_flow_ids: runs immediately after the process st.data_editor so a newly
    inserted row gets a permanent id before "Apply process review" -- or a later rerun --
    sees it again. A row with no process name typed yet is left with a blank id.
    """
    result = df.copy()
    used: set[str] = {process.process_id for process in extraction.processes}
    for raw in result.get("process_id", pd.Series(dtype=object)).tolist():
        existing = _process_id_text(raw)
        if existing:
            used.add(existing)

    new_ids: list[str] = []
    for _, row in result.iterrows():
        existing = _process_id_text(row.get("process_id"))
        if existing:
            new_ids.append(existing)
            continue
        name = str(row.get("process") or "").strip()
        if not name:
            new_ids.append("")
            continue
        base = _slugify_process_id(name)
        candidate = base
        n = 2
        while candidate in used:
            candidate = f"{base}_{n}"
            n += 1
        used.add(candidate)
        new_ids.append(candidate)

    result["process_id"] = new_ids
    return result


def reported_results_to_dataframe(extraction: InventoryExtraction) -> pd.DataFrame:
    """The source's own reported numeric result(s), for comparison against a recreated LCA."""
    rows = []
    for result in extraction.reported_results:
        rows.append({
            "scenario_name": result.scenario_name,
            "value": result.value,
            "unit": result.unit,
            "impact_category": result.impact_category,
            "evidence_text": result.evidence.evidence_text,
        })
    return pd.DataFrame(rows)


def candidate_structure_to_dataframe(extraction: InventoryExtraction) -> pd.DataFrame:
    rows = []
    locked = {process.process_id for process in extraction.processes}
    for candidate in extraction.candidate_activities:
        evidence = candidate.evidence[0].evidence_text if candidate.evidence else ""
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "role": candidate.role,
                "locked_as_process": candidate.candidate_id in locked,
                "parent_candidate_id": candidate.parent_candidate_id or "",
                "reference_product": candidate.reference_product or "",
                "reference_unit": candidate.reference_unit or "",
                "rationale": candidate.rationale,
                "evidence": evidence,
            }
        )
    return pd.DataFrame(rows)


def _records(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records"))


def dataframe_to_json(df: pd.DataFrame) -> str:
    return json.dumps(_records(df), indent=2, ensure_ascii=False)


def review_bundle_to_json(
    extraction: InventoryExtraction,
    inventory_df: pd.DataFrame,
    mapping_df: pd.DataFrame | None = None,
    *,
    original_extraction: InventoryExtraction | None = None,
) -> str:
    """Export both the untouched AI proposal and the final human-reviewed state."""
    original = original_extraction or extraction
    payload = {
        "original_ai_extraction": original.model_dump(mode="json"),
        "reviewed_extraction": extraction.model_dump(mode="json"),
        "reviewed_inventory": _records(inventory_df),
        "selected_mappings": _records(mapping_df),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
