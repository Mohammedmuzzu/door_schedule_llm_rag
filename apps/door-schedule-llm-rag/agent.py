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
from llm_extract import extract_doors_llm, extract_hardware_llm, normalize_hardware_rows
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


def _drop_self_referential_hardware_sets(doors: List[dict]) -> List[dict]:
    for door in doors:
        door_number = re.sub(r"\s+", "", str(door.get("door_number") or "")).upper()
        hardware_set = re.sub(r"\s+", "", str(door.get("hardware_set") or "")).upper()
        if hardware_set and hardware_set == door_number and re.search(r"[A-Z]", door_number):
            door.pop("hardware_set", None)
    return doors


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


def _find_dimensions(value: object) -> List[str]:
    return re.findall(
        r"\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\"",
        str(value or ""),
    )


def _looks_like_combined_dimensions(value: object) -> bool:
    return _split_combined_dimensions(value) is not None


def _normalize_door_mark_cell(value: object) -> Tuple[Optional[str], Optional[str]]:
    """Return a door mark and optional trailing keyed note from a table cell."""
    token = str(value or "").strip()
    if _looks_like_door_mark(token):
        return token, None
    match = re.fullmatch(r"([A-Za-z]{0,3}\d{2,4}[A-Za-z]?)(?:\s+(\d{1,2}))?", token)
    if not match:
        return None, None
    mark = match.group(1)
    if not _looks_like_door_mark(mark):
        return None, None
    return mark, match.group(2)


def _extract_leading_door_mark(value: object) -> Tuple[Optional[str], Optional[str]]:
    token = str(value or "").strip()
    match = re.match(r"^([A-Za-z]{0,3}\d{2,4}[A-Za-z]?)(?:\b|\s)(.*)$", token)
    if not match:
        return None, None
    mark = match.group(1)
    if not _looks_like_door_mark(mark):
        return None, None
    note = match.group(2).strip(" '\"-:;") or None
    return mark, note


def _find_best_door_mark_index(cells: List[Optional[str]]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """
    Pick the actual door mark in rows where notes spill into the first cells.

    Example from dense sheets:
    ``DOOR SCHED. NOTES | 24 | 140A | JAN | NEW VESTIBULE | ...``
    The first number is a note marker, while 140A is the door mark.
    """
    best: Tuple[int, int, str, Optional[str]] | None = None
    for idx, cell in enumerate(cells[:6]):
        mark, keyed_note = _normalize_door_mark_cell(cell)
        if not mark:
            continue

        tail = cells[idx + 1: idx + 10]
        dims = sum(1 for value in tail if _is_dimension(value))
        next_cell = next((value for value in tail if str(value or "").strip()), None)
        next_mark, _ = _normalize_door_mark_cell(next_cell)

        score = dims * 4
        if next_cell and not next_mark:
            score += 4
        if next_mark:
            score -= 8
        if re.search(r"[A-Za-z]", mark):
            score += 2
        elif re.fullmatch(r"\d{3,4}", mark):
            score += 1
        if idx > 0 and re.search(r"\bNOTES?\b", str(cells[idx - 1] or ""), re.IGNORECASE):
            score -= 4

        candidate = (score, -idx, mark, keyed_note)
        if best is None or candidate > best:
            best = candidate

    if best is None:
        return None, None, None
    _, neg_idx, mark, keyed_note = best
    return -neg_idx, mark, keyed_note


def _looks_like_hardware_set_token(value: object) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    if _is_dimension(token):
        return False
    if re.search(r"[/'\"]", token):
        return False
    if re.fullmatch(r"[A-Z]?\d{1,4}[A-Za-z]{0,3}(?:-[A-Za-z0-9]+)?", token, re.IGNORECASE):
        return True
    if re.fullmatch(r"[A-Z]+-?\d{1,4}[A-Za-z0-9-]*", token, re.IGNORECASE):
        return True
    return bool(re.fullmatch(r"\d{1,2}\.\d", token))


def _clean_fire_rating(value: object) -> Optional[str]:
    token = str(value or "").strip()
    if not token:
        return None
    return token if re.search(r"\b(?:MIN|HR|HOUR)\b", token, re.IGNORECASE) else None


def _extract_hardware_set_from_tail(tail: List[Optional[str]]) -> Optional[str]:
    """
    Find the hardware set in a door row without confusing it with frame type.

    In the canonical schedule layout the hardware set appears after the three
    detail columns and the fire-rating column. In flattened rows, it is often
    the number immediately after the last detail reference or fire rating.
    """
    if len(tail) > 16 and _clean_fire_rating(tail[15]) and _looks_like_hardware_set_token(tail[16]):
        return str(tail[16]).strip()
    if len(tail) > 15 and _looks_like_hardware_set_token(tail[15]):
        return str(tail[15]).strip()
    if len(tail) > 16 and _looks_like_hardware_set_token(tail[16]):
        return str(tail[16]).strip()

    for idx, cell in enumerate(tail):
        text = str(cell or "").strip()
        match = re.search(r"\b(?:\d+\s*(?:MIN|HR)|\d+\s*HOUR)\.?\s+([A-Z]?\d{1,2}[A-Za-z]?)\b", text, re.IGNORECASE)
        if match:
            return match.group(1)
        if re.fullmatch(r"[A-Z]\d+(?:\.\d+)?/\d+", text, re.IGNORECASE):
            for later in tail[idx + 1: idx + 5]:
                if _looks_like_hardware_set_token(later):
                    return str(later).strip()

    candidates = [str(cell or "").strip() for cell in tail if _looks_like_hardware_set_token(cell)]
    return candidates[-1] if candidates else None


def _parse_compact_door_table_rows(text: str) -> List[dict]:
    """
    Parse compact schedules shaped like:
    NO | TYPE | SIZE | FRAME | HDWR

    These appear on smaller tenant sheets and should not be interpreted as the
    wider from/to/material/finish/detail schedule.
    """
    doors: List[dict] = []
    in_structured_source = False

    for line in text.splitlines():
        if line.startswith("[Source: "):
            in_structured_source = line.strip() in {"[Source: pdfplumber_tables]", "[Source: pdfplumber_rows]"}
            continue
        if not in_structured_source:
            continue

        cells = _split_markdown_row(line)
        if len(cells) < 5:
            continue

        parsed_tail = None
        door_number = None
        embedded_note = None
        for idx, cell in enumerate(cells):
            candidate, note = _normalize_door_mark_cell(cell)
            if not candidate:
                candidate, note = _extract_leading_door_mark(cell)
            if not candidate:
                continue
            tail = cells[idx:]
            if len(tail) >= 5 and _split_combined_dimensions(tail[2]):
                parsed_tail = tail
                door_number = candidate
                embedded_note = note
                break
        if not parsed_tail or not door_number:
            continue

        dims = _split_combined_dimensions(parsed_tail[2])
        if not dims:
            continue

        hardware_raw = str(parsed_tail[4] or "").strip()
        hardware_set = None
        explicit_no_hardware = False
        hw_match = re.fullmatch(r"HW[\s#.-]*(.+)", hardware_raw, flags=re.IGNORECASE)
        if hw_match:
            candidate = hw_match.group(1).strip()
            hardware_set = candidate if _looks_like_hardware_set_token(candidate) else None
        elif hardware_raw.upper() in {"E", "EXIST", "EXISTING", "EXISTING TO REMAIN"}:
            explicit_no_hardware = True
        elif _looks_like_hardware_set_token(hardware_raw):
            hardware_set = hardware_raw

        door = {
            "door_number": door_number,
            "door_type": str(parsed_tail[1] or "").strip() or None,
            "door_width": dims[0],
            "door_height": dims[1],
            "frame_type": str(parsed_tail[3] or "").strip() or None,
            "frame_material": str(parsed_tail[3] or "").strip() or None,
            "hardware_set": hardware_set,
            "remarks": embedded_note or (str(parsed_tail[5] or "").strip() if len(parsed_tail) > 5 else None),
            "_table_shape": "compact",
            "_hardware_set_explicit_blank": explicit_no_hardware,
            "is_pair": bool(str(dims[0]).startswith(("6'", "7'", "8'"))),
            "door_leaves": 2 if str(dims[0]).startswith(("6'", "7'", "8'")) else 1,
        }
        doors.append({k: v for k, v in door.items() if v not in (None, "")})

    return _drop_self_referential_hardware_sets(_dedupe_doors_by_number(doors))


def _parse_formal_door_table_rows(text: str) -> List[dict]:
    """Parse clean rows from the explicit pdfplumber table block."""
    compact_doors = _parse_compact_door_table_rows(text)
    if len(compact_doors) >= 3:
        return compact_doors

    doors: List[dict] = []
    in_pdfplumber_tables = False

    for line in text.splitlines():
        if line.startswith("[Source: "):
            in_pdfplumber_tables = line.strip() == "[Source: pdfplumber_tables]"
            continue
        if not in_pdfplumber_tables:
            continue

        cells = _split_markdown_row(line)
        if len(cells) < 17:
            continue

        mark_idx, door_number, keyed_note = _find_best_door_mark_index(cells)
        if mark_idx is None or not door_number:
            continue

        tail = cells[mark_idx:]
        if len(tail) < 17 or not (_is_dimension(tail[3]) and _is_dimension(tail[4])):
            continue

        hardware_set = _extract_hardware_set_from_tail(tail) if len(tail) > 15 else None
        details = " / ".join(str(v) for v in tail[12:15] if v)
        remarks = tail[17] if len(tail) > 17 else None
        door_width = tail[3]

        door = {
            "door_number": door_number,
            "from_room": tail[1],
            "room_name": tail[2],
            "door_width": door_width,
            "door_height": tail[4],
            "door_thickness": tail[5],
            "door_material": tail[6],
            "door_type": tail[7],
            "door_finish": tail[8],
            "frame_material": tail[9],
            "frame_type": tail[10],
            "frame_finish": tail[11],
            "head_jamb_sill_detail": details or None,
            "fire_rating": _clean_fire_rating(tail[15]),
            "hardware_set": hardware_set,
            "remarks": remarks,
            "keyed_notes": keyed_note,
            "_table_shape": "formal",
            "is_pair": bool(door_width and str(door_width).strip().startswith(("6'", "7'", "8'"))),
            "door_leaves": 2 if door_width and str(door_width).strip().startswith(("6'", "7'", "8'")) else 1,
        }
        doors.append({k: v for k, v in door.items() if v not in (None, "")})

    return _drop_self_referential_hardware_sets(_dedupe_doors_by_number(doors))


def _parse_packed_dimension_door_rows(text: str) -> List[dict]:
    """
    Parse sheets where width, height, thickness and type are packed into one
    pipe cell instead of separate table columns.
    """
    rows: List[dict] = []
    status_words = {"NEW", "EXISTING", "EXIST", "EXISTING TO REMAIN"}

    for line in text.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 7:
            continue
        door_number = str(cells[0] or "").strip()
        if not (
            _looks_like_door_mark(door_number)
            or (
                re.fullmatch(r"\d{1,4}[A-Z]?", door_number, re.IGNORECASE)
                and not (1900 <= int(re.match(r"\d+", door_number).group()) <= 2099)
            )
        ):
            continue

        dim_idx = None
        dims: List[str] = []
        for idx, cell in enumerate(cells[2:7], 2):
            dims = _find_dimensions(cell)
            if len(dims) >= 2:
                dim_idx = idx
                break
        if dim_idx is None:
            continue

        room_name = str(cells[1] or "").strip() or None
        if room_name:
            room_name = re.sub(r"\s+(?:NEW|EXISTING|EXIST)\s*$", "", room_name, flags=re.IGNORECASE).strip() or room_name

        dim_cell = str(cells[dim_idx] or "")
        after_dims = dim_cell
        for dim in dims:
            after_dims = after_dims.replace(dim, " ")
        door_type = re.sub(r"\s+", " ", after_dims).strip(" -") or None

        hardware_set = None
        for cell in cells[dim_idx + 1: dim_idx + 8]:
            token = str(cell or "").strip()
            if not token or token.upper() in status_words:
                continue
            if "," in token or _is_dimension(token):
                continue
            match = re.search(r"(?:^|\s)([A-Z]?\d{1,3}[A-Z]?|\d{1,2}\.\d)\s*$", token, re.IGNORECASE)
            if match and _looks_like_hardware_set_token(match.group(1)):
                hardware_set = match.group(1)

        door_width = dims[0]
        door_height = dims[1]
        row = {
            "door_number": door_number,
            "room_name": room_name,
            "door_width": door_width,
            "door_height": door_height,
            "door_thickness": dims[2] if len(dims) > 2 else None,
            "door_type": door_type,
            "hardware_set": hardware_set,
            "_table_shape": "packed_dimension",
            "is_pair": bool(str(door_width).strip().startswith(("6'", "7'", "8'"))),
            "door_leaves": 2 if str(door_width).strip().startswith(("6'", "7'", "8'")) else 1,
        }
        rows.append({k: v for k, v in row.items() if v not in (None, "")})

    return _drop_self_referential_hardware_sets(_dedupe_doors_by_number(rows))


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
            match = re.search(r"\b(?:HW|HDWR|HARDWARE)\s*[-#:]?\s*([A-Z0-9.-]+)\b", str(value or ""), re.IGNORECASE)
            if match and _looks_like_hardware_set_token(match.group(1)):
                hardware_set = match.group(1)
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

    return _drop_self_referential_hardware_sets(_dedupe_doors_by_number(doors))


def _parse_opening_list_fallback(text: str) -> List[dict]:
    """
    Recover vendor "Opening List" pages that map openings to hardware sets.

    These pages often have no physical dimensions, so the normal door-table
    fallback intentionally ignores them. They are still valuable because they
    carry the door-to-hardware join.
    """
    upper = (text or "").upper()
    if "OPENING LIST" not in upper or not any(token in upper for token in ("HDW SET", "HDWR SET", "HDWE SET", "HARDWARE SET")):
        return []

    doors: List[dict] = []
    for line in text.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 2:
            continue

        door_number = str(cells[0] or "").strip()
        hardware_set = str(cells[1] or "").strip()
        if not _looks_like_door_mark(door_number):
            continue
        if not _looks_like_hardware_set_token(hardware_set):
            continue

        row = {
            "door_number": door_number,
            "hardware_set": hardware_set,
            "_table_shape": "opening_list",
            "is_pair": False,
            "door_leaves": 1,
        }
        if len(cells) >= 4:
            row["door_type"] = str(cells[-2] or "").strip() or None
            row["frame_type"] = str(cells[-1] or "").strip() or None
        elif len(cells) == 3:
            row["door_type"] = str(cells[2] or "").strip() or None
        doors.append({k: v for k, v in row.items() if v not in (None, "")})

    return _dedupe_doors_by_number(doors)


def _is_bad_room_name(value: object) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    upper = re.sub(r"\s+", " ", token.upper()).strip(" .:-")
    if _looks_like_combined_dimensions(token) or _is_dimension(token):
        return True
    return upper in {"ELECTRICAL COMPONENTS", "PARTITION GENERAL NOTES", "DOOR GENERAL NOTES"}


def _merge_trusted_table_fields(doors: List[dict], parsed_doors: List[dict]) -> int:
    trusted = {
        str(row.get("door_number") or "").strip().upper(): row
        for row in parsed_doors
        if row.get("_table_shape") in {"compact", "formal"}
    }
    if not trusted:
        return 0

    changed = 0
    for door in doors:
        key = str(door.get("door_number") or "").strip().upper()
        parsed = trusted.get(key)
        if not parsed:
            if _is_bad_room_name(door.get("room_name")):
                door.pop("room_name", None)
                changed += 1
            continue

        if _is_bad_room_name(door.get("room_name")):
            door.pop("room_name", None)
            changed += 1

        for field in ("door_width", "door_height", "door_type", "frame_type", "frame_material"):
            value = parsed.get(field)
            if value and door.get(field) != value:
                door[field] = value
                changed += 1

        parsed_hw = parsed.get("hardware_set")
        current_hw = str(door.get("hardware_set") or "").strip().upper()
        if parsed_hw and door.get("hardware_set") != parsed_hw:
            door["hardware_set"] = parsed_hw
            changed += 1
        elif parsed.get("_hardware_set_explicit_blank") and current_hw in {"E", "EXIST", "EXISTING"}:
            door.pop("hardware_set", None)
            changed += 1

    return changed


def _parse_door_table_fallback(text: str) -> List[dict]:
    """
    Deterministic fallback for dense pdfplumber markdown door schedules.

    It intentionally handles only rows with a clear door mark plus width/height
    dimensions, so note blocks and hardware component lists are ignored.
    """
    formal_doors = _parse_formal_door_table_rows(text)
    if len(formal_doors) >= 3:
        return formal_doors
    opening_doors = _parse_opening_list_fallback(text)
    if len(opening_doors) >= 3:
        return opening_doors
    packed_doors = _parse_packed_dimension_door_rows(text)
    if len(packed_doors) >= 3:
        return packed_doors

    doors: List[dict] = []
    dim_re = re.compile(r"\d+\s*['\u2019]\s*-\s*\d+(?:\s+\d+/\d+)?\s*\"")

    for line in text.splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 4:
            continue

        mark_idx, normalized_mark, keyed_note = _find_best_door_mark_index(cells)
        if mark_idx is None or not normalized_mark:
            continue

        # Skip if row looks like a hardware component row to prevent false matching hinge sizes as door dimensions
        row_text = " ".join(str(c or "") for c in cells).upper()
        if any(term in row_text for term in ("HINGE", "LOCK", "CLOSER", "KICKPLATE", "KICK PLATE", "SWEEP", "THRESHOLD", "SILENCER")):
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
        if normalized_mark:
            door_number = normalized_mark
        door_width = dims[0]
        door_height = dims[1]
        door_thickness = dims[2] if len(dims) > 2 else get(5)
        hardware_set = _extract_hardware_set_from_tail(tail) if len(tail) > 15 else None

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
            "keyed_notes": keyed_note,
            "is_pair": bool(door_width and str(door_width).strip().startswith("6'")),
            "door_leaves": 2 if door_width and str(door_width).strip().startswith("6'") else 1,
        }
        doors.append({k: v for k, v in door.items() if v not in (None, "")})

    if len(doors) < 3:
        for line in text.splitlines():
            cells = _split_markdown_row(line)
            if len(cells) < 4:
                continue
            # Skip if row looks like a hardware component row to prevent false matching hinge sizes as door dimensions
            row_text = " ".join(str(c or "") for c in cells).upper()
            if any(term in row_text for term in ("HINGE", "LOCK", "CLOSER", "KICKPLATE", "KICK PLATE", "SWEEP", "THRESHOLD", "SILENCER")):
                continue
            door_number, embedded_room = _extract_door_mark_and_room(cells[0])
            if not door_number:
                continue
            dim_pair = next((pair for cell in cells if (pair := _split_combined_dimensions(cell))), None)
            if not dim_pair:
                continue
            room_name = embedded_room or str(cells[1] or "").strip() or None
            hardware_set = None
            for value in cells[3:]:
                match = re.search(r"\b(?:HW|HDWR|HARDWARE)\s*[-#:]?\s*([A-Z0-9.-]+)\b", str(value or ""), re.IGNORECASE)
                if match and _looks_like_hardware_set_token(match.group(1)):
                    hardware_set = match.group(1)
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
    return _drop_self_referential_hardware_sets(merged)


_VENDOR_HW_COMPONENT_TERMS = (
    "HINGE",
    "EXIT",
    "EXIT DEVICE",
    "CYLINDER",
    "CORE",
    "PULL",
    "CLOSER",
    "CONTINUOUS HINGE",
    "KICK PLATE",
    "ARMOR PLATE",
    "MOP PLATE",
    "PUSH PLATE",
    "THRESHOLD",
    "WEATHERSTRIP",
    "SEAL",
    "GASKET",
    "DOOR BOTTOM",
    "ASTRAGAL",
    "GASKETING",
    "SWEEP",
    "RAIN GUARD",
    "LOCKSET",
    "LEVERSET",
    "DEADLOCK",
    "DEADBOLT",
    "FLUSH BOLT",
    "FLUSH PULL",
    "HEADER BOLT",
    "THRESHOLD BOLT",
    "OVERHEAD HOLDER",
    "SILENCER",
    "STRIKE",
    "DUST PROOF STRIKE",
    "ELECTRIC STRIKE",
    "POWER TRANSFER",
    "HARNESS",
    "CARD READER",
    "POWER SUPPLY",
    "POINT-TO-POINT",
    "ELEVATION DIAGRAM",
    "RISER DIAGRAM",
    "COORDINATOR",
    "WALL BUMPER",
    "FLOOR STOP",
    "DOOR STOP",
    "LATCH PROTECTOR",
    "HOLDER",
    "VIEWER",
    "STOP",
)

_VENDOR_HW_MFR_CODES = {
    "CKN", "FL", "GL", "HA", "LO", "NO", "PE", "SC", "TR",
    "IVE", "LCN", "NGP", "SCH", "VON",
}


def _looks_like_vendor_hw_component(description: str) -> bool:
    upper = str(description or "").upper()
    return any(term in upper for term in _VENDOR_HW_COMPONENT_TERMS)


def _is_vendor_hw_set_header(token: str) -> Optional[re.Match]:
    return re.match(r"(?i)^\s*SET\s*#?\s*([A-Z0-9.-]+)\s*(?:[-:]\s*(.+))?$", token or "")


def _is_vendor_hw_component_start(token: str) -> Optional[re.Match]:
    match = re.match(
        r"^\s*\(?(\d+(?:-\d+/\d+)?|LOT)\)?\s+(?:(EA|EACH|SET|PR|PAIR)\s+)?(.+?)\s*$",
        token or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    if not _looks_like_vendor_hw_component(match.group(3)):
        return None
    return match


def _is_finish_code(token: str) -> bool:
    upper = str(token or "").strip().upper()
    if not upper:
        return False
    if "," in upper:
        return all(_is_finish_code(part) for part in re.split(r"\s*,\s*", upper) if part)
    if re.fullmatch(r"(?:US)?\d{3}[A-Z]{0,2}", upper):
        return True
    if re.fullmatch(r"(?:US)?\d{2}[A-Z]{1,2}", upper):
        return True
    if re.fullmatch(r"(?:US)?[A-Z]{2}\d{2,4}[A-Z]?", upper):
        return True
    return False


def _split_finish_manufacturer_token(token: str) -> tuple[Optional[str], Optional[str]]:
    parts = str(token or "").strip().split()
    if len(parts) < 2:
        return None, None
    manufacturer = parts[-1].upper()
    finish = " ".join(parts[:-1]).strip().upper()
    if manufacturer in _VENDOR_HW_MFR_CODES and _is_finish_code(finish):
        return finish, manufacturer
    return None, None


def _parse_vendor_hardware_sets_fallback(text: str) -> List[dict]:
    """
    Deterministic parser for vendor-generated hardware schedules laid out as:
    Set #100 - name | 4 Hinge | BB1279 ... | US10B | HA | ...
    """
    if not re.search(r"(?i)\bSET\s*#?\s*[A-Z0-9.-]+\b", text or ""):
        return []

    tokens = [
        re.sub(r"\s+", " ", token).strip()
        for token in re.split(r"\s*\|\s*|\r?\n+", text or "")
        if re.sub(r"\s+", " ", token).strip()
    ]
    rows: list[dict] = []
    current_set_id: Optional[str] = None
    current_set_name: Optional[str] = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        set_match = _is_vendor_hw_set_header(token)
        if set_match:
            current_set_id = set_match.group(1).strip()
            current_set_name = (set_match.group(2) or "").strip() or None
            i += 1
            continue

        component_match = _is_vendor_hw_component_start(token)
        if not current_set_id or not component_match:
            i += 1
            continue

        qty_raw = component_match.group(1).strip()
        unit_raw = (component_match.group(2) or "EA").strip().upper()
        description = component_match.group(3).strip()
        row = {
            "hardware_set_id": current_set_id,
            "hardware_set_name": current_set_name,
            "qty": qty_raw if qty_raw.isdigit() else None,
            "qty_raw": qty_raw,
            "unit": "PAIR" if unit_raw == "PR" else unit_raw,
            "description": description,
        }

        extras: list[str] = []
        j = i + 1
        while j < len(tokens) and len(extras) < 4:
            nxt = tokens[j]
            if _is_vendor_hw_set_header(nxt) or _is_vendor_hw_component_start(nxt):
                break
            if nxt.upper().startswith("NOTE"):
                break
            extras.append(nxt)
            j += 1

        catalog_assigned = False
        for extra in extras:
            upper = extra.upper().strip()
            combined_finish, combined_mfr = _split_finish_manufacturer_token(extra)
            if combined_finish and row.get("catalog_number"):
                if not row.get("finish_code"):
                    row["finish_code"] = combined_finish
                if combined_mfr and not row.get("manufacturer_code"):
                    row["manufacturer_code"] = combined_mfr
            elif upper in _VENDOR_HW_MFR_CODES and not row.get("manufacturer_code"):
                row["manufacturer_code"] = upper
            elif not row.get("catalog_number"):
                row["catalog_number"] = extra
                catalog_assigned = True
            elif _is_finish_code(upper) and not row.get("finish_code"):
                row["finish_code"] = upper
            else:
                row.setdefault("extra_fields", {})[f"extra_{len(row.get('extra_fields', {})) + 1}"] = extra

        if catalog_assigned and not row.get("finish_code"):
            extras_fields = row.get("extra_fields") or {}
            for key, value in list(extras_fields.items()):
                if _is_finish_code(value):
                    row["finish_code"] = value
                    extras_fields.pop(key, None)
                    break
            if not extras_fields:
                row.pop("extra_fields", None)

        rows.append(row)
        i = max(j, i + 1)

    has_schedule_title = re.search(
        r"(?i)\b(?:DOOR\s+HARDWARE\s+SCHEDULE|HARDWARE\s+SETS?|HARDWARE\s+GROUPS?)\b",
        text or "",
    )
    return normalize_hardware_rows(rows) if len(rows) >= 3 or (rows and has_schedule_title) else []


def _grid_hw_set_header(token: str) -> Optional[str]:
    match = re.search(r"(?i)\bSET\s*[:#]?\s*([A-Z0-9.]+)\b", token or "")
    if not match:
        return None
    return match.group(1).strip().rstrip(".")


def _hardware_group_no_header(token: str) -> Optional[str]:
    match = re.search(r"(?i)\bHARDWARE\s+GROUP\s+NO\.?\s*([A-Z0-9.]+)\b", token or "")
    if not match:
        return None
    return match.group(1).strip().rstrip(".")


def _parse_grid_hw_component(token: str) -> Optional[dict]:
    clean = re.sub(r"\s+", " ", str(token or "")).strip(" .")
    match = re.match(
        r"(?i)^(\d+(?:-\d+/\d+)?)\s*(?:(EA|EACH|SET|PR|PAIR)\.?)?\s+(.+?)$",
        clean,
    )
    if not match:
        return None
    qty_raw = match.group(1).strip()
    unit_raw = (match.group(2) or "EA").strip().upper()
    description = match.group(3).strip(" .")
    if not _looks_like_vendor_hw_component(description):
        return None
    upper_description = description.upper()
    strong_terms = (
        "HINGE", "EXIT", "CLOSER", "LOCK", "DEAD", "STRIKE", "THRESHOLD",
        "WEATHER", "SEAL", "GASKET", "SWEEP", "STOP", "PULL", "BOLT",
        "HARNESS", "READER", "POWER", "SILENCER", "PLATE",
    )
    if re.search(r"\d+\s*['\u2019]\s*-\s*\d+|\d+/\d+\"", description) and not any(
        term in upper_description for term in strong_terms
    ):
        return None
    return {
        "qty": qty_raw if qty_raw.isdigit() else None,
        "qty_raw": qty_raw,
        "unit": "PAIR" if unit_raw == "PR" else unit_raw,
        "description": description,
    }


def _parse_grid_hardware_sets_fallback(text: str) -> List[dict]:
    """
    Recover architectural-sheet hardware schedules laid out in grid columns:
    ``SET: 1.0 | SET: 4.0`` followed by component rows per column.
    """
    if not re.search(r"(?i)\b(?:HARDWARE\s+SCHEDULE|SET\s*:\s*[A-Z0-9.]+)\b", text or ""):
        return []

    rows: list[dict] = []
    set_by_col: dict[int, str] = {}
    current_set_id: Optional[str] = None
    in_hardware_section = False

    for line in (text or "").splitlines():
        upper_line = line.upper()
        cells = _split_markdown_row(line) or [line.strip()]
        if "HARDWARE SCHEDULE" in upper_line or "HARDWARE SET" in upper_line:
            in_hardware_section = True
        if not in_hardware_section and any(_grid_hw_set_header(str(cell or "")) for cell in cells):
            in_hardware_section = True
        if not in_hardware_section:
            continue

        for col_idx, cell in enumerate(cells):
            token = str(cell or "").strip()
            if not token:
                continue

            set_id = _grid_hw_set_header(token)
            if set_id:
                set_by_col[col_idx] = set_id
                current_set_id = set_id
                continue

            component = _parse_grid_hw_component(token)
            if not component:
                continue
            component_set_id = set_by_col.get(col_idx) or current_set_id
            if not component_set_id:
                continue
            row = {"hardware_set_id": component_set_id, **component}
            rows.append(row)

    return normalize_hardware_rows(rows) if len(rows) >= 3 else []


def _parse_hardware_group_columns_fallback(text: str) -> List[dict]:
    """
    Recover dense architectural sheets with side-by-side ``Hardware Group No.``
    columns. Each active group uses three cells: component, catalog, finish/mfr.
    """
    if not re.search(r"(?i)\bHARDWARE\s+GROUP\s+NO\.?\s*[A-Z0-9.]+\b", text or ""):
        return []

    rows: list[dict] = []
    active_groups: list[str] = []
    for line in (text or "").splitlines():
        cells = _split_markdown_row(line)
        if not cells:
            continue

        group_ids = [_hardware_group_no_header(str(cell or "")) for cell in cells]
        group_ids = [group_id for group_id in group_ids if group_id]
        if group_ids:
            active_groups = group_ids
            continue
        if not active_groups:
            continue
        if len(cells) < len(active_groups) * 3:
            continue

        for group_idx, group_id in enumerate(active_groups):
            base = group_idx * 3
            if base >= len(cells):
                continue
            component = _parse_grid_hw_component(str(cells[base] or ""))
            if not component:
                continue
            row = {"hardware_set_id": group_id, **component}
            if base + 1 < len(cells):
                catalog = str(cells[base + 1] or "").strip()
                if catalog:
                    row["catalog_number"] = catalog
            if base + 2 < len(cells):
                finish_mfr = str(cells[base + 2] or "").strip()
                finish, manufacturer = _split_finish_manufacturer_token(finish_mfr)
                if finish:
                    row["finish_code"] = finish
                if manufacturer:
                    row["manufacturer_code"] = manufacturer
                elif finish_mfr:
                    row["finish_code"] = finish_mfr
            rows.append(row)

    return normalize_hardware_rows(rows) if len(rows) >= 3 else []


def _parse_deterministic_hardware_sets_fallback(text: str) -> List[dict]:
    group_rows = _parse_hardware_group_columns_fallback(text)
    grid_rows = _parse_grid_hardware_sets_fallback(text)
    vendor_rows = _parse_vendor_hardware_sets_fallback(text)
    if group_rows and len(group_rows) >= max(len(grid_rows), len(vendor_rows)):
        return group_rows
    if re.search(r"(?i)\bSET\s*:\s*[A-Z0-9.]+\b", text or "") and grid_rows:
        return grid_rows
    return grid_rows if len(grid_rows) > len(vendor_rows) else vendor_rows


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
    explicit_door_schedule = re.search(
        r"(?i)\b(?:DOOR\s+(?:AND\s+WINDOW\s+)?SCHEDULE|OPENING\s+LIST)\b",
        raw_text,
    ) is not None
    hardware_only_title = (
        re.search(r"(?i)\b(?:DOOR\s+HARDWARE\s+(?:SETS?|SCHEDULE)|HARDWARE\s+SETS?)\b", raw_text) is not None
        and not explicit_door_schedule
    )
    preparsed_full_hardware: List[dict] = []
    if (
        len(raw_text) > 1000
        and (page_type in (PageType.HARDWARE_SET, PageType.MIXED) or evidence.is_hardware_schedule)
    ):
        parsed = _parse_deterministic_hardware_sets_fallback(raw_text)
        if len(parsed) >= 8:
            preparsed_full_hardware = parsed
            logger.info(
                "Deterministic full-page hardware fallback recovered %d components before chunk LLM.",
                len(preparsed_full_hardware),
            )

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
        if page_type in (PageType.DOOR_SCHEDULE, PageType.MIXED) and not hardware_only_title:
            deterministic_door_source = None
            doors = _parse_opening_list_fallback(text)
            if doors:
                deterministic_door_source = "opening-list"
            elif len(text) > 9000 and evidence.is_door_schedule:
                dense_doors = _parse_door_table_fallback(text)
                dense_physical = _physical_door_count(dense_doors)
                has_packed_rows = any(row.get("_table_shape") == "packed_dimension" for row in dense_doors)
                if dense_physical >= 8 or (has_packed_rows and dense_physical >= 3):
                    doors = dense_doors
                    deterministic_door_source = "dense door-table"
            if deterministic_door_source:
                logger.info(
                    "Deterministic %s fallback recovered %d door rows.",
                    deterministic_door_source,
                    len(doors),
                )
            else:
                skip_native_door_llm = (
                    "VISION_CROP_RESCUE" in (text or "").upper()
                    and any((crop.get("crop_type") in ("door", "mixed")) for crop in (crop_candidates or []))
                )
                if skip_native_door_llm:
                    logger.info("Skipping native door LLM on crop-only page; relying on high-resolution crop rescue.")
                    doors = []
                else:
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
            has_hw_sets = has_hw_sets or bool(re.search(r"(?i)\bSET\s*:\s*[A-Z0-9.]+\b", text))
            has_components = len(re.findall(r"(?:HINGE|CLOSER|LOCK|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP)", text.upper())) >= 2
            if has_hw_sets and has_components:
                force_hardware = True
        elif page_type == PageType.MIXED:
            if re.search(r"(?i)\bSET\s*:\s*[A-Z0-9.]+\b", text) and evidence.hw_components >= 2:
                force_hardware = True

        should_extract_hardware = (
            force_hardware
            or page_type == PageType.HARDWARE_SET
            or (page_type == PageType.MIXED and evidence.is_hardware_schedule)
        )

        if should_extract_hardware:
            hw_chunks = []
            hardware = [] if preparsed_full_hardware else _parse_deterministic_hardware_sets_fallback(text)
            used_deterministic_hardware = bool(hardware)
            skip_native_hardware_llm = (
                (bool(preparsed_full_hardware) or not hardware)
                and page_type == PageType.HARDWARE_SET
                and evidence.hw_components < 2
                and any((crop.get("crop_type") in ("hardware", "mixed")) for crop in (crop_candidates or []))
            )
            if preparsed_full_hardware:
                used_deterministic_hardware = True
                skip_native_hardware_llm = True
            if hardware:
                logger.info("Deterministic hardware fallback recovered %d components.", len(hardware))
            elif preparsed_full_hardware:
                logger.info("Skipping chunk hardware LLM; using deterministic full-page hardware rows.")
            elif skip_native_hardware_llm:
                logger.info("Skipping native hardware LLM on low-text hardware page; relying on crop rescue.")
            else:
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
            if (
                not used_deterministic_hardware
                and not skip_native_hardware_llm
                and (not hardware or is_missing_sets or (len(hardware) < 5 and len(text) > 5000))
                and retry_with_hint
                and len(text) > 200
            ):
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
    if preparsed_full_hardware and not all_hardware:
        all_hardware = preparsed_full_hardware
        ctx.update_from_hardware(all_hardware)

    hw_marker_count = len(re.findall(
        r"(?i)\b(?:HARDWARE\s+SET|SET\s*(?:NO\.?|#)?\s*[\w\d.-]+|GROUP\s*(?:NO\.?|#)?\s*[\w\d.-]+)\b",
        raw_text,
    ))
    hw_component_count = len(re.findall(
        r"(?i)\b(?:HINGE|CLOSER|LOCKSET|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP|STOP|SEAL|GASKET|EXIT\s+DEVICE)\b",
        raw_text,
    ))
    if len(all_hardware) == 0:
        parsed_full_hw = _parse_deterministic_hardware_sets_fallback(raw_text)
        if parsed_full_hw:
            logger.warning(
                "Deterministic full-page hardware fallback recovered %d rows before LLM rescue.",
                len(parsed_full_hw),
            )
            all_hardware = parsed_full_hw
            ctx.update_from_hardware(all_hardware)

    if (
        len(all_hardware) == 0
        and hw_marker_count >= 3
        and hw_component_count >= 5
        and len(raw_text) > 1000
        and (evidence.is_hardware_schedule or page_type == PageType.HARDWARE_SET)
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
        and not hardware_only_title
        and page_type != PageType.HARDWARE_SET
        and (page_type in (PageType.DOOR_SCHEDULE, PageType.MIXED) or not evidence.is_hardware_schedule)
    ):
        parsed_doors = _parse_door_table_fallback(raw_text)
        if parsed_doors:
            logger.warning(
                "Deterministic door table fallback recovered %d rows before evidence-driven LLM rescue.",
                len(parsed_doors),
            )
            all_doors = _dedupe_doors_by_number(all_doors + parsed_doors)
            ctx.update_from_doors(all_doors)
        else:
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

    # ── Full-page door rescue for door/window schedule markup pages ──
    # Some vector markup pages expose "DOOR/WINDOW SCHEDULE" text and visible
    # hardware/profile rows, but the standard door prompt returns [] because
    # labels are short numeric profile marks rather than room doors. A final
    # door-only rescue is justified when we already found hardware but no doors.
    if (
        len(all_doors) == 0
        and len(all_hardware) > 0
        and page_type != PageType.HARDWARE_SET
        and explicit_door_schedule
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
    if all_doors:
        parsed_table_doors = _parse_door_table_fallback(raw_text)
        merged_fields = _merge_trusted_table_fields(all_doors, parsed_table_doors)
        if merged_fields:
            logger.info("Merged %d trusted deterministic door-table fields into LLM rows.", merged_fields)

    physical_count = _physical_door_count(all_doors)
    should_try_fallback = (
        page_type != PageType.HARDWARE_SET
        and
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
