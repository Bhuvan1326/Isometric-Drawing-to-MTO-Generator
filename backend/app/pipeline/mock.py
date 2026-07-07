"""Mock pipeline — the graceful-degradation fallback.

Activated when GEMINI_API_KEY is not set (see app/config.py). Returns a
realistic, clearly-labelled sample MTO so the app is demoable end-to-end
without an API key. The returned MTO has source='mock' and every item carries
a remarks tag so the UI can show it's a sample.
"""

from __future__ import annotations

from pathlib import Path

from app.models.mto import (
    Category,
    DrawingMeta,
    EndType,
    MTO,
    MTOItem,
    Summary,
)
from app.pipeline.base import Pipeline
from app.pipeline.validate import parse_and_validate


# A realistic 6" carbon-steel cooling-water line. This is the kind of MTO a
# junior engineer would produce from a clean CAD isometric. We feed it through
# parse_and_validate so the derived gaskets/bolts and summary are computed by
# the same code path as the real pipeline — the mock exercises the validator.
_MOCK_RAW = {
    "drawing_meta": {
        "drawing_no": "ISO-P-1501-001",
        "revision": "B",
        "line_number": '6"-P-1501-A1A-IH',
        "nps": '6"',
        "material_class": "CS",
        "service": "Cooling Water Supply",
    },
    "items": [
        {
            "item_no": 1, "category": "PIPE",
            "description": "Seamless Pipe, 6\" SCH40",
            "size_nps": '6"', "schedule_rating": "SCH40",
            "material_spec": "ASTM A106 Gr.B", "end_type": "BW",
            "quantity": 18.5, "unit": "M", "length_m": 18.5,
            "confidence": 0.9, "remarks": "MOCK SAMPLE — total straight run",
        },
        {
            "item_no": 2, "category": "FITTING",
            "description": "90° LR Elbow, 6\" SCH40",
            "size_nps": '6"', "schedule_rating": "SCH40",
            "material_spec": "ASTM A234 WPB", "end_type": "BW",
            "quantity": 4, "unit": "EA", "length_m": None,
            "confidence": 0.95, "remarks": "MOCK SAMPLE",
        },
        {
            "item_no": 3, "category": "FITTING",
            "description": "45° LR Elbow, 6\" SCH40",
            "size_nps": '6"', "schedule_rating": "SCH40",
            "material_spec": "ASTM A234 WPB", "end_type": "BW",
            "quantity": 2, "unit": "EA", "length_m": None,
            "confidence": 0.9, "remarks": "MOCK SAMPLE",
        },
        {
            "item_no": 4, "category": "FITTING",
            "description": "Equal Tee, 6\" SCH40",
            "size_nps": '6"', "schedule_rating": "SCH40",
            "material_spec": "ASTM A234 WPB", "end_type": "BW",
            "quantity": 1, "unit": "EA", "length_m": None,
            "confidence": 0.9, "remarks": "MOCK SAMPLE",
        },
        {
            "item_no": 5, "category": "FITTING",
            "description": "Concentric Reducer 6\"x4\" SCH40",
            "size_nps": '6"x4"', "schedule_rating": "SCH40",
            "material_spec": "ASTM A234 WPB", "end_type": "BW",
            "quantity": 1, "unit": "EA", "length_m": None,
            "confidence": 0.85, "remarks": "MOCK SAMPLE",
        },
        {
            "item_no": 6, "category": "FLANGE",
            "description": "WN Flange 6\" Class 150 RF",
            "size_nps": '6"', "schedule_rating": "Class 150",
            "material_spec": "ASTM A105", "end_type": "FLGD",
            "quantity": 6, "unit": "EA", "length_m": None,
            "confidence": 0.9, "remarks": "MOCK SAMPLE — 3 flanged joints",
        },
        {
            "item_no": 7, "category": "FLANGE",
            "description": "Blind Flange 6\" Class 150 RF",
            "size_nps": '6"', "schedule_rating": "Class 150",
            "material_spec": "ASTM A105", "end_type": "FLGD",
            "quantity": 2, "unit": "EA", "length_m": None,
            "confidence": 0.85, "remarks": "MOCK SAMPLE — line ends",
        },
        {
            "item_no": 8, "category": "VALVE",
            "description": "Gate Valve 6\" Class 150 Flanged",
            "size_nps": '6"', "schedule_rating": "Class 150",
            "material_spec": "ASTM A216 WCB", "end_type": "FLGD",
            "quantity": 2, "unit": "EA", "length_m": None,
            "confidence": 0.9, "remarks": "MOCK SAMPLE — FW at tie-in",
        },
        {
            "item_no": 9, "category": "VALVE",
            "description": "Swing Check Valve 6\" Class 150 Flanged",
            "size_nps": '6"', "schedule_rating": "Class 150",
            "material_spec": "ASTM A216 WCB", "end_type": "FLGD",
            "quantity": 1, "unit": "EA", "length_m": None,
            "confidence": 0.85, "remarks": "MOCK SAMPLE",
        },
        {
            "item_no": 10, "category": "SUPPORT",
            "description": "Pipe Shoe, 6\" type B",
            "size_nps": '6"', "schedule_rating": None,
            "material_spec": "Carbon Steel", "end_type": None,
            "quantity": 4, "unit": "EA", "length_m": None,
            "confidence": 0.7, "remarks": "MOCK SAMPLE",
        },
    ],
    "summary": {
        "total_pipe_length_m": 18.5,
        "fittings": 8, "flanges": 8, "valves": 3,
        "gaskets": 0, "bolt_sets": 0, "field_welds": 0,
    },
}


class MockPipeline:
    """Returns a fixed sample MTO. Used when no API key is configured."""

    @property
    def name(self) -> str:
        return "mock"

    def extract(self, image_path: Path, *, filename: str) -> MTO:
        # We deliberately ignore the image — the mock always returns the same
        # sample. parse_and_validate re-derives gaskets/bolts and the summary,
        # so the mock exercises the same validation path as the real pipeline.
        return parse_and_validate(_MOCK_RAW, source="mock")
