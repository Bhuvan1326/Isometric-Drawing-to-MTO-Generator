"""Tests for the validation/derivation layer.

The validator re-derives gaskets, bolt sets, and summary totals from the raw
LLLM output. These tests pin that behaviour — it's the deterministic safety
net that catches LLM miscounts.
"""

from app.pipeline.validate import parse_and_validate


def _raw_with_flanges(n_flanges: int) -> dict:
    items = [
        {
            "item_no": 1, "category": "PIPE", "description": "Pipe 6\"",
            "size_nps": '6"', "quantity": 10.0, "unit": "M", "length_m": 10.0,
        }
    ]
    for i in range(n_flanges):
        items.append({
            "item_no": i + 2, "category": "FLANGE", "description": "WN Flange 6\"",
            "size_nps": '6"', "schedule_rating": "Class 150",
            "material_spec": "A105", "end_type": "FLGD",
            "quantity": 1, "unit": "EA",
        })
    return {
        "drawing_meta": {},
        "items": items,
        "summary": {"total_pipe_length_m": 0, "fittings": 0, "flanges": 0,
                    "valves": 0, "gaskets": 0, "bolt_sets": 0, "field_welds": 0},
    }


def test_derives_one_gasket_and_bolt_set_per_flange_pair() -> None:
    # 4 flanges = 2 joints = 2 gaskets + 2 bolt sets
    mto = parse_and_validate(_raw_with_flanges(4), source="test")
    gaskets = [i for i in mto.items if i.category == "GASKET"]
    bolts = [i for i in mto.items if i.category == "BOLT"]
    assert len(gaskets) == 1
    assert len(bolts) == 1
    assert gaskets[0].quantity == 2.0
    assert bolts[0].quantity == 2.0
    assert bolts[0].unit == "SET"
    assert mto.summary.gaskets == 2
    assert mto.summary.bolt_sets == 2


def test_odd_flange_count_rounds_down_joints() -> None:
    # 5 flanges = 2 joints (one flange is unpaired, e.g. a blind or a loose
    # flange waiting for equipment). 2 gaskets + 2 bolt sets.
    mto = parse_and_validate(_raw_with_flanges(5), source="test")
    assert mto.summary.gaskets == 2
    assert mto.summary.bolt_sets == 2
    assert mto.summary.flanges == 5


def test_no_flanges_means_no_derived_items() -> None:
    mto = parse_and_validate(_raw_with_flanges(0), source="test")
    assert not any(i.category == "GASKET" for i in mto.items)
    assert not any(i.category == "BOLT" for i in mto.items)


def test_summary_recomputed_from_items_not_trusted() -> None:
    # The raw summary lies (says 0 pipe) — the validator must recompute.
    raw = _raw_with_flanges(0)
    raw["summary"]["total_pipe_length_m"] = 999.0
    mto = parse_and_validate(raw, source="test")
    assert mto.summary.total_pipe_length_m == 10.0  # from the PIPE item


def test_item_numbers_renumbered_sequentially() -> None:
    mto = parse_and_validate(_raw_with_flanges(4), source="test")
    numbers = [i.item_no for i in mto.items]
    assert numbers == list(range(1, len(numbers) + 1))


def test_field_weld_remarks_counted() -> None:
    raw = _raw_with_flanges(0)
    raw["items"].append({
        "item_no": 99, "category": "VALVE", "description": "Gate Valve",
        "quantity": 1, "unit": "EA", "remarks": "FW at tie-in",
    })
    mto = parse_and_validate(raw, source="test")
    assert mto.summary.field_welds >= 1


def test_invalid_json_raises_pipeline_error() -> None:
    from app.pipeline.base import PipelineError
    import pytest

    bad = {"items": [{"category": "NOPE"}]}  # missing required fields
    with pytest.raises(PipelineError):
        parse_and_validate(bad, source="test")
