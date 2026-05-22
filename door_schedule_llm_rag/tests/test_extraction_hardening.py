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
from agent import (  # noqa: E402
    _parse_door_table_fallback,
    _parse_grid_hardware_sets_fallback,
    _parse_hardware_group_columns_fallback,
    _parse_vendor_hardware_sets_fallback,
)
from page_evidence import PageEvidence, collect  # noqa: E402
from page_extractor import PageType, classify_page, _collect_schedule_signals  # noqa: E402
from pipeline import (  # noqa: E402
    _backfill_orphan_hw_sets_by_door_number,
    _is_likely_quote_or_proposal_pdf,
    _merge_direct_pdf_witness,
    _resolve_hybrid_direct_pdf_mode,
    _should_run_direct_pdf_witness,
)
from verification import (  # noqa: E402
    _crop_has_door_schedule_evidence,
    _crop_has_hardware_schedule_evidence,
    _deterministic_crop_hardware_rows,
    _deterministic_crop_door_rows,
    _filter_crop_door_rows,
    _missing_referenced_hw_sets,
    _normalize_crop_hardware_rows,
)
from schema import HardwareComponentRow  # noqa: E402
from verification import _needs_crop_door_rescue, _needs_crop_hardware_rescue  # noqa: E402
from vision_crops import _needs_tiles, _tile_rects  # noqa: E402


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
    assert not is_probable_hardware_component(
        {"hardware_set_id": "DOOR_HARDWARE", "description": "HOLLOW METAL DOOR / PRIME & PAINT DOOR & FRAME PTXXX", "qty": 1}
    )
    assert not is_probable_hardware_component(
        {"hardware_set_id": "DOOR_HARDWARE", "description": "GLASS PANEL / DOOR & FRAME TO BE PAINTED", "qty": 1}
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


def test_hardware_set_pages_do_not_run_door_crop_rescue():
    evidence = PageEvidence(real_door_numbers=8, dimensions=8, hw_components=6, text_length=1000)
    crops = [{"crop_type": "mixed"}, {"crop_type": "door"}]

    assert not _needs_crop_door_rescue([], evidence, PageType.HARDWARE_SET, crops)


def test_crop_door_rescue_skips_complete_mixed_sheet_with_large_hardware_grid():
    evidence = PageEvidence(real_door_numbers=80, dimensions=80, row_lines=80, hw_components=100, text_length=30000)
    doors = [
        {"door_number": f"10{i}", "door_width": "3'-0\"", "door_height": "7'-0\""}
        for i in range(12)
    ]
    hardware = [{"hardware_set_id": "1", "description": "HINGE"} for _ in range(60)]
    crops = [{"crop_type": "mixed"}, {"crop_type": "door"}]

    assert not _needs_crop_door_rescue(doors, evidence, PageType.MIXED, crops, hardware)


def test_visual_only_single_grid_still_gets_fallback_tiles():
    rects = [("visual_grid", 0.88, (33.0, 708.6, 580.2, 783.0), None)]
    assert _needs_tiles("", PageType.MIXED, rects)
    assert not _needs_tiles("DOOR SCHEDULE", PageType.MIXED, rects + [("tile_top_right", 0.36, (1, 2, 3, 4), None)])


def test_visual_only_multiple_tight_grids_still_get_broad_tiles():
    rects = [
        ("visual_grid", 0.88, (277.0, 353.0, 490.0, 411.0), None),
        ("visual_grid", 0.88, (318.0, 245.0, 454.0, 288.0), None),
        ("visual_grid", 0.88, (277.0, 178.0, 490.0, 221.0), None),
    ]

    assert _needs_tiles("", PageType.MIXED, rects)
    assert _needs_tiles("Title block only\nSHEET TITLE: DOOR SCHEDULE", PageType.MIXED, rects)


def test_visual_only_tiles_include_rotated_schedule_bands():
    class PageRect:
        width = 612.0
        height = 792.0

    tiles = _tile_rects(PageRect(), visual_only=True)
    by_source = {tile[0]: tile for tile in tiles}

    assert by_source["tile_visual_schedule_stack"][3] == "mixed"
    assert by_source["tile_visual_bottom_hardware_band"][3] == "hardware"
    assert by_source["tile_rotated_door_schedule_ccw"][3] == "door"
    assert by_source["tile_rotated_door_schedule_ccw"][4] == 90
    assert by_source["tile_rotated_door_schedule_cw"][4] == 270
    assert by_source["tile_rotated_hardware_schedule_ccw"][3] == "hardware"
    assert by_source["tile_top_left"][4] == 0


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


def test_opening_list_fallback_extracts_door_to_hardware_mapping():
    text = """
[Source: pdfplumber_rows]
Section 08711 | DOOR HARDWARE SCHEDULE
Opening List
Opening | Hdw Set | Opening Label | Door Type | Frame Type
D101A | 109 |  | H | H
D101B | 103 |  | I | I
D102A | 101 |  | A | A
D102B | 101 |  | A | A
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert set(by_mark) == {"D101A", "D101B", "D102A", "D102B"}
    assert by_mark["D101A"]["hardware_set"] == "109"
    assert by_mark["D101B"]["door_type"] == "I"


def test_alphanumeric_door_mark_is_not_used_as_its_own_hardware_set():
    text = """
[Source: pdfplumber_rows]
NO | TYPE | SIZE | FRAME | HDWR
D101 | A | 3'-0" x 7'-0" | HM | D101
D102 | A | 3'-0" x 7'-0" | HM | 5
D103 | A | 3'-0" x 7'-0" | HM | 5
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert "hardware_set" not in by_mark["D101"]
    assert by_mark["D102"]["hardware_set"] == "5"


def test_packed_dimension_schedule_rows_extract_without_llm():
    text = """
[Source: pdfplumber_rows]
DOOR SCHEDULE
TAG ROOM | STATUS | DOOR DESCRIPTION | WIDTH HEIGHT THICKNESS DOOR TYPE | FRAME TYPE | MATERIAL | STILE | HARDWARE SET STATUS | REMARKS
1 | MAIN ENTRY NEW | NEW DOUBLE STOREFRONT | 6' - 0" 7' - 0" 0' - 1 3/4" A | SEE A301 | STOREFRONT | ALUM | WIDE (5") 1 | NEW | 1,2,4
2 | DINING | NEW SINGLE STOREFRONT | 3' - 0" 7' - 0" 0' - 1 3/4" A | SEE A301 | STOREFRONT | ALUM | WIDE (5") 2A | NEW
4 | OFFICE | NEW MANAGER'S OFFICE | 3' - 0" 7' - 0" 0' - 1 3/4" C | D1 (SEE A120) 1 | H.M. | - | 4 | NEW
"""
    rows = _parse_door_table_fallback(text)
    by_mark = {row["door_number"]: row for row in rows}

    assert set(by_mark) == {"1", "2", "4"}
    assert by_mark["1"]["room_name"] == "MAIN ENTRY"
    assert by_mark["1"]["door_width"] == "6' - 0\""
    assert by_mark["1"]["door_height"] == "7' - 0\""
    assert by_mark["1"]["hardware_set"] == "1"
    assert by_mark["2"]["hardware_set"] == "2A"
    assert by_mark["4"]["hardware_set"] == "4"


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

    option_text = """
Section 08711 | DOOR HARDWARE SCHEDULE
Option List
Code
Description
CD
Cylinder Dogging
JD
Less FSIC Cylinder
Tapcon Screws
Tapcon Screws (#TC316175) 1 3/4"
"""
    assert classify_page(option_text) == PageType.OTHER


def test_hardware_specification_prose_routes_to_other():
    text = """
Section 08710 DOOR HARDWARE
PART 1 GENERAL
1.1 SUBMITTALS
Submit product data, shop drawings, templates, warranty, and final keying schedule.
PART 2 PRODUCTS
Door closers shall be adjusted to comply with accessibility requirements.
PART 3 EXECUTION
Install hardware according to manufacturer's written instructions.
Cleaning and protection shall be provided before substantial completion.
"""
    assert classify_page(text) == PageType.OTHER


def test_hardware_set_description_title_routes_to_hardware_set():
    text = """
Sheet Content:
HARDWARE SET
DESCRIPTIONS
Project Number: 002.01
Copyright 2025 Architect
"""
    assert classify_page(text) == PageType.HARDWARE_SET


def test_clear_hardware_set_page_routes_without_door_extraction():
    text = """
Section 08711 | DOOR HARDWARE SCHEDULE
Hardware Sets
Set #100 - EXIT HOLD OPEN CLOSER
8 Hinge | BB1279 4 1/2 x 4 1/2 NRP | US10B | HA
2 Exit Device | CD 25-V-NL-OP | 313AN | FL
2 Closer | 8501H | 690 | NO
Set #101 - LOCK ONLY
3 Hinge | BB1279 4 1/2 X 4 1/2 | US10B | HA
1 Lockset | ALX53T SPA | 613 | SC
"""
    assert classify_page(text) == PageType.HARDWARE_SET


def test_hardware_set_page_does_not_run_door_rescue_on_title_numbers():
    import agent as agent_module

    text = """
Sheet Content:
HARDWARE SET
DESCRIPTIONS
Project Number: 002.01
"""
    old_doors = agent_module.extract_doors_llm
    old_hardware = agent_module.extract_hardware_llm

    def fail(*_args, **_kwargs):
        raise AssertionError("LLM should not be called")

    try:
        agent_module.extract_doors_llm = fail
        agent_module.extract_hardware_llm = fail
        doors, hardware = agent_module.extract_page_with_llm(
            text,
            PageType.HARDWARE_SET,
            use_rag=False,
            retry_with_hint=False,
            crop_candidates=[{"crop_type": "hardware"}],
        )
    finally:
        agent_module.extract_doors_llm = old_doors
        agent_module.extract_hardware_llm = old_hardware

    assert doors == []
    assert hardware == []


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
        {"door_number": "C", "room_name": "SINGLE GLAZED", "door_width": "3'-0\""},
        {"door_number": "L", "room_name": "SINGLE FLUSH SWING", "door_width": "3'-0\""},
        {"door_number": "202", "room_name": "CONFERENCE ROOM", "door_width": "3'-0\""},
        {"door_number": "100", "room_name": "WELLNESS ROOM", "door_width": "3'-0\"", "hardware_set": "AL-2C"},
    ]

    filtered = _filter_crop_door_rows(rows, crop, page_text)

    assert [row["door_number"] for row in filtered] == ["100"]
    assert filtered[0]["hardware_set"] is None


def test_trusted_rotated_door_crop_keeps_rows_when_ocr_misses_mark():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "door",
        "source": "tile_rotated_door_schedule_ccw",
        "text": "",
        "_ocr_text_220": "\n".join(
            [
                "y=10 x=100 conf=0.98 text=DOOR SCHEDULE",
                "y=20 x=10 conf=0.98 text=NO",
                "y=20 x=80 conf=0.98 text=WIDTH",
                "y=20 x=120 conf=0.98 text=HEIGHT",
                "y=20 x=200 conf=0.98 text=HARDWARE",
                "y=40 x=80 conf=0.98 text=UCC",
            ]
        ),
    }
    rows = [
        {"door_number": "100", "room_name": "UCC", "door_width": "3'-0\"", "door_height": "7'-0\""},
        {"door_number": "A2", "room_name": "UCC", "door_width": "3'-0\""},
    ]

    filtered = _filter_crop_door_rows(rows, crop, page_text)

    assert [row["door_number"] for row in filtered] == ["100"]


def test_crop_only_rotated_ocr_columns_recover_multiple_door_rows():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "mixed",
        "text": "",
        "_ocr_text_220": "\n".join(
            [
                "y=104 x=108 conf=0.98 text=DOOR SCHEDULE",
                "y=128 x=26 conf=0.99 text=117",
                "y=129 x=47 conf=1.00 text=100",
                "y=129 x=59 conf=0.99 text=NO.",
                "y=174 x=26 conf=0.97 text=WELLNESS ROOM",
                "y=174 x=47 conf=0.99 text=24HR VESTIBULE",
                "y=296 x=58 conf=0.98 text=TYPE",
                "y=298 x=46 conf=0.95 text=EX",
                "y=299 x=25 conf=1.00 text=A2",
                "y=328 x=58 conf=0.99 text=WIDTH",
                "y=335 x=48 conf=0.87 text=2.9",
                "y=338 x=26 conf=0.85 text=3'-0",
                "y=381 x=58 conf=0.98 text=HEIGHT",
                "y=390 x=48 conf=0.91 text=7-8",
                "y=391 x=26 conf=0.87 text=7'-0",
                "y=800 x=68 conf=1.00 text=HARDWARE",
                "y=814 x=59 conf=1.00 text=SET",
                "y=819 x=27 conf=0.99 text=16",
            ]
        ),
    }

    rows = _deterministic_crop_door_rows(crop, page_text)
    by_mark = {row["door_number"]: row for row in rows}

    assert set(by_mark) == {"117", "100"}
    assert by_mark["117"]["room_name"] == "WELLNESS ROOM"
    assert by_mark["100"]["room_name"] == "24HR VESTIBULE"
    assert by_mark["117"]["door_width"] == "3'-0\""
    assert by_mark["100"]["door_height"] == "7'-8\""


def test_crop_only_horizontal_ocr_schedule_recovers_door_rows():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "mixed",
        "_ocr_text_220": "\n".join(
            [
                "y=180 x=82 conf=0.99 text=DOOR SCHEDULE",
                "y=220 x=60 conf=0.99 text=NUMBER",
                "y=220 x=215 conf=0.99 text=ROOM",
                "y=220 x=980 conf=0.99 text=SIZE",
                "y=220 x=1320 conf=0.99 text=TYPE",
                "y=220 x=1510 conf=0.99 text=HARDWARE",
                "y=220 x=1705 conf=0.99 text=RATING",
                "y=220 x=1930 conf=0.99 text=REMARKS",
                "y=260 x=62 conf=0.98 text=R1OO",
                "y=260 x=215 conf=0.98 text=RESIDENT",
                "y=260 x=410 conf=0.98 text=UNIT",
                "y=260 x=540 conf=0.98 text=ENTRY",
                "y=260 x=980 conf=0.98 text=4'-O\"X",
                "y=260 x=1120 conf=0.98 text=7'-O\"",
                "y=260 x=1325 conf=0.98 text=A",
                "y=260 x=1520 conf=0.98 text=1",
                "y=290 x=62 conf=0.98 text=RIO!",
                "y=290 x=215 conf=0.98 text=RESIDENT",
                "y=290 x=410 conf=0.98 text=UNIT",
                "y=290 x=540 conf=0.98 text=BATHROOM",
                "y=290 x=980 conf=0.98 text=3'-O\"X",
                "y=290 x=1120 conf=0.98 text=7'-O\"",
                "y=290 x=1325 conf=0.98 text=B",
                "y=290 x=1520 conf=0.98 text=2",
                "y=320 x=72 conf=0.98 text=01",
                "y=320 x=215 conf=0.98 text=LOBBY",
                "y=320 x=980 conf=0.98 text=4'-O\"X",
                "y=320 x=1120 conf=0.98 text=7'-O\"",
                "y=320 x=1325 conf=0.98 text=A",
                "y=320 x=1520 conf=0.98 text=1",
                "y=350 x=72 conf=0.98 text=02",
                "y=350 x=215 conf=0.98 text=MARKETING",
                "y=350 x=980 conf=0.98 text=3'-O\"X",
                "y=350 x=1120 conf=0.98 text=7'-O\"",
                "y=350 x=1325 conf=0.98 text=A",
                "y=350 x=1520 conf=0.98 text=10",
                "y=380 x=72 conf=0.98 text=03",
                "y=380 x=215 conf=0.98 text=OFFICE",
                "y=380 x=980 conf=0.98 text=3'-O\"X",
                "y=380 x=1120 conf=0.98 text=7'-O\"",
                "y=380 x=1325 conf=0.98 text=A",
                "y=380 x=1520 conf=0.98 text=10",
            ]
        ),
    }

    rows = _filter_crop_door_rows(_deterministic_crop_door_rows(crop, page_text), crop, page_text)
    by_mark = {row["door_number"]: row for row in rows}

    assert {"R100", "R101", "01", "02", "03"}.issubset(by_mark)
    assert by_mark["R100"]["room_name"] == "RESIDENT UNIT ENTRY"
    assert by_mark["R101"]["room_name"] == "RESIDENT UNIT BATHROOM"
    assert by_mark["R100"]["door_width"] == "4'-0\""
    assert by_mark["R101"]["door_height"] == "7'-0\""
    assert by_mark["02"]["hardware_set"] == "10"


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


def test_rotated_hardware_crop_requires_readable_column_headers():
    page_text = "VISION_CROP_RESCUE: weak native text"
    wrong_way_crop = {
        "crop_type": "hardware",
        "source": "tile_rotated_hardware_schedule_cw",
        "_ocr_text_220": "y=10 x=10 conf=0.95 text=HARDWARE GROUP NO.16\ny=20 x=20 conf=0.95 text=SILENCER",
    }
    readable_crop = {
        "crop_type": "hardware",
        "source": "tile_rotated_hardware_schedule_ccw",
        "_ocr_text_220": (
            "y=10 x=10 conf=0.95 text=DOOR HARDWARE SCHEDULE\n"
            "y=20 x=10 conf=0.95 text=QUANTITY\n"
            "y=20 x=80 conf=0.95 text=DESCRIPTION\n"
            "y=20 x=160 conf=0.95 text=MODEL NUMBER\n"
            "y=20 x=250 conf=0.95 text=FINISH\n"
            "y=20 x=300 conf=0.95 text=MFR\n"
            "y=40 x=10 conf=0.95 text=HARDWARE GROUP NO. 4\n"
            "y=55 x=60 conf=0.95 text=3\n"
            "y=55 x=125 conf=0.95 text=HINGE"
        ),
    }

    assert not _crop_has_hardware_schedule_evidence(wrong_way_crop, page_text)
    assert _crop_has_hardware_schedule_evidence(readable_crop, page_text)


def test_deterministic_rotated_hardware_ocr_table_parser():
    page_text = "VISION_CROP_RESCUE: weak native text"
    crop = {
        "crop_type": "hardware",
        "source": "tile_rotated_hardware_schedule_ccw",
        "_ocr_text_220": "\n".join(
            [
                "y=10 x=120 conf=0.99 text=DOOR HARDWARE SCHEDULE",
                "y=20 x=50 conf=0.99 text=QUANTITY",
                "y=20 x=130 conf=0.99 text=DESCRIPTION",
                "y=20 x=250 conf=0.99 text=MODEL NUMBER",
                "y=20 x=430 conf=0.99 text=FINISH",
                "y=20 x=470 conf=0.99 text=MFR",
                "y=40 x=60 conf=0.99 text=HARDWARE GROUP NO. 04 ALT",
                "y=55 x=80 conf=0.99 text=4",
                "y=55 x=126 conf=0.99 text=HINGE",
                "y=55 x=240 conf=0.99 text=BB1279",
                "y=55 x=435 conf=0.99 text=26D",
                "y=55 x=470 conf=0.99 text=HAG",
                "y=70 x=80 conf=0.99 text=1",
                "y=70 x=126 conf=0.99 text=SURFACE CLOSER",
                "y=70 x=240 conf=0.99 text=4111",
                "y=70 x=435 conf=0.99 text=689",
                "y=70 x=470 conf=0.99 text=LCN",
                "y=90 x=60 conf=0.99 text=HARDWARE GROUP NO. 10",
                "y=105 x=80 conf=0.99 text=3",
                "y=105 x=126 conf=0.99 text=SILENCER",
                "y=105 x=240 conf=0.99 text=SR64",
                "y=105 x=435 conf=0.99 text=GRY",
                "y=105 x=470 conf=0.99 text=IVE",
                "y=120 x=80 conf=0.99 text=1",
                "y=120 x=126 conf=0.99 text=WALL STOP",
                "y=120 x=240 conf=0.99 text=WS407CCV",
                "y=120 x=435 conf=0.99 text=630",
                "y=120 x=470 conf=0.99 text=IVE",
            ]
        ),
    }

    rows = _deterministic_crop_hardware_rows(crop, page_text)
    by_key = {(row["hardware_set_id"], row["description"]): row for row in rows}

    assert by_key[("4", "HINGE")]["qty"] == 4
    assert by_key[("4", "SURFACE CLOSER")]["manufacturer_code"] == "LCN"
    assert by_key[("10", "SILENCER")]["catalog_number"] == "SR64"
    assert len(rows) == 4


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


def test_vendor_hardware_set_fallback_parses_pipe_layout_without_llm():
    text = """
Section 08711 | DOOR HARDWARE SCHEDULE | Hardware Sets |
Set #103 - EXIT - HOLD OPEN CLOSER |
4 Hinge | BB1279 4 1/2 x 4 1/2 NRP | US10B HA |
1 Exit Device | 25-R-L x 510L QUANTUM | SP313, 313AN FL |
1 Closer | 8501H | 690 | NO |
Set #104 - BARN DOOR HARDWARE |
4 Flush Pull | 106 | US10B | HA |
"""
    rows = _parse_vendor_hardware_sets_fallback(text)
    by_key = {(row["hardware_set_id"], row["description"]): row for row in rows}

    assert len(rows) == 4
    assert by_key[("103", "Hinge")]["qty"] == 4
    assert by_key[("103", "Hinge")]["catalog_number"].startswith("BB1279")
    assert by_key[("103", "Hinge")]["finish_code"] == "US10B"
    assert by_key[("103", "Hinge")]["manufacturer_code"] == "HA"
    assert by_key[("103", "Exit Device")]["manufacturer_code"] == "FL"
    assert by_key[("103", "Exit Device")]["finish_code"] == "SP313, 313AN"
    assert by_key[("103", "Closer")]["catalog_number"] == "8501H"
    assert by_key[("103", "Closer")]["finish_code"] == "690"
    assert by_key[("104", "Flush Pull")]["catalog_number"] == "106"
    assert by_key[("104", "Flush Pull")]["hardware_set_name"] == "BARN DOOR HARDWARE"

    small_text = """
DOOR HARDWARE SCHEDULE
Hardware Sets
Set #1 - SINGLE OFFICE
1 SET Weatherstrip | 700S | 628 | NGP
"""
    small_rows = _parse_vendor_hardware_sets_fallback(small_text)
    assert len(small_rows) == 1
    assert small_rows[0]["unit"] == "SET"
    assert small_rows[0]["catalog_number"] == "700S"


def test_grid_hardware_set_fallback_parses_multicolumn_set_schedule():
    text = """
HARDWARE SCHEDULE
SET: 1.0 | SET: 4.0
2 EA. CONTINUOUS HINGE | 1 EA. MORTISE DEADLOCK
1 EA. CONCEALED VERT ROD EXIT, NIGHTLATCH | 1 EA. CORE
2 EA. SURFACE CLOSER | 1 EA. DOOR STOP
104 | 3'-0" | 8'-0" | 1 3/4" | A | SOLID CORE | PTD | WOOD | 8
"""
    rows = _parse_grid_hardware_sets_fallback(text)
    by_set = {}
    for row in rows:
        by_set.setdefault(row["hardware_set_id"], []).append(row["description"])

    assert by_set["1"] == [
        "CONTINUOUS HINGE",
        "CONCEALED VERT ROD EXIT, NIGHTLATCH",
        "SURFACE CLOSER",
    ]
    assert by_set["4"] == ["MORTISE DEADLOCK", "CORE", "DOOR STOP"]
    assert all(row["description"] != "3'-0\" 8'-0\" 1 3/4\" A SOLID CORE PTD WOOD 8" for row in rows)


def test_hardware_group_no_columns_parse_without_llm():
    text = """
[Source: pdfplumber_rows]
Hardware Group No. 01.A | Hardware Group No. 07 | Hardware Group No. 13 | ISSUE LOG
Provide each SGL door(s) with the following: | Provide each SGL door(s) with the following: | Provide each SGL door(s) with the following: | DOOR SCHEDULE
QTY DESCRIPTION | CATALOG NUMBER | FINISH MFR. | QTY DESCRIPTION | CATALOG NUMBER | FINISH MFR. | QTY DESCRIPTION | CATALOG NUMBER | FINISH MFR. | Mark | Room Name
1 EA CONT. HINGE | 112XY HEIGHT AS REQ | 628 IVE | 3 EA HINGE | 5BB1 4.5 X 4.5 | 652 IVE | 3 EA HINGE | 5BB1 4.5 X 4.5 | 652 IVE | 001 | LOBBY
1 EA PANIC HARDWARE | CD-99-NL | 626 VON | 1 EA CLASSROOM LOCK | L9070L 06A | 626 SCH | 1 EA OFFICE/ENTRY LOCK | L9050L 06A L583-363 | 626 SCH | 002 | APPARATUS BAY
1 EA MORTISE CYLINDER | MATCH EXISTING "CYBER KEY" | CYB | 1 EA WALL STOP | WS406/407CCV | 630 IVE | 1 EA SURFACE CLOSER | SC71 RW/PA X MTG. PLT. | 689 FAL
"""
    rows = _parse_hardware_group_columns_fallback(text)
    by_key = {(row["hardware_set_id"], row["description"]): row for row in rows}

    assert len(rows) == 9
    assert by_key[("01.A", "CONT. HINGE")]["catalog_number"] == "112XY HEIGHT AS REQ"
    assert by_key[("07", "CLASSROOM LOCK")]["manufacturer_code"] == "SCH"
    assert by_key[("13", "SURFACE CLOSER")]["finish_code"] == "689"


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


def test_direct_pdf_witness_skips_complete_opening_list_with_hardware():
    doors = [
        {"door_number": "D101A", "hardware_set": "109", "_table_shape": "opening_list"},
        {"door_number": "D101B", "hardware_set": "103", "_table_shape": "opening_list"},
        {"door_number": "D102A", "hardware_set": "101", "_table_shape": "opening_list"},
    ]
    hardware = [{"hardware_set_id": "109", "description": "Hinge"} for _ in range(3)]

    assert not _should_run_direct_pdf_witness("rescue", doors, hardware)


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
    test_crop_door_rescue_skips_complete_mixed_sheet_with_large_hardware_grid()
    test_visual_only_single_grid_still_gets_fallback_tiles()
    test_opening_list_routes_as_door_schedule_without_ocr_signal()
    test_opening_list_fallback_extracts_door_to_hardware_mapping()
    test_alphanumeric_door_mark_is_not_used_as_its_own_hardware_set()
    test_packed_dimension_schedule_rows_extract_without_llm()
    test_reference_code_lists_route_to_other_not_hardware()
    test_hardware_specification_prose_routes_to_other()
    test_hardware_set_description_title_routes_to_hardware_set()
    test_clear_hardware_set_page_routes_without_door_extraction()
    test_hardware_set_page_does_not_run_door_rescue_on_title_numbers()
    test_crop_only_door_rescue_requires_local_door_schedule_evidence()
    test_crop_only_filters_profile_labels_and_generic_invented_door_rows()
    test_crop_only_rotated_ocr_columns_recover_multiple_door_rows()
    test_crop_only_horizontal_ocr_schedule_recovers_door_rows()
    test_crop_only_hardware_rescue_normalizes_item_numbers_without_set_header()
    test_crop_only_hardware_rescue_keeps_explicit_set_headers()
    test_direct_pdf_witness_fills_and_adds_conservatively()
    test_direct_pdf_witness_records_conflicts_without_overwriting()
    test_formal_door_table_fallback_uses_hardware_column()
    test_vendor_hardware_set_fallback_parses_pipe_layout_without_llm()
    test_grid_hardware_set_fallback_parses_multicolumn_set_schedule()
    test_missing_referenced_hw_sets_normalizes_ids()
    test_openai_model_routing_respects_selected_model_by_default()
    test_hybrid_direct_pdf_enabled_defaults_to_rescue_mode()
    test_direct_pdf_witness_skips_complete_opening_list_with_hardware()
    test_cross_reference_backfills_matching_door_number_hardware_sets()
    print("tests_ok")
