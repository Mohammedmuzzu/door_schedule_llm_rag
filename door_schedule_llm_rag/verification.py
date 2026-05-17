"""
verification.py
───────────────
Post-extraction self-verification.

Why
    The single biggest "robustness" lever — and the one the PRD explicitly
    asks for ("Model accuracy 99.5% / robust to PDF format variations") — is
    not another hand-crafted rule. It is a **verification pass** that compares
    what we actually extracted against structural evidence collected from the
    page. Whenever the two disagree by a wide margin, we escalate to a
    Vision LLM re-extraction that uses both the page image and the raw text.

How it works
    1.  Build `PageEvidence` from the page content (cheap, pure).
    2.  Compare number of extracted doors / hardware-sets vs. what evidence
        suggests should be present.
    3.  If the gap is large (or extraction is entirely empty while evidence
        says there should be content), run a Vision-LLM retry with
        `force_model="gpt-4o"` and a targeted corrective hint.
    4.  Merge the retry result with the original (dedup by key fields).

The module is deliberately additive: it only ever *adds* rows, never removes
them. Pre-existing green paths (machine-generated schedules that already
return complete data) therefore never regress.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import List, Optional, Tuple

from page_evidence import PageEvidence, collect as collect_evidence, confidence_score
from page_extractor import PageType, get_raw_paddle_ocr
from prompts import build_crop_door_prompt, build_crop_hardware_prompt
from prompts.rescue import DOOR_SELF_VERIFICATION_HINT, HARDWARE_SELF_VERIFICATION_HINT
from vision_crops import crop_summary

logger = logging.getLogger("verification")

_DOOR_TYPE_OR_PROFILE_LABEL_RE = re.compile(
    r"^(?:A|B|C|E|F|G|H|I|J|K|AL|HM|WD|FR|FG)[-]?\d+[A-Z]?$",
    re.IGNORECASE,
)

_HARDWARE_COMPONENT_TERMS = (
    "HINGE",
    "LOCK",
    "LATCH",
    "CLOSER",
    "STOP",
    "SEAL",
    "SWEEP",
    "THRESHOLD",
    "EXIT DEVICE",
    "PUSH",
    "PULL",
    "KICK PLATE",
    "WEATHERSTRIP",
    "GASKET",
    "CYLINDER",
    "STRIKE",
    "BOLT",
)

_EXPLICIT_HW_SET_HEADER_RE = re.compile(
    r"\b(?:HARDWARE\s+)?(?:SET|GROUP|HW\s*SET|HDW\s*SET|SET\s*NO\.?|GROUP\s*NO\.?)\b"
    r"[\s:#.-]*(?:[A-Z]?\d|\d+[A-Z]?|[A-Z])",
    re.IGNORECASE,
)


# ─── Helpers ──────────────────────────────────────────────────────
def _door_key(row: dict) -> str:
    return str(row.get("door_number") or "").strip().upper()


def _hw_key(row: dict) -> Tuple[str, str]:
    hw_id = str(row.get("hardware_set_id") or "").strip().upper()
    desc = str(row.get("description") or "").strip().upper()
    return hw_id, desc


def _clean_hw_ref(value: object) -> str:
    token = str(value or "").strip().upper()
    if token in {"", "?", "N/A", "NA", "NONE", "NULL", "-", "--", "---", "----"}:
        return ""
    token = re.sub(r"^(?:HW|HDWR|HARDWARE|SET|GROUP)[\s.#:-]*", "", token).strip()
    if token.endswith(".0"):
        token = token[:-2]
    return token


def _sort_hw_refs(values: set[str] | list[str]) -> list[str]:
    def key(value: str):
        return (0, int(value)) if value.isdigit() else (1, value)

    return sorted((v for v in values if v), key=key)


def _missing_referenced_hw_sets(doors: List[dict], hardware: List[dict]) -> list[str]:
    referenced = {_clean_hw_ref(d.get("hardware_set")) for d in doors}
    present = {_clean_hw_ref(h.get("hardware_set_id")) for h in hardware}
    return _sort_hw_refs(referenced - present - {""})


def _missing_hw_repair_hint(missing_sets: list[str]) -> str:
    wanted = ", ".join(missing_sets)
    visible = ", ".join(f"Set: {set_id}" for set_id in missing_sets)
    scope = (
        "this single requested set"
        if len(missing_sets) == 1
        else "these requested sets"
    )
    return (
        "TARGETED MISSING-SET REPAIR:\n"
        f"Door rows already reference hardware set IDs that are still missing from the extracted hardware table: {wanted}.\n"
        f"In the attached crop, extract ONLY components visibly belonging to these set headers: {visible}.\n"
        "First locate each underlined Set header in the image. If a requested Set header is not visibly present in this crop, "
        f"return no rows for that set. Do NOT extract neighboring sets. Focus on {scope}. For each visible requested set, read the component rows "
        "beneath that set header down to the next Set header in the same local column. Ignore component rows physically above the requested Set header. "
        "Use the Description line immediately below the requested Set header as hardware_set_name when present. "
        "If several set blocks are side-by-side, keep the requested set header, its Doors/Description lines, and its component rows in the same local x-column; "
        "never borrow component rows from a neighboring set block."
    )


def _hardware_repair_crop_rank(crop: dict):
    source = str(crop.get("source") or "")
    if "column" in source.lower():
        bucket = 0
    elif "upper-right" in source.lower() or "lower-right" in source.lower():
        bucket = 1
    else:
        bucket = 2
    return (bucket, -float(crop.get("confidence") or 0.0))


def _door_gap(doors: List[dict], evidence: PageEvidence) -> int:
    unique = {_door_key(d) for d in doors if _door_key(d)}
    expected = evidence.expected_door_rows()
    return max(0, expected - len(unique))


def _hw_gap(hardware: List[dict], evidence: PageEvidence) -> int:
    unique_sets = {str(h.get("hardware_set_id") or "").strip().upper() for h in hardware}
    unique_sets.discard("")
    unique_sets.discard("?")
    expected_sets = evidence.expected_hw_sets()
    set_gap = max(0, expected_sets - len(unique_sets))
    # Also check components-per-set sanity: a well-extracted set has >= 2 components.
    expected_components = evidence.hw_components
    component_gap = max(0, expected_components - len(hardware))
    return max(set_gap * 3, component_gap)  # weight missing sets heavier


def _dedup_doors(existing: List[dict], new: List[dict]) -> List[dict]:
    best = {_door_key(d): d for d in existing if _door_key(d)}
    merged_without_key = [d for d in existing if not _door_key(d)]
    for d in new:
        k = _door_key(d)
        if not k:
            continue
        if k not in best or _row_completeness(d) > _row_completeness(best[k]):
            best[k] = d
    return merged_without_key + list(best.values())


def _dedup_hw(existing: List[dict], new: List[dict]) -> List[dict]:
    seen = {_hw_key(h) for h in existing}
    merged = list(existing)
    for h in new:
        k = _hw_key(h)
        if k == ("", "") or k in seen:
            continue
        seen.add(k)
        merged.append(h)
    return merged


def _row_completeness(row: dict) -> int:
    return sum(1 for value in row.values() if value not in (None, "", "N/A", [], {}))


def _has_physical_door_attrs(row: dict) -> bool:
    return any(
        row.get(field) not in (None, "", "N/A", [], {})
        for field in (
            "door_width", "door_height", "door_thickness", "door_material",
            "door_type", "frame_material", "fire_rating",
        )
    )


def _crop_count(crop_candidates: list[dict], *types: str) -> int:
    allowed = set(types)
    return sum(1 for crop in crop_candidates if crop.get("crop_type") in allowed)


def _crop_supporting_text(page_text: str, crop: dict) -> str:
    crop_text = str(crop.get("text") or "").strip()
    ocr_text = _crop_ocr_text(crop) if _is_crop_only_rescue_context(page_text) else ""
    if not crop_text and not ocr_text:
        return page_text
    parts = []
    if ocr_text:
        parts.append(
            "=== LOCAL OCR WORDS FROM THIS CROP (sorted top-to-bottom, left-to-right) ===\n"
            f"{ocr_text}"
        )
    if crop_text:
        parts.append(f"=== TEXT EXTRACTED FROM THIS CROP ===\n{crop_text}")
    parts.append(f"=== FULL PAGE CONTEXT ===\n{page_text}")
    return "\n\n".join(parts)


def _crop_ocr_text(crop: dict, max_items: int = 220) -> str:
    cache_key = f"_ocr_text_{max_items}"
    if cache_key in crop:
        return str(crop.get(cache_key) or "")

    try:
        import cv2
        import numpy as np
    except Exception:
        return ""

    try:
        b64 = crop.get("base64_image")
        if not b64:
            return ""
        ocr = get_raw_paddle_ocr()
        if ocr is None:
            return ""
        raw = base64.b64decode(b64)
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return ""
        result = ocr.ocr(image, cls=True)
    except Exception as exc:
        logger.debug("Crop OCR support failed: %s", exc)
        return ""

    items: list[tuple[float, float, str, float]] = []
    for page in result or []:
        for box, rec in page or []:
            try:
                text, conf = rec
                text = str(text or "").strip()
                if not text or float(conf) < 0.45:
                    continue
                xs = [point[0] for point in box]
                ys = [point[1] for point in box]
                items.append((min(ys), min(xs), text, float(conf)))
            except Exception:
                continue
    if not items:
        return ""

    lines = []
    for y, x, text, conf in sorted(items)[:max_items]:
        lines.append(f"y={int(round(y))} x={int(round(x))} conf={conf:.2f} text={text}")
    result = "\n".join(lines)
    crop[cache_key] = result
    return result


def _is_crop_only_rescue_context(page_text: str) -> bool:
    return "VISION_CROP_RESCUE" in str(page_text or "").upper()


def _crop_visible_text(crop: dict) -> str:
    cached = crop.get("_visible_text")
    if cached is not None:
        return str(cached)

    parts = []
    crop_text = str(crop.get("text") or "").strip()
    if crop_text:
        parts.append(crop_text)
    ocr_text = _crop_ocr_text(crop)
    if ocr_text:
        parts.append(ocr_text)

    visible = "\n".join(parts).strip()
    crop["_visible_text"] = visible
    return visible


def _crop_search_text(crop: dict) -> str:
    cached = crop.get("_search_text")
    if cached is not None:
        return str(cached)

    search_lines = []
    for line in _crop_visible_text(crop).splitlines():
        if " text=" in line:
            search_lines.append(line.split(" text=", 1)[1])
        elif not line.lstrip().startswith("y="):
            search_lines.append(line)
    search = re.sub(r"\s+", " ", "\n".join(search_lines).upper()).strip()
    crop["_search_text"] = search
    return search


def _visible_token(search_text: str, value: object) -> bool:
    token = str(value or "").strip().upper()
    if not token:
        return False
    return re.search(rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])", search_text) is not None


def _visible_phrase(search_text: str, value: object) -> bool:
    phrase = re.sub(r"\s+", " ", str(value or "").upper()).strip()
    if not phrase:
        return False
    return phrase in search_text


def _crop_has_door_schedule_evidence(crop: dict, page_text: str) -> bool:
    if not _is_crop_only_rescue_context(page_text):
        return True

    search = _crop_search_text(crop)
    if not search:
        # If OCR support is unavailable, let the vision model inspect the crop.
        return True
    if "DOOR SCHEDULE" in search or "DOOR SCHED" in search or "OPENING LIST" in search:
        return True
    has_row_id_header = re.search(r"\b(?:DOOR\s+NO|DOOR\s+#|NO\.|MARK|OPENING|TAG)\b", search) is not None
    has_door_columns = re.search(r"\b(?:ROOM|WIDTH|HEIGHT|SIZE|FRAME|MATERIAL|HDW|HARDWARE)\b", search) is not None
    return bool(has_row_id_header and has_door_columns)


def _crop_has_hardware_schedule_evidence(crop: dict, page_text: str) -> bool:
    if not _is_crop_only_rescue_context(page_text):
        return True

    search = _crop_search_text(crop)
    if not search:
        return True
    if any(marker in search for marker in ("DOOR HARDWARE", "HARDWARE SET", "HARDWARE SCHEDULE", "HARDWARE GROUP")):
        return True
    if _EXPLICIT_HW_SET_HEADER_RE.search(search):
        return True
    component_hits = sum(1 for term in _HARDWARE_COMPONENT_TERMS if term in search)
    return component_hits >= 2


def _filter_crop_door_rows(rows: List[dict], crop: dict, page_text: str) -> List[dict]:
    if not rows or not _is_crop_only_rescue_context(page_text):
        return rows

    search = _crop_search_text(crop)
    if not search:
        return rows

    filtered: list[dict] = []
    for row in rows:
        door_number = _door_key(row)
        if not door_number:
            continue
        if _DOOR_TYPE_OR_PROFILE_LABEL_RE.match(door_number):
            logger.debug("Dropping crop door row with type/profile label as mark: %s", door_number)
            continue

        room_name = re.sub(r"\s+", " ", str(row.get("room_name") or "").upper()).strip()
        door_number_visible = _visible_token(search, door_number)

        # Crop-only pages are where hallucinated generic rows are most likely.
        # If the model invents a plausible room/mark pair not present in OCR,
        # keep it out of the merge instead of polluting otherwise-good results.
        if not door_number_visible:
            logger.debug("Dropping crop door row without visible mark: %s %s", door_number, room_name)
            continue

        filtered.append(row)
    return filtered


def _normalize_crop_hardware_rows(rows: List[dict], crop: dict, page_text: str) -> List[dict]:
    if not rows or not _is_crop_only_rescue_context(page_text):
        return rows

    search = _crop_search_text(crop)
    if not search:
        return rows

    has_explicit_set_header = _EXPLICIT_HW_SET_HEADER_RE.search(search) is not None
    if has_explicit_set_header:
        return rows

    normalized: list[dict] = []
    for row in rows:
        hw_id = _clean_hw_ref(row.get("hardware_set_id"))
        if not hw_id or hw_id.isdigit() or re.fullmatch(r"[A-Z]", hw_id):
            row = dict(row)
            row["hardware_set_id"] = "DOOR_HARDWARE"
            row.setdefault("hardware_set_name", "DOOR HARDWARE")
        normalized.append(row)
    return normalized


def _repair_crop_supporting_text(page_text: str, crop: dict) -> str:
    parts = []
    ocr_text = _crop_ocr_text(crop)
    if ocr_text:
        parts.append(
            "=== LOCAL OCR WORDS FROM THIS CROP (sorted top-to-bottom, left-to-right) ===\n"
            f"{ocr_text}"
        )
    crop_text = str(crop.get("text") or "").strip()
    if crop_text:
        parts.append(f"=== TEXT EXTRACTED FROM THIS CROP ===\n{crop_text}")
    if page_text:
        parts.append(f"=== FULL PAGE CONTEXT ===\n{page_text}")
    return "\n\n".join(parts)


def _needs_crop_door_rescue(doors: List[dict], evidence: PageEvidence, page_type: str, crop_candidates: list[dict]) -> bool:
    if not crop_candidates:
        return False
    door_crop_count = _crop_count(crop_candidates, "door", "mixed")
    if needs_door_rescue(doors, evidence, page_type):
        return True
    if page_type in (PageType.DOOR_SCHEDULE, PageType.MIXED) and not doors and door_crop_count:
        return True
    unique = len({_door_key(d) for d in doors if _door_key(d)})
    # Scanned/cropped sheets often have no parseable dimension tokens in OCR,
    # so expected_door_rows() is intentionally conservative. If there are
    # multiple schedule crops plus many door-mark-like tokens, a one-row result
    # is still a severe undershoot and deserves crop-level vision.
    if (
        page_type in (PageType.DOOR_SCHEDULE, PageType.MIXED)
        and door_crop_count >= 2
        and unique < 3
        and (evidence.real_door_numbers >= 5 or evidence.schedule_headers >= 2)
    ):
        return True
    if doors and not any(_has_physical_door_attrs(d) for d in doors) and any(
        crop.get("crop_type") in ("door", "mixed") for crop in crop_candidates
    ):
        return True
    return False


def _needs_crop_hardware_rescue(hardware: List[dict], evidence: PageEvidence, page_type: str, crop_candidates: list[dict]) -> bool:
    if not crop_candidates:
        return False
    hardware_crop_count = _crop_count(crop_candidates, "hardware", "mixed")
    if needs_hardware_rescue(hardware, evidence, page_type):
        return True
    if hardware_crop_count == 0:
        return False
    if page_type in (PageType.HARDWARE_SET, PageType.MIXED) and not hardware:
        return True
    if not hardware and (evidence.hw_components >= 2 or evidence.hw_set_headers >= 1):
        return True
    if (
        page_type in (PageType.HARDWARE_SET, PageType.MIXED)
        and hardware_crop_count >= 2
        and len(hardware) < 2
        and evidence.hw_components >= 4
    ):
        return True
    return False


# ─── Escalation gates ─────────────────────────────────────────────
#
# Design philosophy:
#   Rescue is EXPENSIVE — each trigger costs a full GPT-4o Vision call
#   (~$0.03 + 20-60s). On multi-page schedules we were previously firing
#   rescue on every page, adding 0 rows each time because the extraction
#   was already correct. The thresholds below are deliberately conservative:
#   rescue must show a clear, large gap with real evidence of missing data,
#   not a soft "you could have extracted more" feeling.
#
#   Rule of thumb:
#     * fire when extraction returned 0 but evidence says many rows exist
#     * fire when extraction is < 30% of expected AND the absolute gap is
#       material (>= 10 rows)
#     * never fire just because one heuristic overcounts expected
def needs_door_rescue(
    doors: List[dict],
    evidence: PageEvidence,
    page_type: str,
) -> bool:
    if page_type not in (PageType.DOOR_SCHEDULE, PageType.MIXED) and not evidence.is_door_schedule:
        return False
    if not evidence.is_door_schedule and not doors:
        return False
    expected = evidence.expected_door_rows()
    unique = len({_door_key(d) for d in doors if _door_key(d)})

    # Zero extraction but evidence says a real schedule exists.
    if expected >= 5 and unique == 0:
        return True
    if expected >= 3 and unique == 0 and evidence.dimensions >= 3:
        return True

    # Severe undershoot: both ratio and absolute gap must be bad.
    # Previous code fired whenever unique < expected * 0.5, which triggered
    # endlessly on dense schedules where `expected_door_rows()` overcounted.
    if expected >= 20 and unique < expected * 0.3 and (expected - unique) >= 10:
        return True

    # Small schedule shortfall: for small schedules (<15 expected), even missing
    # a single door matters. For larger ones, require a 20% gap.
    if 3 <= expected < 15 and unique > 0 and unique < expected:
        return True
    if expected >= 15 and unique > 0 and unique < expected * 0.8 and (expected - unique) >= 2:
        return True

    return False


def needs_hardware_rescue(
    hardware: List[dict],
    evidence: PageEvidence,
    page_type: str,
) -> bool:
    if page_type not in (PageType.HARDWARE_SET, PageType.MIXED) and not evidence.is_hardware_schedule:
        return False
    if not evidence.is_hardware_schedule and not hardware:
        return False
    expected_sets = evidence.expected_hw_sets()
    unique_sets = {
        str(h.get("hardware_set_id") or "").strip().upper()
        for h in hardware
    }
    unique_sets.discard("")
    unique_sets.discard("?")

    # Strong signal of sets expected but nothing extracted.
    if expected_sets >= 2 and len(unique_sets) == 0:
        return True

    # Evidence shows lots of components but extraction returned almost nothing.
    if evidence.hw_components >= 8 and len(hardware) < 3:
        return True

    return False


# ─── Public entry point ───────────────────────────────────────────
def verify_and_rescue(
    doors: List[dict],
    hardware: List[dict],
    page_text: str,
    page_type: str,
    base64_image: Optional[str],
    *,
    build_door_prompt,
    build_hardware_prompt,
    extract_doors_llm,
    extract_hardware_llm,
    max_chars: int,
    rag_door_chunks: Optional[list] = None,
    rag_hw_chunks: Optional[list] = None,
    prev_level_area: Optional[str] = None,
    prev_set_id: Optional[str] = None,
    crop_candidates: Optional[list[dict]] = None,
) -> Tuple[List[dict], List[dict], dict]:
    """
    Optionally re-run door / hardware extraction with a Vision LLM when the
    current result disagrees with page evidence.

    Returns (doors, hardware, report). `report` is a small dict suitable for
    logging or metric tracking.
    """
    evidence = collect_evidence(page_text)
    crops = crop_candidates or []
    report = {
        "confidence": round(confidence_score(evidence), 3),
        "evidence": evidence.as_dict(),
        "door_rescue": False,
        "hw_rescue": False,
        "door_added": 0,
        "hw_added": 0,
        "crop_count": len(crops),
        "crop_rescue_attempted": False,
        "crop_rescue": False,
        "crop_door_added": 0,
        "crop_hw_added": 0,
        "crop_candidates": crop_summary(crops),
    }

    # Door rescue
    if needs_door_rescue(doors, evidence, page_type) and base64_image:
        before_doors = len(doors)
        hint = DOOR_SELF_VERIFICATION_HINT.format(
            expected=evidence.expected_door_rows(),
            dims=evidence.dimensions,
            rows=evidence.row_lines,
            nums=evidence.real_door_numbers,
            got=before_doors,
        )
        try:
            prompt = build_door_prompt(
                rag_door_chunks or [], page_text + hint,
                max_chars=max_chars,
                is_continuation=False,
                prev_level_area=prev_level_area,
            )
            rescue_doors = extract_doors_llm(
                prompt["system"],
                prompt["user"],
                base64_image=base64_image,
                force_model="gpt-4o",
            )
            doors = _dedup_doors(doors, rescue_doors)
            report["door_rescue"] = True
            report["door_added"] = len(doors) - before_doors
            logger.info(
                "Door rescue: +%d rows (%d→%d, expected %d)",
                report["door_added"], before_doors, len(doors),
                evidence.expected_door_rows(),
            )
        except Exception as e:
            logger.warning("Door rescue failed: %s", e)

    if _needs_crop_door_rescue(doors, evidence, page_type, crops):
        report["crop_rescue_attempted"] = True
        before_doors = len(doors)
        for idx, crop in enumerate(crops, 1):
            if crop.get("crop_type") not in ("door", "mixed"):
                continue
            if not _crop_has_door_schedule_evidence(crop, page_text):
                logger.info("Door crop rescue %d/%d skipped: no local door schedule evidence.", idx, len(crops))
                continue
            try:
                prompt = build_crop_door_prompt(
                    _crop_supporting_text(page_text, crop),
                    crop_meta={k: crop.get(k) for k in ("source", "confidence", "bbox", "page_size", "crop_type")},
                    max_chars=min(max_chars, 7000),
                )
                crop_doors = extract_doors_llm(
                    prompt["system"],
                    prompt["user"],
                    base64_image=crop.get("base64_image"),
                    force_model="gpt-4o",
                )
                raw_count = len(crop_doors)
                crop_doors = _filter_crop_door_rows(crop_doors, crop, page_text)
                doors = _dedup_doors(doors, crop_doors)
                logger.info("Door crop rescue %d/%d returned %d rows (%d after filtering).", idx, len(crops), raw_count, len(crop_doors))
            except Exception as e:
                logger.warning("Door crop rescue failed on crop %d: %s", idx, e)
        added = len(doors) - before_doors
        if added > 0:
            report["door_rescue"] = True
            report["crop_rescue"] = True
            report["crop_door_added"] = added
            report["door_added"] += added

    # Hardware rescue
    if needs_hardware_rescue(hardware, evidence, page_type) and base64_image:
        before_hw = len(hardware)
        hint = HARDWARE_SELF_VERIFICATION_HINT.format(
            expected_sets=evidence.expected_hw_sets(),
            expected_components=evidence.hw_components,
            got_sets=len({
                str(h.get("hardware_set_id") or "").strip().upper()
                for h in hardware
            } - {"", "?"}),
            got_components=before_hw,
        )
        try:
            prompt = build_hardware_prompt(
                rag_hw_chunks or [], page_text + hint,
                max_chars=max_chars,
                is_continuation=False,
                prev_set_id=prev_set_id,
            )
            rescue_hw = extract_hardware_llm(
                prompt["system"],
                prompt["user"],
                base64_image=base64_image,
                force_model="gpt-4o",
            )
            hardware = _dedup_hw(hardware, rescue_hw)
            report["hw_rescue"] = True
            report["hw_added"] = len(hardware) - before_hw
            logger.info(
                "Hardware rescue: +%d components (%d→%d, expected sets=%d)",
                report["hw_added"], before_hw, len(hardware),
                evidence.expected_hw_sets(),
            )
        except Exception as e:
            logger.warning("Hardware rescue failed: %s", e)

    if _needs_crop_hardware_rescue(hardware, evidence, page_type, crops):
        report["crop_rescue_attempted"] = True
        before_hw = len(hardware)
        for idx, crop in enumerate(crops, 1):
            if crop.get("crop_type") not in ("hardware", "mixed"):
                continue
            if not _crop_has_hardware_schedule_evidence(crop, page_text):
                logger.info("Hardware crop rescue %d/%d skipped: no local hardware evidence.", idx, len(crops))
                continue
            try:
                prompt = build_crop_hardware_prompt(
                    _crop_supporting_text(page_text, crop),
                    crop_meta={k: crop.get(k) for k in ("source", "confidence", "bbox", "page_size", "crop_type")},
                    max_chars=min(max_chars, 7000),
                )
                crop_hw = extract_hardware_llm(
                    prompt["system"],
                    prompt["user"],
                    base64_image=crop.get("base64_image"),
                    force_model="gpt-4o",
                )
                raw_count = len(crop_hw)
                crop_hw = _normalize_crop_hardware_rows(crop_hw, crop, page_text)
                hardware = _dedup_hw(hardware, crop_hw)
                logger.info("Hardware crop rescue %d/%d returned %d rows (%d after filtering).", idx, len(crops), raw_count, len(crop_hw))
            except Exception as e:
                logger.warning("Hardware crop rescue failed on crop %d: %s", idx, e)
        added = len(hardware) - before_hw
        if added > 0:
            report["hw_rescue"] = True
            report["crop_rescue"] = True
            report["crop_hw_added"] = added
            report["hw_added"] += added

    missing_hw_sets = _missing_referenced_hw_sets(doors, hardware)
    hardware_crops = [
        crop for crop in crops
        if crop.get("crop_type") in ("hardware", "mixed") and crop.get("base64_image")
        and _crop_has_hardware_schedule_evidence(crop, page_text)
    ]
    if missing_hw_sets and hardware_crops:
        report["crop_rescue_attempted"] = True
        before_hw = len(hardware)
        remaining = missing_hw_sets[:]
        ranked_crops = sorted(hardware_crops, key=_hardware_repair_crop_rank)
        for idx, crop in enumerate(ranked_crops, 1):
            if not remaining:
                break
            for set_id in list(remaining):
                try:
                    prompt = build_crop_hardware_prompt(
                        _repair_crop_supporting_text(page_text, crop),
                        crop_meta={k: crop.get(k) for k in ("source", "confidence", "bbox", "page_size", "crop_type")},
                        max_chars=min(max_chars, 7000),
                    )
                    prompt["user"] = f"{prompt['user']}\n\n{_missing_hw_repair_hint([set_id])}"
                    repair_hw = extract_hardware_llm(
                        prompt["system"],
                        prompt["user"],
                        base64_image=crop.get("base64_image"),
                    )
                    repair_hw = [
                        row for row in repair_hw
                        if _clean_hw_ref(row.get("hardware_set_id")) == set_id
                    ]
                    hardware = _dedup_hw(hardware, repair_hw)
                    remaining = _missing_referenced_hw_sets(doors, hardware)
                    logger.info(
                        "Hardware missing-set repair crop %d/%d for set %s returned %d rows; remaining=%s.",
                        idx, len(ranked_crops), set_id, len(repair_hw), ",".join(remaining) or "none",
                    )
                    if set_id not in remaining:
                        continue
                except Exception as e:
                    logger.warning("Hardware missing-set repair failed on crop %d for set %s: %s", idx, set_id, e)

        added = len(hardware) - before_hw
        if added > 0:
            report["hw_rescue"] = True
            report["crop_rescue"] = True
            report["hw_missing_set_repair"] = True
            report["crop_hw_added"] = report.get("crop_hw_added", 0) + added
            report["hw_added"] += added

    return doors, hardware, report
