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

import logging
import re
from typing import List, Optional, Tuple

from page_evidence import PageEvidence, collect as collect_evidence, confidence_score
from page_extractor import PageType

logger = logging.getLogger("verification")


# ─── Helpers ──────────────────────────────────────────────────────
def _door_key(row: dict) -> str:
    return str(row.get("door_number") or "").strip().upper()


def _hw_key(row: dict) -> Tuple[str, str]:
    hw_id = str(row.get("hardware_set_id") or "").strip().upper()
    desc = str(row.get("description") or "").strip().upper()
    return hw_id, desc


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
    seen = {_door_key(d) for d in existing if _door_key(d)}
    merged = list(existing)
    for d in new:
        k = _door_key(d)
        if not k or k in seen:
            continue
        seen.add(k)
        merged.append(d)
    return merged


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
    if page_type not in (PageType.DOOR_SCHEDULE, PageType.MIXED):
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

    return False


def needs_hardware_rescue(
    hardware: List[dict],
    evidence: PageEvidence,
    page_type: str,
) -> bool:
    if page_type not in (PageType.HARDWARE_SET, PageType.MIXED):
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


# ─── Re-extraction prompts ────────────────────────────────────────
_DOOR_RESCUE_HINT = (
    "\n\nSELF-VERIFICATION ALERT: Structural analysis of this page indicates "
    "~{expected} door rows (dimensions={dims}, row-like lines={rows}, "
    "door-number tokens={nums}), but the previous extraction produced {got}. "
    "You are being given ANOTHER chance with the page image attached. Use the "
    "image as ground truth: scan every row of the door schedule matrix, "
    "extract EVERY door mark (even if the native text layer is corrupt or "
    "missing). Output the full list — do not omit doors to keep the response "
    "short."
)

_HW_RESCUE_HINT = (
    "\n\nSELF-VERIFICATION ALERT: Structural analysis of this page indicates "
    "~{expected_sets} hardware sets and ~{expected_components} components "
    "(HINGE/CLOSER/LOCK keyword hits), but the previous extraction produced "
    "{got_sets} sets / {got_components} components. Re-examine the page image "
    "carefully. Identify every SET/GROUP header (numeric or descriptive) and "
    "list EVERY component underneath it. Missing a set is worse than merging "
    "two — so err on the side of extracting more."
)


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
) -> Tuple[List[dict], List[dict], dict]:
    """
    Optionally re-run door / hardware extraction with a Vision LLM when the
    current result disagrees with page evidence.

    Returns (doors, hardware, report). `report` is a small dict suitable for
    logging or metric tracking.
    """
    evidence = collect_evidence(page_text)
    report = {
        "confidence": round(confidence_score(evidence), 3),
        "evidence": evidence.as_dict(),
        "door_rescue": False,
        "hw_rescue": False,
        "door_added": 0,
        "hw_added": 0,
    }

    # Door rescue
    if needs_door_rescue(doors, evidence, page_type) and base64_image:
        before_doors = len(doors)
        hint = _DOOR_RESCUE_HINT.format(
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

    # Hardware rescue
    if needs_hardware_rescue(hardware, evidence, page_type) and base64_image:
        before_hw = len(hardware)
        hint = _HW_RESCUE_HINT.format(
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

    return doors, hardware, report
