from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from llm_extract import (  # noqa: E402
    _blank_if_unknown,
    _output_token_budget,
    is_probable_door_mark,
    is_probable_hardware_component,
)
from page_evidence import PageEvidence, collect  # noqa: E402
from page_extractor import PageType  # noqa: E402
from pipeline import _is_likely_quote_or_proposal_pdf  # noqa: E402
from schema import HardwareComponentRow  # noqa: E402
from verification import _needs_crop_door_rescue, _needs_crop_hardware_rescue  # noqa: E402


def test_unknown_placeholders_are_not_treated_as_extracted_values():
    assert _blank_if_unknown("N/A") is None
    assert _blank_if_unknown("not shown") is None
    assert _blank_if_unknown("HM") == "HM"


def test_hardware_qty_preserves_raw_non_integer_quantities():
    row = HardwareComponentRow(
        hardware_set_id="Set 1",
        qty="LOT",
        qty_raw="LOT",
        unit="SET",
        description="Weatherstrip package",
    )
    assert row.hardware_set_id == "1"
    assert row.qty is None
    assert row.qty_raw == "LOT"
    assert row.unit == "SET"


def test_page_evidence_detects_bracketed_and_prefixed_door_marks():
    evidence = collect(
        """
        DOOR SCHEDULE
        D101A OFFICE 3'-0" 7'-0" HM HARDWARE SET 1
        [107] BREAK RM 3'-0" 7'-0" SC KD 20 GA
        """
    )
    assert evidence.real_door_numbers >= 2
    assert evidence.dimensions >= 4
    assert evidence.is_door_schedule


def test_dynamic_token_budget_never_exceeds_model_context():
    budget = _output_token_budget("qwen2.5:7b", "system", "x" * 20000)
    assert 512 <= budget <= 6144


def test_hardware_noise_filter_rejects_schedule_references():
    assert not is_probable_hardware_component(
        {"hardware_set_id": "1", "description": "SEE HARDWARE SCHED", "unit": "EA"}
    )
    assert is_probable_hardware_component(
        {"hardware_set_id": "1", "description": "Surface closer", "qty": 1}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "E7", "description": "12-inch grab bar", "qty": 1, "catalog_number": "102091900019"}
    )


def test_door_mark_filter_rejects_room_names():
    assert is_probable_door_mark("101A")
    assert is_probable_door_mark("D1")
    assert is_probable_door_mark("1")
    assert not is_probable_door_mark("RESTROOM")
    assert not is_probable_door_mark("KITCHEN")


def test_quote_files_do_not_contribute_door_schedule_rows():
    assert _is_likely_quote_or_proposal_pdf("P26_01275_63912302096.pdf")
    assert _is_likely_quote_or_proposal_pdf("proposal.pdf")
    assert not _is_likely_quote_or_proposal_pdf("Door Schedule.pdf")


def test_crop_rescue_triggers_on_scanned_mixed_undershoot():
    evidence = PageEvidence(real_door_numbers=8, hw_components=6, text_length=1000)
    crops = [{"crop_type": "mixed"}, {"crop_type": "mixed"}]
    assert _needs_crop_door_rescue(
        [{"door_number": "101", "door_width": "3'-0\"", "door_height": "7'-0\""}],
        evidence,
        PageType.MIXED,
        crops,
    )
    assert _needs_crop_hardware_rescue([], evidence, PageType.MIXED, crops)


if __name__ == "__main__":
    test_unknown_placeholders_are_not_treated_as_extracted_values()
    test_hardware_qty_preserves_raw_non_integer_quantities()
    test_page_evidence_detects_bracketed_and_prefixed_door_marks()
    test_dynamic_token_budget_never_exceeds_model_context()
    test_hardware_noise_filter_rejects_schedule_references()
    test_door_mark_filter_rejects_room_names()
    test_quote_files_do_not_contribute_door_schedule_rows()
    test_crop_rescue_triggers_on_scanned_mixed_undershoot()
    print("tests_ok")
