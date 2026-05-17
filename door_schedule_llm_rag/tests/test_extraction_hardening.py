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
from agent import _parse_door_table_fallback  # noqa: E402
from page_evidence import PageEvidence, collect  # noqa: E402
from page_extractor import PageType, classify_page, _collect_schedule_signals  # noqa: E402
from pipeline import (  # noqa: E402
    _backfill_orphan_hw_sets_by_door_number,
    _is_likely_quote_or_proposal_pdf,
    _merge_direct_pdf_witness,
    _resolve_hybrid_direct_pdf_mode,
)
from verification import (  # noqa: E402
    _crop_has_door_schedule_evidence,
    _crop_has_hardware_schedule_evidence,
    _filter_crop_door_rows,
    _missing_referenced_hw_sets,
    _normalize_crop_hardware_rows,
)
from schema import HardwareComponentRow  # noqa: E402
from verification import _needs_crop_door_rescue, _needs_crop_hardware_rescue  # noqa: E402
from vision_crops import _needs_tiles  # noqa: E402


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

    row_decimal = HardwareComponentRow(
        hardware_set_id="1.0",
        qty=1,
        unit="EA",
        description="Hinge",
    )
    assert row_decimal.hardware_set_id == "1"


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
    assert not is_probable_hardware_component(
        {"hardware_set_id": "1", "hardware_set_name": "CARD READER ACCESS", "description": "CARD READER ACCESS", "qty_raw": "C714", "catalog_number": "C714"}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "C715", "hardware_set_name": "CARD READER ACCESS", "description": "C205", "qty_raw": "1"}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "1", "hardware_set_name": "ROOM FINISH SCHEDULE", "description": "CT/PNT", "qty_raw": "1 EA."}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "25", "hardware_set_name": "RESIDENT UNIT - BATHROOM", "description": "SIDELIGHTS", "qty_raw": "(2)"}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "115", "hardware_set_name": "DOOR HARDWARE", "description": "HARDWARE SET 115", "qty_raw": "1"}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "1", "hardware_set_name": "DOOR CLOSER", "description": "CLOSER", "qty": 1, "catalog_number": "8413", "manufacturer_code": "ABC Corp"}
    )
    assert is_probable_hardware_component(
        {"hardware_set_id": "1", "description": "Electric strike", "qty": 1}
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


def test_visual_only_single_grid_still_gets_fallback_tiles():
    rects = [("visual_grid", 0.88, (33.0, 708.6, 580.2, 783.0), None)]
    assert _needs_tiles("", PageType.MIXED, rects)
    assert not _needs_tiles("DOOR SCHEDULE", PageType.MIXED, rects + [("tile_top_right", 0.36, (1, 2, 3, 4), None)])


def test_opening_list_routes_as_door_schedule_without_ocr_signal():
    text = """
Section 08711 | DOOR HARDWARE SCHEDULE
Opening List
Opening
Hdw Set
Opening Label
Door Type
Frame Type
D101A
109
H
H
D101B
103
I
I
D102A
101
A
A
D102B
101
A
A
"""
    signals = _collect_schedule_signals(text)
    assert signals["real_doors"] >= 4
    assert classify_page(text) == PageType.DOOR_SCHEDULE


def test_reference_code_lists_route_to_other_not_hardware():
    text = """
Section 08711 | DOOR HARDWARE SCHEDULE
Manufacturer List
Code
Name
CKN
K.N. Crowder
FL
Falcon Lock
HA
Hager
"""
    assert classify_page(text) == PageType.OTHER


def test_crop_only_door_rescue_requires_local_door_schedule_evidence():
    page_text = "VISION_CROP_RESCUE: weak native text"
    hardware_legend_crop = {
        "crop_type": "mixed",
        "text": "SECURITY AT EXTERIOR ENTRY DOORS\nDOOR HARDWARE\nHINGE\nCLOSER\nEXIT DEVICE",
    }
    door_schedule_crop = {
        "crop_type": "mixed",
        "text": "DOOR SCHEDULE\nNO. ROOM WIDTH HEIGHT TYPE\n100 WELLNESS ROOM 3'-0\" 7'-0\" A2",
    }

    assert not _crop_has_door_schedule_evidence(hardware_legend_crop, page_text)
    assert _crop_has_door_schedule_evidence(door_schedule_crop, page_text)


def test_crop_only_filters_profile_labels_and_generic_invented_door_rows():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "mixed",
        "text": "DOOR SCHEDULE\nNO. ROOM WIDTH HEIGHT TYPE\n100 WELLNESS ROOM 3'-0\" 7'-0\" A2",
    }
    rows = [
        {"door_number": "A2", "room_name": "WELLNESS ROOM", "door_width": "3'-0\""},
        {"door_number": "202", "room_name": "CONFERENCE ROOM", "door_width": "3'-0\""},
        {"door_number": "100", "room_name": "WELLNESS ROOM", "door_width": "3'-0\""},
    ]

    filtered = _filter_crop_door_rows(rows, crop, page_text)

    assert [row["door_number"] for row in filtered] == ["100"]


def test_crop_only_hardware_rescue_normalizes_item_numbers_without_set_header():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "mixed",
        "text": "DOOR HARDWARE\nQTY DESCRIPTION\n1 HINGE\n2 CLOSER\n3 EXIT DEVICE",
    }
    rows = [
        {"hardware_set_id": "1", "description": "HINGE"},
        {"hardware_set_id": "2", "description": "CLOSER"},
    ]

    assert _crop_has_hardware_schedule_evidence(crop, page_text)
    normalized = _normalize_crop_hardware_rows(rows, crop, page_text)

    assert {row["hardware_set_id"] for row in normalized} == {"DOOR_HARDWARE"}


def test_crop_only_hardware_rescue_keeps_explicit_set_headers():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "mixed",
        "text": "HARDWARE SET 3\n3 EA HINGE\n1 EA CLOSER",
    }
    rows = [{"hardware_set_id": "3", "description": "HINGE"}]

    normalized = _normalize_crop_hardware_rows(rows, crop, page_text)

    assert normalized[0]["hardware_set_id"] == "3"


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


def test_formal_door_table_fallback_uses_hardware_column():
    text = """
[Source: pdfplumber_rows]
100B | EXTERIOR | LOBBY | 6' - 0" 7' - 0" | 0' - 1 3/4" ALUM | BB | FF | ALUM | 2 | FF | A5.40/02 | A5.40/02 | A5.40/01 | 1 | A.C. CONTROL | No. | Date | Description

[Source: pdfplumber_tables]
=== TABLE (3x22) ===
|  |  | 100A | EXIST. CORRIDOR | LOBBY | 6' - 0" | 7' - 0" | 0' - 1 3/4" | HM | AA | PT | HM | 1 | PT |  |  |  | 90 MIN. | 10 | FIRE RATED DOOR ASSEMBLY |  |  |
|  |  | 100B | EXTERIOR | LOBBY | 6' - 0" | 7' - 0" | 0' - 1 3/4" | ALUM | BB | FF | ALUM | 2 | FF | A5.40/02 | A5.40/02 | A5.40/01 |  | 1 | A.C. CONTROL |  |  |
| DOOR SCHED. NOTES | 24 | 140A | JAN | NEW VESTIBULE | 3' - 0" | 7' - 0" | 0' - 1 3/4" | SC | A | PLAM | HM | 1 | PT | A5.40/09 | A5.40/08 | A5.40/07 |  | 13 |  |  |  |
| 213 | NURSERY 2 | DG | 3'-0" | 8'-0" | 1 3/4" | SCWD | PLAM-03 | GL4 | F4A | ALUM | ANOD | GL4 | 06/A6.70 | 17/A6.70 | - | 103U | CMTA |  |  |  |
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert "24" not in by_mark
    assert by_mark["100A"]["hardware_set"] == "10"
    assert by_mark["100A"]["fire_rating"] == "90 MIN."
    assert by_mark["100B"]["frame_type"] == "2"
    assert by_mark["100B"]["hardware_set"] == "1"
    assert by_mark["140A"]["room_name"] == "NEW VESTIBULE"
    assert by_mark["140A"]["hardware_set"] == "13"
    assert by_mark["213"]["hardware_set"] == "103U"


def test_compact_door_table_fallback_maps_type_size_frame_hardware():
    text = """
[Source: pdfplumber_rows]
CASE GYP BD CASED OPENING. PREP FOR FINISH | 100A | E | 6'-0" x 8'-0" | E | E | T-TURN INSIDE & EXTERIOR CYLINDER GUARD

[Source: pdfplumber_tables]
=== TABLE (5x5) ===
| 101A | A1 | 3'-0" x 8'-0" | HM | HW-4 |
| 102A | A1 | 3'-0" x 8'-0" | HM | HW-3 |
| 103A | A1 | 3'-0" x 8'-0" | HM | HW-2 |
| 103B | E | 3'-0" x 7'-0" | E | E |
| 104A 'E' INDICATES EXISTING TO REMAIN. | A1 | 3'-0" x 8'-0" | HM | HW-2 |
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert by_mark["100A"]["door_type"] == "E"
    assert "hardware_set" not in by_mark["100A"]
    assert by_mark["100A"]["remarks"] == "T-TURN INSIDE & EXTERIOR CYLINDER GUARD"
    assert by_mark["101A"]["door_type"] == "A1"
    assert by_mark["101A"]["hardware_set"] == "4"
    assert by_mark["102A"]["hardware_set"] == "3"
    assert by_mark["103A"]["hardware_set"] == "2"
    assert "hardware_set" not in by_mark["103B"]
    assert by_mark["104A"]["remarks"] == "E' INDICATES EXISTING TO REMAIN."
    assert by_mark["104A"]["hardware_set"] == "2"


def test_truncated_formal_row_does_not_infer_hardware_from_frame_tokens():
    text = """
[Source: pdfplumber_rows]
217 | PRESCHOOL | G2 : INT | 3'-0" | 8'-0" | 1 3/4" | SCWD PLAM-03 | GL5 | F4A | ALUM | ANOD | GL5 | 06/A6.7
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert by_mark["217"]["door_width"] == "3'-0\""
    assert "hardware_set" not in by_mark["217"]


def test_missing_referenced_hw_sets_normalizes_ids():
    doors = [
        {"door_number": "100A", "hardware_set": "5"},
        {"door_number": "100B", "hardware_set": "Group 7.0"},
        {"door_number": "100C", "hardware_set": None},
    ]
    hardware = [{"hardware_set_id": "Set 5.0"}]

    assert _missing_referenced_hw_sets(doors, hardware) == ["7"]


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


def test_cross_reference_backfills_matching_door_number_hardware_sets():
    import pandas as pd

    doors = pd.DataFrame(
        [
            {"project_id": "p1", "door_number": "203", "hardware_set": ""},
            {"project_id": "p1", "door_number": "204", "hardware_set": ""},
            {"project_id": "p1", "door_number": "C710AM", "hardware_set": None},
        ]
    )
    hardware = pd.DataFrame(
        [
            {"project_id": "p1", "hardware_set_id": "203"},
            {"project_id": "p1", "hardware_set_id": "C710AM"},
        ]
    )

    assert _backfill_orphan_hw_sets_by_door_number(doors, hardware, project_id="p1") == 2
    assert doors.loc[doors["door_number"] == "203", "hardware_set"].iloc[0] == "203"
    assert doors.loc[doors["door_number"] == "C710AM", "hardware_set"].iloc[0] == "C710AM"
    assert doors.loc[doors["door_number"] == "204", "hardware_set"].iloc[0] == ""


if __name__ == "__main__":
    test_unknown_placeholders_are_not_treated_as_extracted_values()
    test_hardware_qty_preserves_raw_non_integer_quantities()
    test_page_evidence_detects_bracketed_and_prefixed_door_marks()
    test_dynamic_token_budget_never_exceeds_model_context()
    test_hardware_noise_filter_rejects_schedule_references()
    test_door_mark_filter_rejects_room_names()
    test_quote_files_do_not_contribute_door_schedule_rows()
    test_crop_rescue_triggers_on_scanned_mixed_undershoot()
    test_visual_only_single_grid_still_gets_fallback_tiles()
    test_opening_list_routes_as_door_schedule_without_ocr_signal()
    test_reference_code_lists_route_to_other_not_hardware()
    test_crop_only_door_rescue_requires_local_door_schedule_evidence()
    test_crop_only_filters_profile_labels_and_generic_invented_door_rows()
    test_crop_only_hardware_rescue_normalizes_item_numbers_without_set_header()
    test_crop_only_hardware_rescue_keeps_explicit_set_headers()
    test_direct_pdf_witness_fills_and_adds_conservatively()
    test_direct_pdf_witness_records_conflicts_without_overwriting()
    test_formal_door_table_fallback_uses_hardware_column()
    test_missing_referenced_hw_sets_normalizes_ids()
    test_openai_model_routing_respects_selected_model_by_default()
    test_hybrid_direct_pdf_enabled_defaults_to_rescue_mode()
    test_cross_reference_backfills_matching_door_number_hardware_sets()
    print("tests_ok")
