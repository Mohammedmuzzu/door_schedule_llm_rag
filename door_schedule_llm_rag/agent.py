"""
Agent: orchestate extraction for one page with context awareness.

Key improvements over original:
1. Only extracts doors from door pages, hardware from hardware pages
2. Tracks multi-page continuity (last hardware_set_id, last level/area)
3. Retry with borderless-table hint when first attempt yields nothing
4. Validates extraction quality
"""
import logging
import re
from typing import List, Tuple, Optional

from config import MAX_PAGE_CHARS
from prompts import SYSTEM_DOOR, build_door_prompt, build_hardware_prompt
from rag_store import query_door_instructions, query_hardware_instructions
from llm_extract import extract_doors_llm, extract_hardware_llm
from page_extractor import PageType
from verification import verify_and_rescue

# Module-level sink used by pipeline.py to read the latest verification
# report emitted by this agent. A global is appropriate here because
# extraction runs strictly single-threaded per pipeline invocation.
LAST_VERIFY_REPORT: Optional[dict] = None

logger = logging.getLogger("agent")


class ExtractionContext:
    """Track state across pages for multi-page table continuity."""

    def __init__(self):
        self.last_page_type: Optional[str] = None
        self.last_level_area: Optional[str] = None
        self.last_hardware_set_id: Optional[str] = None
        self.door_numbers_seen: set = set()

    def update_from_doors(self, doors: List[dict]):
        if doors:
            self.last_page_type = PageType.DOOR_SCHEDULE
            for d in doors:
                dn = d.get("door_number", "")
                if dn:
                    self.door_numbers_seen.add(dn)
                la = d.get("level_area")
                if la:
                    self.last_level_area = la

    def update_from_hardware(self, hardware: List[dict]):
        if hardware:
            self.last_page_type = PageType.HARDWARE_SET
            for h in hardware:
                hs = h.get("hardware_set_id")
                if hs and hs != "?":
                    self.last_hardware_set_id = hs


def extract_page_with_llm(
    page_text: str,
    page_type: str = PageType.MIXED,
    page_idx: int = 0,
    use_rag: bool = True,
    retry_with_hint: bool = True,
    is_continuation: bool = False,
    context: Optional[ExtractionContext] = None,
    base64_image: Optional[str] = None,
) -> Tuple[List[dict], List[dict]]:
    """
    Extract door rows and/or hardware component rows from one page.

    Args:
        page_text: Structured text from page_extractor
        page_type: Classification from page_extractor
        page_idx: Page index (0-based)
        use_rag: Whether to use RAG retrieval
        retry_with_hint: Whether to retry on empty results
        is_continuation: Whether this is a continuation page
        context: ExtractionContext for multi-page tracking

    Returns:
        (door_rows, hardware_rows)
    """
    raw_text = (page_text or "").strip()
    if not raw_text or len(raw_text) < 30:
        return [], []

    # Semantic Chunking for smaller models
    # Split text into chunks of roughly MAX_PAGE_CHARS cleanly on newlines
    chunks = []
    current_chunk = []
    current_len = 0
    
    for line in raw_text.split('\n'):
        # If adding this line exceeds max (and we already have some lines), cut here
        if current_len + len(line) > MAX_PAGE_CHARS and current_chunk:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line) + 1 # +1 for newline

    if current_chunk:
        chunks.append('\n'.join(current_chunk))

    # Fallback if no chunks could be formed
    if not chunks:
        chunks = [raw_text[:MAX_PAGE_CHARS]]

    ctx = context or ExtractionContext()
    all_doors = []
    all_hardware = []

    def _line_chunks(text: str, limit: int = 7000) -> List[str]:
        chunks_out: List[str] = []
        buf: List[str] = []
        size = 0
        for line in text.splitlines():
            line_len = len(line) + 1
            if buf and size + line_len > limit:
                chunks_out.append("\n".join(buf))
                buf = [line]
                size = line_len
            else:
                buf.append(line)
                size += line_len
        if buf:
            chunks_out.append("\n".join(buf))
        return chunks_out or [text[:limit]]

    for chunk_idx, text in enumerate(chunks):
        doors = []
        hardware = []

        # ── Extract Doors (if page has door content) ──
        if page_type in (PageType.DOOR_SCHEDULE, PageType.MIXED):
            door_chunks = query_door_instructions(text) if use_rag else []
            door_prompt = build_door_prompt(
                door_chunks, text,
                max_chars=MAX_PAGE_CHARS,
                is_continuation=is_continuation,
                prev_level_area=ctx.last_level_area,
            )
            doors = extract_doors_llm(door_prompt["system"], door_prompt["user"], base64_image=base64_image)

            # Retry if empty and page looks like it has door data
            if not doors and retry_with_hint and len(text) > 200:
                hint = (
                    "\n\nCRITICAL CORRECTIVE ACTION: This is likely a BORDERLESS profile list "
                    "(e.g. 'DRY STORAGE 105 3-0 8-10 Alum'). You MUST visually identify the isolated physical door "
                    "numbers (like 105, 106, 208) even if there are no table borders, and extract every row. "
                    "In inline text, the room name often comes before the door number; parse it properly."
                )
                door_prompt2 = build_door_prompt(
                    door_chunks, text + hint,
                    max_chars=MAX_PAGE_CHARS,
                    is_continuation=is_continuation,
                    prev_level_area=ctx.last_level_area,
                )
                doors = extract_doors_llm(door_prompt2["system"], door_prompt2["user"], base64_image=base64_image, force_model="gpt-4o")

            ctx.update_from_doors(doors)

        # ── Extract Hardware (if page has hardware content) ──
        # Fallback: if classified as DOOR_SCHEDULE but text clearly has hardware sets, force extraction.
        force_hardware = False
        if page_type == PageType.DOOR_SCHEDULE:
            has_hw_sets = len(re.findall(r"(?:SET|GROUP|HW|HDWE|HARDWARE)\s*(?:NO\.?|#)?\s*[\w\d]+", text.upper())) >= 2
            has_components = len(re.findall(r"(?:HINGE|CLOSER|LOCK|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP)", text.upper())) >= 2
            if has_hw_sets and has_components:
                force_hardware = True
                
        if page_type in (PageType.HARDWARE_SET, PageType.MIXED) or force_hardware:
            hw_chunks = query_hardware_instructions(text) if use_rag else []
            hw_prompt = build_hardware_prompt(
                hw_chunks, text,
                max_chars=MAX_PAGE_CHARS,
                is_continuation=is_continuation,
                prev_set_id=ctx.last_hardware_set_id,
            )
            hardware = extract_hardware_llm(hw_prompt["system"], hw_prompt["user"], base64_image=base64_image)

            # ── Corrective Agentic Loop / Heuristic Counters ──
            # Count explicit markers in the text
            expected_sets = len(set(re.findall(r'(?i)(?:set[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|group[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|hardware set no\.)', text)))
            extracted_set_ids = set()
            for h in hardware:
                hs = h.get("hardware_set_id")
                if hs and hs != "?":
                    extracted_set_ids.add(hs)
                    
            is_missing_sets = len(extracted_set_ids) < expected_sets - 1  # Allowing for slight mismatch in regex

            # Retry if empty, suspiciously small, or heuristic count fails
            if (not hardware or is_missing_sets or (len(hardware) < 5 and len(text) > 5000)) and retry_with_hint and len(text) > 200:
                if is_missing_sets:
                    logger.warning(f"Heuristic Trigger: Extracted {len(extracted_set_ids)} hw sets, expected ~{expected_sets}. Triggering corrective retry.")
                    hint = (
                        f"\n\nCRITICAL CORRECTIVE ACTION: The previous extraction missed data. "
                        f"You extracted {len(extracted_set_ids)} unique sets, but there are structural markers indicating up to {expected_sets} sets in this block. "
                        "If there is a MULTI-COLUMN LAYOUT (side-by-side sets on the same line, e.g. GROUP#1  GROUP#2  GROUP#3), "
                        "you MUST mentally split them horizontally! Extract ALL parallel sets distinctly. Do not drop data."
                    )
                else:
                    hint = (
                        "\n\nNOTE: The previous extraction was incomplete. "
                        "You MUST process the entire document. Look for all hardware set headers and component lines deep in the text."
                    )
                    
                hw_prompt2 = build_hardware_prompt(
                    hw_chunks, text + hint,
                    max_chars=MAX_PAGE_CHARS,
                    is_continuation=is_continuation,
                    prev_set_id=ctx.last_hardware_set_id,
                )
                hardware = extract_hardware_llm(hw_prompt2["system"], hw_prompt2["user"], base64_image=base64_image, force_model="gpt-4o")

            ctx.update_from_hardware(hardware)
            
        all_doors.extend(doors)
        all_hardware.extend(hardware)

    # ── Full-page hardware rescue ─────────────────────────────────
    # Dense hardware-only sheets can be misclassified as MIXED and the first
    # hardware pass may return [] after a door-focused interpretation. If the
    # raw text has many explicit set/component markers, make one final
    # hardware-only call over the full page text and merge it additively.
    hw_marker_count = len(re.findall(
        r"(?i)\b(?:HARDWARE\s+SET|SET\s*(?:NO\.?|#)?\s*[\w\d.-]+|GROUP\s*(?:NO\.?|#)?\s*[\w\d.-]+)\b",
        raw_text,
    ))
    hw_component_count = len(re.findall(
        r"(?i)\b(?:HINGE|CLOSER|LOCKSET|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP|STOP|SEAL|GASKET|EXIT\s+DEVICE)\b",
        raw_text,
    ))
    if (
        len(all_hardware) == 0
        and hw_marker_count >= 3
        and hw_component_count >= 5
        and len(raw_text) > 1000
    ):
        logger.warning(
            "Full-page hardware rescue: %d set markers and %d component hits but 0 hardware rows.",
            hw_marker_count, hw_component_count,
        )
        seen = {
            (
                str(h.get("hardware_set_id") or "").strip().upper(),
                str(h.get("description") or "").strip().upper(),
            )
            for h in all_hardware
        }
        for rescue_idx, rescue_text in enumerate(_line_chunks(raw_text, limit=6500), 1):
            rescue_prompt = build_hardware_prompt(
                query_hardware_instructions(rescue_text) if use_rag else [],
                rescue_text + (
                    "\n\nFINAL HARDWARE-ONLY RESCUE CHUNK: Ignore door schedule rows and title blocks. "
                    "This chunk is from a dense hardware-set sheet. Extract ONLY hardware components "
                    "grouped under each SET/GROUP header visible in this chunk. If sets are side-by-side "
                    "in columns, split the columns mentally and preserve each set id."
                ),
                max_chars=8000,
                is_continuation=is_continuation,
                prev_set_id=ctx.last_hardware_set_id,
            )
            rescued_hw = extract_hardware_llm(
                rescue_prompt["system"], rescue_prompt["user"], base64_image=None, force_model="gpt-4o"
            )
            logger.info(
                "Full-page hardware rescue chunk %d returned %d rows.",
                rescue_idx, len(rescued_hw),
            )
            for h in rescued_hw:
                key = (
                    str(h.get("hardware_set_id") or "").strip().upper(),
                    str(h.get("description") or "").strip().upper(),
                )
                if key not in seen:
                    seen.add(key)
                    all_hardware.append(h)
        if all_hardware:
            ctx.update_from_hardware(all_hardware)

    # ── Full-page door rescue for door/window schedule markup pages ──
    # Some vector markup pages expose "DOOR/WINDOW SCHEDULE" text and visible
    # hardware/profile rows, but the standard door prompt returns [] because
    # labels are short numeric profile marks rather than room doors. A final
    # door-only rescue is justified when we already found hardware but no doors.
    if (
        len(all_doors) == 0
        and len(all_hardware) > 0
        and (
            re.search(r"(?i)\bDOOR\b.*\bSCHEDULE\b|\bWINDOW\b.*\bSCHEDULE\b", raw_text)
            or page_type == PageType.MIXED  # Scanned PDFs classified as MIXED with 0 doors need rescue
        )
    ):
        logger.warning(
            "Full-page door rescue: schedule text and %d hardware rows but 0 door rows.",
            len(all_hardware),
        )
        user = (
            "=== START TEXT ===\n"
            f"{raw_text[:MAX_PAGE_CHARS]}\n"
            "=== END TEXT ===\n\n"
            "FINAL DOOR/WINDOW SCHEDULE RESCUE: Extract door/profile rows even if the primary "
            "mark is a short numeric profile ID (1, 2, 3) or a storefront/window/door type. "
            "Do NOT require room names. Treat each visible schedule/profile row as a door "
            "schedule row when it has dimensions, hardware, frame, or door/window type fields. "
            "Return the same JSON shape as the normal door extractor."
        )
        rescued_doors = extract_doors_llm(SYSTEM_DOOR, user, base64_image=base64_image, force_model="gpt-4o")
        if rescued_doors:
            seen_doors = {str(d.get("door_number") or "").strip().upper() for d in all_doors}
            for d in rescued_doors:
                key = str(d.get("door_number") or "").strip().upper()
                if key and key not in seen_doors:
                    seen_doors.add(key)
                    all_doors.append(d)
            ctx.update_from_doors(all_doors)

    # ── Self-verification pass ──
    # Compare the final per-page result against structural evidence. If the
    # gap is large (or extraction is empty while evidence says a schedule is
    # present), re-run with the Vision LLM and merge the results. This is the
    # mechanism that replaces brittle format-specific rules with a general
    # "evidence-driven escalation" loop and is the primary lever for hitting
    # the PRD's 99.5% accuracy target on unfamiliar PDF layouts.
    global LAST_VERIFY_REPORT
    LAST_VERIFY_REPORT = None
    try:
        all_doors, all_hardware, verify_report = verify_and_rescue(
            all_doors,
            all_hardware,
            raw_text,
            page_type,
            base64_image,
            build_door_prompt=build_door_prompt,
            build_hardware_prompt=build_hardware_prompt,
            extract_doors_llm=extract_doors_llm,
            extract_hardware_llm=extract_hardware_llm,
            max_chars=MAX_PAGE_CHARS,
            rag_door_chunks=query_door_instructions(raw_text) if use_rag else None,
            rag_hw_chunks=query_hardware_instructions(raw_text) if use_rag else None,
            prev_level_area=ctx.last_level_area,
            prev_set_id=ctx.last_hardware_set_id,
        )
        if verify_report["door_rescue"] or verify_report["hw_rescue"]:
            logger.info(
                "Page %d verification: confidence=%.2f, door_rescue=%s (+%d), "
                "hw_rescue=%s (+%d)",
                page_idx + 1,
                verify_report["confidence"],
                verify_report["door_rescue"],
                verify_report["door_added"],
                verify_report["hw_rescue"],
                verify_report["hw_added"],
            )
        if verify_report.get("door_rescue"):
            ctx.update_from_doors(all_doors)
        if verify_report.get("hw_rescue"):
            ctx.update_from_hardware(all_hardware)
        LAST_VERIFY_REPORT = verify_report
    except Exception as e:
        logger.warning("Verification layer error (non-fatal): %s", e)

    logger.info(
        "Page %d [%s%s]: %d doors, %d hardware components (across %d chunks)",
        page_idx + 1, page_type,
        " (cont)" if is_continuation else "",
        len(all_doors), len(all_hardware), len(chunks)
    )

    return all_doors, all_hardware
