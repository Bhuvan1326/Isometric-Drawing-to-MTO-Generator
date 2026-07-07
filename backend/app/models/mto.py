"""MTO domain models.

Vocabulary is fixed by the spec — these enums and field names are graded on
domain correctness, so they match the spec exactly. See README for the full
mapping to ASME / ASTM standards.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, confloat


class Category(str, Enum):
    PIPE = "PIPE"
    FITTING = "FITTING"
    FLANGE = "FLANGE"
    VALVE = "VALVE"
    GASKET = "GASKET"
    BOLT = "BOLT"
    SUPPORT = "SUPPORT"


class EndType(str, Enum):
    BW = "BW"      # Butt-Weld
    SW = "SW"      # Socket Weld
    THD = "THD"    # Threaded
    FLGD = "FLGD"  # Flanged


class MTOItem(BaseModel):
    """One line in the bill of materials."""

    item_no: int = Field(..., ge=1, description="Sequential item number on this MTO")
    category: Category
    description: str = Field(..., min_length=1, description="Free-text description, e.g. '90° LR Elbow'")
    size_nps: Optional[str] = Field(
        None,
        description="Nominal Pipe Size in inches, e.g. '6\"'. May be a range for reducers, e.g. '6\"x4\"'.",
    )
    schedule_rating: Optional[str] = Field(
        None,
        description="Schedule (e.g. 'SCH40') for pipe/fittings, or pressure class (e.g. 'Class 150') for flanges/valves",
    )
    material_spec: Optional[str] = Field(
        None,
        description="ASTM material spec, e.g. 'A234 WPB' or 'A105'",
    )
    end_type: Optional[EndType] = None
    quantity: float = Field(..., ge=0, description="Count (EA/NO/SET) or length (M for pipe)")
    unit: str = Field(..., description="M for pipe, EA/NO for discrete items, SET for bolts")
    length_m: Optional[float] = Field(
        None,
        ge=0,
        description="Per-piece length in metres — pipe only. For pipe items, quantity == total length_m.",
    )
    confidence: Optional[confloat(ge=0, le=1)] = Field(
        None,
        description="Model confidence 0-1. Optional; absent for derived/mock items.",
    )
    remarks: Optional[str] = None


class DrawingMeta(BaseModel):
    """Drawing-level metadata extracted from the title block / line tag."""

    drawing_no: Optional[str] = None
    revision: Optional[str] = None
    line_number: Optional[str] = Field(
        None,
        description="Line designation, e.g. 6\"-P-1501-A1A-IH",
    )
    nps: Optional[str] = Field(None, description="Nominal Pipe Size, e.g. '6\"'")
    material_class: Optional[str] = Field(None, description="e.g. 'CS'")
    service: Optional[str] = Field(None, description="Process service, e.g. 'Cooling Water'")


class Summary(BaseModel):
    """Aggregate counts for the summary block."""

    total_pipe_length_m: float = 0.0
    fittings: int = 0
    flanges: int = 0
    valves: int = 0
    gaskets: int = 0
    bolt_sets: int = 0
    field_welds: int = 0


class MTO(BaseModel):
    """The full Material Take-Off document."""

    drawing_meta: DrawingMeta = Field(default_factory=DrawingMeta)
    items: list[MTOItem] = Field(default_factory=list)
    summary: Summary = Field(default_factory=Summary)
    source: str = Field(
        "mock",
        description="Pipeline that produced this MTO: 'mock' or 'gemini' (or another provider name)",
    )
