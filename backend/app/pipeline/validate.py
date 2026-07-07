"""Validation + normalization layer.

This runs after the LLM (or mock) returns raw JSON. It does three things:

1. Parse into Pydantic models — rejects malformed output with a typed error.
2. Normalize units: NPS stays in inches (string), pipe length in metres.
3. Re-derive gaskets, bolt sets, and summary totals deterministically.

The re-derivation is the important part. LLMs miscount gaskets and bolts on
dense drawings. The spec says "one gasket + one bolt set per flanged joint",
and a flanged joint is a PAIR of flanges. So:

    flanged_joints = (count of FLANGE items) // 2
    gaskets  = flanged_joints  (one per joint)
    bolt_sets = flanged_joints (one set per joint)

If the LLM already returned GASKET/BOLT rows, we trust the derived counts and
replace them — the derived numbers are the source of truth. We also re-compute
the summary block from the items, never trusting the LLM's own summary.

Field welds: we count items whose remarks contain "FW" or "field weld"
(case-insensitive), plus any SUPPORT items that mention weld. This is a
heuristic — the spec calls field welds a "bonus" output.
"""

from __future__ import annotations

import re
from typing import Any

from app.models.mto import Category, MTO, MTOItem, Summary
from app.pipeline.base import PipelineError


_FIELD_WELD_RE = re.compile(r"\b(FW|field\s*weld)\b", re.IGNORECASE)


def _coerce_float(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _coerce_int(v: Any) -> int:
    return int(_coerce_float(v))


def parse_and_validate(raw: dict[str, Any], *, source: str) -> MTO:
    """Parse raw LLM JSON into a validated MTO, then re-derive derived fields."""
    try:
        mto = MTO.model_validate(raw)
    except Exception as exc:
        raise PipelineError(
            f"LLM returned JSON that failed schema validation: {exc}",
            code="LLM_FAILURE",
        ) from exc

    mto.source = source
    mto.items = _renumber(_derive_gaskets_and_bolts(mto.items))
    mto.summary = _compute_summary(mto.items)
    return mto


def _derive_gaskets_and_bolts(items: list[MTOItem]) -> list[MTOItem]:
    """Replace any LLM-provided GASKET/BOLT rows with derived ones.

    A flanged joint is a pair of flanges. We count flange items, integer-divide
    by 2, and emit that many gaskets and bolt sets. We use the first flange's
    size/class/material as the template for the derived rows — a reasonable
    assumption since most lines are single-size.
    """
    flanges = [i for i in items if i.category == Category.FLANGE]
    # Remove any existing GASKET/BOLT rows — we re-derive them.
    kept = [i for i in items if i.category not in (Category.GASKET, Category.BOLT)]

    if not flanges:
        return kept

    flange_count = sum(_coerce_int(i.quantity) for i in flanges)
    joints = flange_count // 2
    if joints <= 0:
        return kept

    template = flanges[0]
    size = template.size_nps
    rating = template.schedule_rating
    # Gasket material defaults to a spiral-wound CS/Graphite if not specified.
    gasket_mat = "ASME B16.20 Spiral Wound CS/Graphite"
    bolt_mat = "ASTM A193 B7 / A194 2H"

    # item_no is renumbered later by _renumber; use 1 as a valid placeholder
    # so the MTOItem validator (ge=1) accepts the row.
    gasket = MTOItem(
        item_no=1,
        category=Category.GASKET,
        description="Spiral Wound Gasket (derived per flanged joint)",
        size_nps=size,
        schedule_rating=rating,
        material_spec=gasket_mat,
        end_type=None,
        quantity=float(joints),
        unit="EA",
        length_m=None,
        confidence=0.6,
        remarks="Derived: one gasket per flanged joint",
    )
    bolts = MTOItem(
        item_no=1,
        category=Category.BOLT,
        description=f"Stud Bolt + 2 Nuts (derived, {rating or 'Class 150'})",
        size_nps=size,
        schedule_rating=rating,
        material_spec=bolt_mat,
        end_type=None,
        quantity=float(joints),
        unit="SET",
        length_m=None,
        confidence=0.6,
        remarks="Derived: one bolt set per flanged joint",
    )
    return kept + [gasket, bolts]


def _renumber(items: list[MTOItem]) -> list[MTOItem]:
    """Re-assign sequential item_no starting at 1."""
    for idx, item in enumerate(items, start=1):
        item.item_no = idx
    return items


def _compute_summary(items: list[MTOItem]) -> Summary:
    total_pipe = 0.0
    fittings = 0
    flanges = 0
    valves = 0
    gaskets = 0
    bolt_sets = 0
    field_welds = 0

    for item in items:
        qty = _coerce_int(item.quantity)
        if item.category == Category.PIPE:
            total_pipe += _coerce_float(item.quantity)
        elif item.category == Category.FITTING:
            fittings += qty
        elif item.category == Category.FLANGE:
            flanges += qty
        elif item.category == Category.VALVE:
            valves += qty
        elif item.category == Category.GASKET:
            gaskets += qty
        elif item.category == Category.BOLT:
            bolt_sets += qty
        # Field welds: count remarks mentioning FW, plus any item whose
        # description mentions field weld. Heuristic, per spec ("bonus").
        if item.remarks and _FIELD_WELD_RE.search(item.remarks):
            field_welds += 1
        if item.description and _FIELD_WELD_RE.search(item.description):
            field_welds += 1

    return Summary(
        total_pipe_length_m=round(total_pipe, 3),
        fittings=fittings,
        flanges=flanges,
        valves=valves,
        gaskets=gaskets,
        bolt_sets=bolt_sets,
        field_welds=field_welds,
    )
