from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from llm_extract import (  # noqa: E402
    _blank_if_unknown,
    _output_token_budget,
    _resolve_openai_model,
    is_probable_door_mark,
    is_probable_hardware_component,
    llm_config,
)
from page_evidence import PageEvidence, collect  # noqa: E402
from page_extractor import PageType  # noqa: E402
from pipeline import _is_likely_quote_or_proposal_pdf, _merge_direct_pdf_witness, _resolve_hybrid_direct_pdf_mode  # noqa: E402
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


def test_direct_pdf_witness_fills_and_adds_conservatively():
    doors = [
        {
            "project_id": "p1",
            "source_file": "test.pdf",
            "door_number": "101",
            "door_width": "3'-0\"",
            "door_height": None,
            "source_method": "pdfplumber_text",
        }
    ]
    hardware = [
        {
            "project_id": "p1",
            "source_file": "test.pdf",
            "hardware_set_id": "1",
            "description": "Surface closer",
            "source_method": "pdfplumber_text",
        }
    ]
    metrics = _merge_direct_pdf_witness(
        doors,
        hardware,
        0,
        0,
        [
            {"door_number": "101", "door_height": "7'-0\"", "door_material": "HM"},
            {"door_number": "102", "door_width": "3'-0\"", "door_height": "7'-0\""},
            {"door_number": "103"},
        ],
        [
            {"hardware_set_id": "1", "description": "Surface closer", "manufacturer_code": "LCN"},
            {"hardware_set_id": "1", "description": "Hinge", "qty": 3},
        ],
        pdf_name="test.pdf",
        project_id="p1",
    )
    assert metrics["door_confirmed"] == 1
    assert metrics["door_added"] == 1
    assert metrics["hardware_confirmed"] == 1
    assert metrics["hardware_added"] == 1
    assert metrics["door_conflicts"] == 0
    assert metrics["hardware_conflicts"] == 0
    assert doors[0]["door_height"] == "7'-0\""
    assert len([d for d in doors if d["door_number"] == "103"]) == 0
    assert hardware[0]["manufacturer_code"] == "LCN"


def test_direct_pdf_witness_records_conflicts_without_overwriting():
    doors = [{"door_number": "100A", "hardware_set": "1", "source_method": "pdfplumber_text"}]
    metrics = _merge_direct_pdf_witness(
        doors,
        [],
        0,
        0,
        [{"door_number": "100A", "hardware_set": "10", "door_width": "6'-0\"", "door_height": "7'-0\""}],
        [],
        pdf_name="test.pdf",
        project_id="p1",
    )
    assert metrics["door_confirmed"] == 1
    assert metrics["door_conflicts"] == 1
    assert doors[0]["hardware_set"] == "1"
    assert "hardware_set" in doors[0]["hybrid_conflicts"]


def test_openai_model_routing_respects_selected_model_by_default(monkeypatch=None):
    if monkeypatch:
        monkeypatch.delenv("OPENAI_ALLOW_MODEL_ESCALATION", raising=False)
        monkeypatch.delenv("OPENAI_AUTO_ESCALATE_VISION", raising=False)
    else:
        import os
        os.environ.pop("OPENAI_ALLOW_MODEL_ESCALATION", None)
        os.environ.pop("OPENAI_AUTO_ESCALATE_VISION", None)
    previous = llm_config.openai_model
    try:
        llm_config.set("openai", "gpt-4o-mini")
        assert _resolve_openai_model(base64_image="abc", force_model=None) == "gpt-4o-mini"
        assert _resolve_openai_model(base64_image="abc", force_model="gpt-4o") == "gpt-4o-mini"
    finally:
        llm_config.set("openai", previous)


def test_hybrid_direct_pdf_enabled_defaults_to_rescue_mode():
    assert _resolve_hybrid_direct_pdf_mode(True, None) == "rescue"
    assert _resolve_hybrid_direct_pdf_mode(False, None) == "off"
    assert _resolve_hybrid_direct_pdf_mode(None, "always") == "always"


if __name__ == "__main__":
    test_unknown_placeholders_are_not_treated_as_extracted_values()
    test_hardware_qty_preserves_raw_non_integer_quantities()
    test_page_evidence_detects_bracketed_and_prefixed_door_marks()
    test_dynamic_token_budget_never_exceeds_model_context()
    test_hardware_noise_filter_rejects_schedule_references()
    test_door_mark_filter_rejects_room_names()
    test_quote_files_do_not_contribute_door_schedule_rows()
    test_crop_rescue_triggers_on_scanned_mixed_undershoot()
    test_direct_pdf_witness_fills_and_adds_conservatively()
    test_direct_pdf_witness_records_conflicts_without_overwriting()
    test_openai_model_routing_respects_selected_model_by_default()
    test_hybrid_direct_pdf_enabled_defaults_to_rescue_mode()
    print("tests_ok")
