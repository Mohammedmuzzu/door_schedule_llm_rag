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
from prompts import build_door_prompt, build_hardware_prompt
from rag_store import query_door_instructions, query_hardware_instructions
from llm_extract import extract_doors_llm, extract_hardware_llm
from page_extractor import PageType

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
        if page_type in (PageType.HARDWARE_SET, PageType.MIXED):
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

    logger.info(
        "Page %d [%s%s]: %d doors, %d hardware components (across %d chunks)",
        page_idx + 1, page_type,
        " (cont)" if is_continuation else "",
        len(all_doors), len(all_hardware), len(chunks)
    )

    return all_doors, all_hardware
