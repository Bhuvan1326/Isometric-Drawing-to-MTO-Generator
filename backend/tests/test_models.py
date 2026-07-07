"""Schema validation tests — the MTO data model is graded on domain
correctness, so we pin its behaviour here."""

import pytest
from pydantic import ValidationError

from app.models.mto import Category, EndType, MTO, MTOItem, Summary


def _valid_item(**overrides) -> dict:
    base = {
        "item_no": 1,
        "category": "PIPE",
        "description": "Seamless Pipe 6\" SCH40",
        "size_nps": '6"',
        "schedule_rating": "SCH40",
        "material_spec": "ASTM A106 Gr.B",
        "end_type": "BW",
        "quantity": 12.5,
        "unit": "M",
        "length_m": 12.5,
        "confidence": 0.9,
        "remarks": None,
    }
    base.update(overrides)
    return base


def test_valid_item_parses() -> None:
    item = MTOItem.model_validate(_valid_item())
    assert item.category == Category.PIPE
    assert item.end_type == EndType.BW
    assert item.unit == "M"


def test_invalid_category_rejected() -> None:
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(category="HOSE"))


def test_invalid_end_type_rejected() -> None:
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(end_type="GLUED"))


def test_negative_quantity_rejected() -> None:
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(quantity=-1))


def test_confidence_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(confidence=1.5))
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(confidence=-0.1))


def test_item_no_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        MTOItem.model_validate(_valid_item(item_no=0))


def test_unit_not_constrained_to_enum() -> None:
    # unit is a free string per spec (M / EA / NO / SET are conventions, not
    # an enum) — but the schema still requires it to be present.
    item = MTOItem.model_validate(_valid_item(unit="LOTS"))
    assert item.unit == "LOTS"


def test_summary_defaults_zero() -> None:
    s = Summary()
    assert s.total_pipe_length_m == 0.0
    assert s.fittings == 0
    assert s.flanges == 0
    assert s.valves == 0
    assert s.gaskets == 0
    assert s.bolt_sets == 0
    assert s.field_welds == 0


def test_mto_round_trip() -> None:
    mto = MTO.model_validate({
        "drawing_meta": {"line_number": '6"-P-1501-A1A-IH', "nps": '6"'},
        "items": [_valid_item()],
        "summary": {"total_pipe_length_m": 12.5, "fittings": 0},
        "source": "mock",
    })
    assert mto.drawing_meta.line_number == '6"-P-1501-A1A-IH'
    assert len(mto.items) == 1
    assert mto.source == "mock"
