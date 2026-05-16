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
from prompts.rescue import (
    BORDERLESS_DOOR_RETRY_HINT,
    EVIDENCE_DRIVEN_DOOR_RESCUE_HINT,
    FINAL_HARDWARE_ONLY_RESCUE_HINT,
    HARDWARE_INCOMPLETE_RETRY_HINT,
    final_door_window_rescue_user,
    hardware_missing_sets_hint,
)
from rag_store import query_door_instructions, query_hardware_instructions
from llm_extract import extract_doors_llm, extract_hardware_llm
from page_evidence import collect as collect_evidence
from page_extractor import PageType
from verification import verify_and_rescue

# Module-level sink used by pipeline.py to read the latest verification
# report emitted by this agent. A global is appropriate here because
# extraction runs strictly single-threaded per pipeline invocation.
LAST_VERIFY_REPORT: Optional[dict] = None

logger = logging.getLogger("agent")


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


def _physical_door_count(doors: List[dict]) -> int:
    return sum(1 for door in doors if _has_physical_door_attrs(door))


def _dedupe_doors_by_number(doors: List[dict]) -> List[dict]:
    """Keep the richest row for each door number within a page."""
    best: dict[str, dict] = {}
    for door in doors:
        key = str(door.get("door_number") or "").strip().upper()
        if not key:
            continue
        if key not in best or _row_completeness(door) > _row_completeness(best[key]):
            best[key] = door
    return list(best.values())


def _split_markdown_row(line: str) -> List[str]:
    if "|" not in line:
        return []
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return [cell if cell else None for cell in cells]


def _looks_like_door_mark(value: object) -> bool:
    token = str(value or "").strip()
    if not token or token.upper() in {"MARK", "DOOR", "NO", "NUMBER"}:
        return False
    if re.fullmatch(r"\d{2,4}[A-Za-z]?", token):
        return not (1900 <= int(re.match(r"\d+", token).group()) <= 2099)
    return bool(re.fullmatch(r"[A-Za-z]{1,3}\d{2,4}[A-Za-z]?", token))


def _extract_door_mark_and_room(value: object) -> Tuple[Optional[str], Optional[str]]:
    token = str(value or "").strip()
    if _looks_like_door_mark(token):
        return token, None
    match = re.search(r"\b([A-Za-z]{0,3}\d{2,4}[A-Za-z]?)\b\s*$", token)
    if not match:
        return None, None
    mark = match.group(1)
    digits = int(re.search(r"\d+", mark).group())
    if 1900 <= digits <= 2099:
        return None, None
    room = token[:match.start()].strip(" -:/") or None
    return mark, room


def _is_dimension(value: object) -> bool:
    return bool(re.fullmatch(r"\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\"", str(value or "").strip()))


def _split_combined_dimensions(value: object) -> Optional[Tuple[str, str]]:
    match = re.search(
        r"(\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\")\s*[xX]\s*"
        r"(\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\")",
        str(value or "").strip(),
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _collect_pipe_cells(text: str) -> List[str]:
    cells: List[str] = []
    for line in text.splitlines():
        row = _split_markdown_row(line)
        if row:
            cells.extend(str(cell or "").strip() for cell in row)
    return [cell for cell in cells if cell]


def _parse_door_cell_stream_fallback(text: str) -> List[dict]:
    """
    Recover door rows from flattened pipe-delimited schedules.

    Some A0 sheets arrive as one long pdfplumber row where the table structure is
    gone but the token order is preserved: mark, room, width, height, fields...
    We only accept candidates with two dimensions within the next few cells.
    """
    if "DOOR SCHEDULE" not in text.upper():
        return []

    cells = _collect_pipe_cells(text)
    doors: List[dict] = []
    stop_words = {
        "DOOR", "DOORS", "FRAME", "TYPE", "TYPES", "NOTES", "SCHEDULE",
        "WIDTH", "HEIGHT", "HARDWARE", "DETAIL", "COMMENTS", "MATERIAL",
    }

    for idx, cell in enumerate(cells):
        token = str(cell or "").strip()
        if not _looks_like_door_mark(token):
            continue
        if token.upper() in stop_words:
            continue

        lookahead = cells[idx + 1: idx + 10]
        dims = [value for value in lookahead if _is_dimension(value)]
        if len(dims) < 2:
            continue

        first_dim_idx = next((i for i, value in enumerate(lookahead) if _is_dimension(value)), None)
        between = lookahead[:first_dim_idx] if first_dim_idx is not None else []
        room_name = " ".join(
            value for value in between
            if value and not _looks_like_door_mark(value) and value.upper() not in stop_words
        ) or None

        door_width = dims[0]
        door_height = dims[1]
        hardware_set = None
        for value in lookahead:
            if re.fullmatch(r"\d{1,2}[A-Za-z]?", str(value or "").strip()) and value != token:
                hardware_set = str(value).strip()
                break

        doors.append({
            "door_number": token,
            "room_name": room_name,
            "door_width": door_width,
            "door_height": door_height,
            "hardware_set": hardware_set,
            "is_pair": bool(str(door_width).startswith(("2 @", "6'"))),
            "door_leaves": 2 if str(door_width).startswith(("2 @", "6'")) else 1,
        })

    return _dedupe_doors_by_number(doors)


def _parse_door_table_fallback(text: str) -> List[dict]:
    """
    Deterministic fallback for dense pdfplumber markdown door schedules.

    It intentionally handles only rows with a clear door mark plus width/height
    dimensions, so note blocks and hardware component lists are ignored.
    """
    doors: List[dict] = []
    dim_re = re.compile(r"\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\"")

    for line in text.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 4:
            continue

        mark_idx = None
        for idx, cell in enumerate(cells[:3]):
            if _looks_like_door_mark(cell):
                mark_idx = idx
                break
        if mark_idx is None:
            continue

        tail = cells[mark_idx:]
        dims = dim_re.findall(line)
        combined_dims = next((pair for cell in tail if (pair := _split_combined_dimensions(cell))), None)
        if combined_dims:
            dims = [combined_dims[0], combined_dims[1]]
        if len(dims) < 2:
            continue

        def get(offset: int):
            return tail[offset] if offset < len(tail) else None

        door_number = str(get(0)).strip()
        door_width = dims[0]
        door_height = dims[1]
        door_thickness = dims[2] if len(dims) > 2 else get(5)
        hardware_set = None
        for cell in tail:
            value = str(cell or "").strip()
            if re.fullmatch(r"\d{1,2}[A-Za-z]?", value):
                hardware_set = value
                break

        door = {
            "door_number": door_number,
            "from_room": get(1),
            "room_name": get(2),
            "door_width": door_width,
            "door_height": door_height,
            "door_thickness": door_thickness,
            "door_material": get(6),
            "door_type": get(7),
            "door_finish": get(8),
            "frame_material": get(9),
            "frame_type": get(10),
            "frame_finish": get(11),
            "head_jamb_sill_detail": " / ".join(str(v) for v in [get(12), get(13), get(14)] if v),
            "fire_rating": get(15),
            "hardware_set": hardware_set,
            "remarks": get(17),
            "is_pair": bool(door_width and str(door_width).strip().startswith("6'")),
            "door_leaves": 2 if door_width and str(door_width).strip().startswith("6'") else 1,
        }
        doors.append({k: v for k, v in door.items() if v not in (None, "")})

    if len(doors) < 3:
        for line in text.splitlines():
            cells = _split_markdown_row(line)
            if len(cells) < 4:
                continue
            door_number, embedded_room = _extract_door_mark_and_room(cells[0])
            if not door_number:
                continue
            dim_pair = next((pair for cell in cells if (pair := _split_combined_dimensions(cell))), None)
            if not dim_pair:
                continue
            room_name = embedded_room or str(cells[1] or "").strip() or None
            hardware_set = None
            for cell in cells[3:]:
                value = str(cell or "").strip()
                if re.fullmatch(r"\d{1,2}[A-Za-z]?", value) and value != door_number:
                    hardware_set = value
                    break
            door_width, door_height = dim_pair
            doors.append({
                "door_number": door_number,
                "room_name": room_name,
                "door_width": door_width,
                "door_height": door_height,
                "hardware_set": hardware_set,
                "is_pair": bool(str(door_width).startswith(("2 @", "6'"))),
                "door_leaves": 2 if str(door_width).startswith(("2 @", "6'")) else 1,
            })

    stream_doors = _parse_door_cell_stream_fallback(text) if len(doors) < 3 else []
    merged = _dedupe_doors_by_number(doors + stream_doors)
    return merged


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
    crop_candidates: Optional[List[dict]] = None,
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
    evidence = collect_evidence(raw_text)

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
                hint = BORDERLESS_DOOR_RETRY_HINT
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
            has_hw_sets = len(re.findall(
                r"(?m)^\s*(?:HARDWARE\s+SET|HARDWARE\s+GROUP|HDWE\s+SET|HDWR\s+SET|HW\s+SET|"
                r"SET\s*NO\.?|GROUP\s*NO\.?|HW\s*[#\-]?\s*\d+|SET\s*[#\-]?\s*\d+|GROUP\s*[#\-]?\s*\d+)",
                text.upper(),
            )) >= 1
            has_components = len(re.findall(r"(?:HINGE|CLOSER|LOCK|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP)", text.upper())) >= 2
            if has_hw_sets and has_components:
                force_hardware = True

        should_extract_hardware = (
            force_hardware
            or page_type == PageType.HARDWARE_SET
            or (page_type == PageType.MIXED and evidence.is_hardware_schedule)
        )

        if should_extract_hardware:
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
                    hint = hardware_missing_sets_hint(len(extracted_set_ids), expected_sets)
                else:
                    hint = HARDWARE_INCOMPLETE_RETRY_HINT
                    
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
                rescue_text + FINAL_HARDWARE_ONLY_RESCUE_HINT,
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

    # ── Evidence-driven door rescue for empty door extractions ──────
    # Some pages are misrouted, and some correctly routed dense schedules still
    # occasionally return an empty JSON array. Structural evidence gets one
    # final door-only pass before verification.
    if (
        len(all_doors) == 0
        and evidence.is_door_schedule
    ):
        logger.warning(
            "Evidence-driven door rescue: page classified as %s but evidence suggests %d door rows.",
            page_type,
            evidence.expected_door_rows(),
        )
        rescue_prompt = build_door_prompt(
            query_door_instructions(raw_text) if use_rag else [],
            raw_text + EVIDENCE_DRIVEN_DOOR_RESCUE_HINT,
            max_chars=MAX_PAGE_CHARS,
            is_continuation=is_continuation,
            prev_level_area=ctx.last_level_area,
        )
        rescued_doors = extract_doors_llm(
            rescue_prompt["system"], rescue_prompt["user"], base64_image=base64_image, force_model="gpt-4o"
        )
        if rescued_doors:
            all_doors = _dedupe_doors_by_number(all_doors + rescued_doors)
            if all_doors:
                ctx.update_from_doors(all_doors)

        if not all_doors:
            parsed_doors = _parse_door_table_fallback(raw_text)
            if parsed_doors:
                logger.warning(
                    "Deterministic door table fallback recovered %d rows after LLM rescue returned empty.",
                    len(parsed_doors),
                )
                all_doors = _dedupe_doors_by_number(all_doors + parsed_doors)
                ctx.update_from_doors(all_doors)

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
        user = final_door_window_rescue_user(raw_text, MAX_PAGE_CHARS)
        rescued_doors = extract_doors_llm(SYSTEM_DOOR, user, base64_image=base64_image, force_model="gpt-4o")
        if rescued_doors:
            seen_doors = {str(d.get("door_number") or "").strip().upper() for d in all_doors}
            for d in rescued_doors:
                key = str(d.get("door_number") or "").strip().upper()
                if key and key not in seen_doors:
                    seen_doors.add(key)
                    all_doors.append(d)
            ctx.update_from_doors(all_doors)

    all_doors = _dedupe_doors_by_number(all_doors)

    physical_count = _physical_door_count(all_doors)
    should_try_fallback = (
        evidence.is_door_schedule
        and (
            len(all_doors) < max(1, evidence.expected_door_rows() // 2)
            or physical_count < max(1, min(len(all_doors), evidence.expected_door_rows()) // 2)
            or (3 <= evidence.expected_door_rows() <= 20 and len(all_doors) < evidence.expected_door_rows())
        )
    )
    if should_try_fallback:
        parsed_doors = _parse_door_table_fallback(raw_text)
        parsed_physical = _physical_door_count(parsed_doors)
        if parsed_physical > physical_count and len(parsed_doors) >= max(1, len(all_doors) // 2):
            logger.warning(
                "Deterministic door table fallback recovered %d physical rows; replacing %d weak LLM rows.",
                len(parsed_doors),
                len(all_doors),
            )
            all_doors = parsed_doors
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
            crop_candidates=crop_candidates,
        )
        if verify_report["door_rescue"] or verify_report["hw_rescue"] or verify_report.get("crop_rescue"):
            logger.info(
                "Page %d verification: confidence=%.2f, door_rescue=%s (+%d), "
                "hw_rescue=%s (+%d), crop_rescue=%s (+doors %d, +hw %d)",
                page_idx + 1,
                verify_report["confidence"],
                verify_report["door_rescue"],
                verify_report["door_added"],
                verify_report["hw_rescue"],
                verify_report["hw_added"],
                verify_report.get("crop_rescue"),
                verify_report.get("crop_door_added", 0),
                verify_report.get("crop_hw_added", 0),
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
