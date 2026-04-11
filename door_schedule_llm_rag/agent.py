"""
Agent: orchestate extraction for one page with context awareness.

Key improvements over original:
1. Only extracts doors from door pages, hardware from hardware pages
2. Tracks multi-page continuity (last hardware_set_id, last level/area)
3. Retry with borderless-table hint when first attempt yields nothing
4. Validates extraction quality
"""
import logging
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
    text = (page_text or "").strip()[:MAX_PAGE_CHARS]
    if not text or len(text) < 30:
        return [], []

    ctx = context or ExtractionContext()
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
        doors = extract_doors_llm(door_prompt["system"], door_prompt["user"])

        # Retry if empty and page looks like it has door data
        if not doors and retry_with_hint and len(text) > 200:
            hint = (
                "\n\nNOTE: The previous extraction returned no results. "
                "This may be a borderless table or unusual layout. "
                "Look harder for door numbers (3-4 digit numbers, possibly with letter suffix) "
                "and extract every door row you can identify."
            )
            door_prompt2 = build_door_prompt(
                door_chunks, text + hint,
                max_chars=MAX_PAGE_CHARS,
                is_continuation=is_continuation,
                prev_level_area=ctx.last_level_area,
            )
            doors = extract_doors_llm(door_prompt2["system"], door_prompt2["user"])

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
        hardware = extract_hardware_llm(hw_prompt["system"], hw_prompt["user"])

        # Retry if empty or suspiciously small (e.g., LLM gave up early on a huge document)
        if (not hardware or (len(hardware) < 5 and len(text) > 5000)) and retry_with_hint and len(text) > 200:
            hint = (
                "\n\nNOTE: The previous extraction was incomplete. "
                "You MUST process the entire document. Look for all hardware set headers (SET NO, GROUP, HARDWARE SET, HW.1, HW.2, etc.) "
                "and component lines (qty + description like HINGE, CLOSER, LOCK) located deep in the text."
            )
            hw_prompt2 = build_hardware_prompt(
                hw_chunks, text + hint,
                max_chars=MAX_PAGE_CHARS,
                is_continuation=is_continuation,
                prev_set_id=ctx.last_hardware_set_id,
            )
            hardware = extract_hardware_llm(hw_prompt2["system"], hw_prompt2["user"])

        ctx.update_from_hardware(hardware)

    logger.info(
        "Page %d [%s%s]: %d doors, %d hardware components",
        page_idx + 1, page_type,
        " (cont)" if is_continuation else "",
        len(doors), len(hardware),
    )

    return doors, hardware
