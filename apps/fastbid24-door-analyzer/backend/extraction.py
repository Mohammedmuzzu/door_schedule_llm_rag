import base64
import http.client
import json
import random
import re
import time
import urllib.error
import urllib.request
from typing import Any

from config import settings
from hardware_rescue import detect_hardware_crops, extract_pdf_text


class ExtractionError(Exception):
    pass


class ExtractionProviderError(ExtractionError):
    def __init__(self, public_message: str, raw_message: str = ""):
        super().__init__(public_message)
        self.raw_message = raw_message


STAGED_DOOR_SYSTEM = """You are extracting a door schedule from a construction drawing.

Return structured JSON only.

First, capture project-level header information from any cover sheet, title block, or schedule header visible in the drawing:
- project_name
- architect

Also capture, if visible anywhere on the door-schedule sheet(s):
- general_notes: array of free-text notes adjacent to or above the door schedule. Include sheet-level "General Notes", "Door Schedule Notes", "Door Notes", finish notes, "see drawings for X" callouts, alternates, allowances, and scope statements that affect Division 8. One string per logical note. Preserve text verbatim.
- schedule_legend: object mapping each abbreviation defined on the schedule (for example "CR", "EL", "DPS", "RX", "AO", "EH") to its expanded meaning verbatim from the legend panel. Empty object if no legend is visible.
- keying_notes: array of any keying-related instructions visible on the door-schedule sheet (master/sub-master structure, keyway, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, etc.). Verbatim. Empty array if none.

Then extract every visible door schedule row.

For each door, capture:
- mark
- room_or_location
- width
- height
- thickness
- door_type
- door_material
- door_finish
- frame_type
- frame_material
- frame_finish
- glazing
- fire_rating
- hardware_set
- closer
- electric_or_access_control
- remarks
- source_page
- source_crop_id
- confidence

Rules:
- Preserve text exactly as shown.
- Do not infer missing values.
- Use null if unclear.
- Do not complete missing door numbers.
- Do not assume hardware items from the hardware set name.
- Existing-to-remain doors must be marked as existing_to_remain.
- If the row is partially unclear, still extract visible fields and mark confidence below 0.75.
- For project_name and architect: read verbatim from the title block / cover sheet. Use null if not visible. Do not abbreviate or paraphrase.
- For general_notes, schedule_legend, and keying_notes: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent abbreviation meanings - only include legend entries that are explicitly defined on the sheet.

Return JSON only in this exact shape:
{ "project_name": string|null, "architect": string|null, "general_notes": [string], "schedule_legend": { [abbrev: string]: string }, "keying_notes": [string], "doors": [ { "mark": string|null, "room_or_location": string|null, "width": string|null, "height": string|null, "thickness": string|null, "door_type": string|null, "door_material": string|null, "door_finish": string|null, "frame_type": string|null, "frame_material": string|null, "frame_finish": string|null, "glazing": string|null, "fire_rating": string|null, "hardware_set": string|null, "closer": string|null, "electric_or_access_control": string|null, "remarks": string|null, "existing_to_remain": boolean, "source_page": number|string|null, "source_crop_id": string|null, "confidence": number } ] }"""


STAGED_HW_SYSTEM = """You are extracting hardware set descriptions from a construction drawing crop.

Return structured JSON only.

First, capture any sheet-level context visible alongside the hardware sets:
- hardware_preamble: array of free-text notes that appear above, beside, or below the hardware sets - for example "All hardware to comply with ANSI A156.x", manufacturer/finish standards, substitution rules, scope notes for electrified hardware, "EC to provide 120 V", etc. One string per logical note. Verbatim. Empty array if none.
- keying_notes: array of keying-related instructions visible on the hardware-set sheet(s) (master/sub-master structure, keyway brand, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, allowance counts, etc.). Verbatim. Empty array if none.
- hardware_legend: object mapping any abbreviations defined on the hardware sheet (for example "REX", "DPS", "EPT", "AO") to their expanded meanings. Empty object if no legend.

Then extract every visible hardware set or hardware group in this crop.

For each hardware set, capture:
- hardware_set
- set_title
- referenced_doors
- status: active / not_used / existing / void / review_required
- set_notes
- items

For each item, capture:
- item_seq
- qty
- unit
- description
- manufacturer
- model_or_catalog
- finish
- notes
- confidence

Rules:
- Extract item rows exactly as visible.
- Do not guess manufacturer or model.
- Do not merge multiple hardware sets.
- Do NOT emit the same hardware_set id more than once. If the same set appears across multiple pages or columns, combine its visible items into a single entry.
- Do NOT emit the same item line twice within a set. If the same item appears twice in the same set on the drawing, list it once.
- If text is unclear, return null and lower confidence.
- If a hardware set says NOT USED, mark status as not_used.
- If existing hardware is to remain, mark status as existing.
- Do not map doors in this step.
- Do not create RFIs in this step.
- For hardware_preamble, keying_notes, and hardware_legend: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent legend meanings.
- Return only the extracted hardware set JSON.

Return JSON only in this exact shape:
{ "hardware_preamble": [string], "keying_notes": [string], "hardware_legend": { [abbrev: string]: string }, "hardware_sets": [ { "hardware_set": string, "set_title": string|null, "referenced_doors": [string], "status": "active"|"not_used"|"existing"|"void"|"review_required", "set_notes": string|null, "items": [ { "item_seq": number|string|null, "qty": number|string|null, "unit": string|null, "description": string|null, "manufacturer": string|null, "model_or_catalog": string|null, "finish": string|null, "notes": string|null, "confidence": number } ] } ] }"""


STAGED_RFI_SYSTEM = """You are a senior doors, frames, and hardware estimator.

Review the extracted door schedule, hardware sets, door-to-hardware mapping, and any sheet-level context that was captured (general notes, schedule legend, keying notes, hardware preamble).

Use the sheet-level context as your source of truth for project-specific conventions:
- The schedule_legend / hardware_legend tells you what each abbreviation means for THIS project. Use those meanings - do not assume the industry-standard meaning if the project defines its own.
- The general_notes and hardware_preamble may explicitly include or exclude scope (for example "EC provides 120 V", "owner-supplied cylinders", "alternate #3 deletes hardware sets 9-12"). Reflect those in your RFIs and coordination notes - do not generate an RFI for something the notes already resolve.
- The keying_notes may already answer questions about keyway / master-key / construction cores. Skip RFIs the notes already answer.

Create RFIs and coordination notes only for real issues.

Flag:
- Missing hardware set
- Hardware set referenced but no item rows extracted
- Existing door with new hardware ambiguity
- Exterior door without threshold/weatherstrip/sweep
- Access control / card reader / electrified hardware
- Panic / egress hardware
- Double door missing pair hardware components
- Fire-rated or smoke-rated opening requiring verification
- Door remarks that conflict with hardware set
- Door type that does not match assigned hardware set
- Hardware set marked not used but referenced by door
- Storefront or aluminum entrance coordination

Return:
- severity
- category
- issue
- affected_doors
- recommendation

Return JSON only in this exact shape:
{ "rfis": [ { "severity": "low"|"medium"|"high", "category": string, "issue": string, "affected_doors": [string], "recommendation": string } ] }"""


def _log(logs: list[dict[str, Any]], kind: str, text: str, stage: str | None = None) -> None:
    logs.append({"kind": kind, "level": kind, "text": text, "message": text, "stage": stage, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})


def _openai_json_call(label: str, input_payload: list[dict[str, Any]], max_tokens: int, reasoning_effort: str, logs: list[dict[str, Any]], api_key: str | None = None) -> dict[str, Any]:
    resolved_api_key = api_key or settings.openai_api_key
    if not resolved_api_key:
        raise ExtractionError("Analysis service is not configured for this account.")
    started = time.time()
    body: dict[str, Any] = {
        "model": settings.openai_model,
        "input": input_payload,
        "reasoning": {"effort": reasoning_effort},
        "text": {"format": {"type": "json_object"}},
        "max_output_tokens": max_tokens,
    }

    def send(payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(3):
            req = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {resolved_api_key}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=900) as res:
                    return json.loads(res.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                try:
                    error_payload = json.loads(exc.read().decode("utf-8"))
                except Exception:
                    error_payload = {"error": {"message": f"Analysis service HTTP {exc.code}"}}
                raw_message = error_payload.get("error", {}).get("message") or f"Analysis service HTTP {exc.code}"
                if exc.code in {500, 502, 503, 504} and attempt < 2:
                    _log(logs, "warn", f"{label} - temporary service error, retrying.", label)
                    backoff = (2 ** (attempt + 1)) + random.uniform(0.5, 2.0)
                    time.sleep(backoff)
                    continue
                if exc.code in {401, 403}:
                    public_message = "Analysis service rejected this account key. Ask an admin to replace it."
                elif exc.code == 429:
                    public_message = "Analysis service is quota-limited or busy. Try again later."
                else:
                    public_message = f"Analysis service returned an error (HTTP {exc.code})."
                raise ExtractionProviderError(public_message, raw_message) from exc
            except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError) as exc:
                if attempt < 2:
                    _log(logs, "warn", f"{label} - network interruption, retrying.", label)
                    backoff = (2 ** (attempt + 1)) + random.uniform(0.5, 2.0)
                    time.sleep(backoff)
                    continue
                reason = getattr(exc, "reason", None) or str(exc)
                raise ExtractionError(f"Network error contacting analysis service: {reason}") from exc
        raise ExtractionError("Analysis service did not return a response.")

    _log(logs, "info", f"{label} - processing document data.", label)
    try:
        data = send(body)
    except ExtractionProviderError as exc:
        if re.search(r"reasoning|effort|parameter", exc.raw_message, re.I):
            _log(logs, "warn", f"{label} - retrying with simplified request.", label)
            body.pop("reasoning", None)
            data = send(body)
        else:
            raise

    text = data.get("output_text") or ""
    if not text and isinstance(data.get("output"), list):
        chunks: list[str] = []
        for item in data["output"]:
            for content in item.get("content") or []:
                if isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        text = "".join(chunks)
    text = text or "{}"
    truncated = (data.get("incomplete_details") or {}).get("reason") == "max_output_tokens"
    elapsed = round(time.time() - started)
    _log(logs, "ok", f"{label} - completed in {elapsed}s{' - truncated' if truncated else ''}.", label)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        last_brace = text.rfind("}")
        if last_brace <= 0:
            raise ExtractionError(f"{label}: invalid JSON")
        try:
            parsed = json.loads(text[: last_brace + 1])
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"{label}: invalid JSON") from exc
    return {"parsed": parsed, "elapsed": elapsed, "truncated": truncated}


def canonical_set_key(value: Any) -> str:
    s = clean_hardware_set_label(value)
    if not s:
        return ""
    s = _normalize_set_label_text(s)
    stripped = re.sub(r"^(hardware\s+group\s+(?:no\.?\s*)?|hardware\s+set\s*(?:#|no\.?)?\s*|hw\s*set\s*(?:#|no\.?)?\s*|set\s+(?:no\.?\s*)?|group\s+(?:no\.?\s*)?|fhw[-\s]?|hw[-\s]?|#)", "", s, flags=re.I)
    stripped = re.sub(r"\s+", " ", stripped).strip().upper()
    numeric = re.fullmatch(r"0*(\d+)(?:\.0+)?", stripped)
    if numeric:
        return numeric.group(1)
    dotted_numeric = re.fullmatch(r"\.(\d+)", stripped)
    if dotted_numeric:
        return dotted_numeric.group(1)
    if "|" in stripped:
        parts = sorted(_compact_set_key(part) for part in stripped.split("|") if _compact_set_key(part))
        if parts:
            return " | ".join(parts)
    return stripped or s.upper()


def clean_hardware_set_label(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    prefixes = [
        r"hardware\s+group\s+(?:no\.?\s*|#)?",
        r"hardware\s+set\s*(?:#|no\.?)?\s*",
        r"hw\s*set\s*(?:#|no\.?)?\s*",
        r"hw\s*group\s*(?:#|no\.?)?\s*",
        r"door\s+schedule\s+id\s*",
        r"door\s+schedule\s+set\s*",
        r"door\s+schedule\s+group\s*",
        r"door\s+schedule\s*",
        r"door\s+set\s*",
        r"door\s+group\s*",
        r"door\s+id\s*",
        r"opening\s+id\s*",
        r"opening\s+set\s*",
        r"opening\s+group\s*",
        r"opening\s+no\.?\s*",
        r"set\s+(?:no\.?\s*|#)?",
        r"group\s+(?:no\.?\s*|#)?",
        r"fhw[-\s]?",
        r"hw[-\s]?",
        r"#"
    ]
    pattern = "^(" + "|".join(prefixes) + ")"
    s = re.sub(pattern, "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"-{2,}", "-", s)
    numeric = re.fullmatch(r"(\d+)\.0+", s)
    if numeric:
        return numeric.group(1)
    dotted_numeric = re.fullmatch(r"\.(\d+)", s)
    if dotted_numeric:
        return dotted_numeric.group(1)
    return s


def is_placeholder_set_label(value: Any) -> bool:
    label = clean_hardware_set_label(value)
    if not label:
        return True
    compact = re.sub(r"[\s._:/\\|()-]+", "", label).upper()
    text = re.sub(r"\s+", " ", label).strip().upper()
    return (
        compact in {"", "-", "NA", "N/A", "NONE", "NULL", "NO", "NIC", "TBD", "VARIES", "EVARIES", "EXIST", "EXISTING"}
        or text in {"-", "--", "—", "<VARIES>", "(E)", "E", "DOOR HARDWARE", "HARDWARE", "HARDWARE SET", "HARDWARE SETS", "MANUF.", "MANUFACTURER", "TWO ACCESSORIES"}
    )


def _normalize_set_label_text(value: str) -> str:
    s = str(value or "").strip()
    s = re.sub(r"\bPASASAGE\b", "PASSAGE", s, flags=re.I)
    s = re.sub(r"\bw\s*/\s*", " ", s, flags=re.I)
    s = re.sub(r"\s*([|/])\s*", r" \1 ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _compact_set_key(value: str) -> str:
    s = _normalize_set_label_text(value).upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    numeric = re.fullmatch(r"0*(\d+)(?:\.0+)?", s)
    return numeric.group(1) if numeric else s


def alias_set_keys(value: Any) -> set[str]:
    label = clean_hardware_set_label(value)
    if not label:
        return set()
    normalized = _normalize_set_label_text(label)
    keys = {canonical_set_key(normalized)}
    for part in re.split(r"\s*[|/]\s*", normalized):
        part = part.strip()
        if len(part) >= 3 or part.isdigit():
            keys.add(canonical_set_key(part))
    loose_tokens = sorted(re.findall(r"[A-Z0-9]+", _normalize_set_label_text(normalized).upper()))
    if loose_tokens:
        keys.add(" ".join(loose_tokens))
    keys.discard("")
    return keys


def _build_set_lookup(sets: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    exact: dict[str, dict[str, Any]] = {}
    alias_candidates: dict[str, list[dict[str, Any]]] = {}
    for s in sets:
        key = canonical_set_key(s.get("hardware_set"))
        if key and key not in exact:
            exact[key] = s
        for alias in alias_set_keys(s.get("hardware_set")):
            alias_candidates.setdefault(alias, []).append(s)
    aliases: dict[str, dict[str, Any]] = {}
    for alias, candidates in alias_candidates.items():
        unique: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            unique[canonical_set_key(candidate.get("hardware_set"))] = candidate
        if len(unique) == 1:
            aliases[alias] = next(iter(unique.values()))
    return exact, aliases


def resolve_set(value: Any, exact: dict[str, dict[str, Any]], aliases: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = canonical_set_key(value)
    if not key:
        return None
    return exact.get(key) or aliases.get(key)


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if x]
    if value:
        return [str(value)]
    return []


def _can_fallback_after_error(exc: ExtractionError) -> bool:
    message = str(exc).lower()
    return not any(token in message for token in ("rejected this account key", "quota-limited", "not configured"))


def extract_pdf_text_markdown(file_bytes: bytes, filename: str = "document.pdf", max_chars: int = 45000) -> str:
    # 1. Try IBM Docling (visual AI layout-aware table parser)
    try:
        import tempfile
        import os
        from pathlib import Path
        from docling.document_converter import DocumentConverter

        suffix = ".pdf"
        if filename:
            ext = Path(filename).suffix
            if ext:
                suffix = ext

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            converter = DocumentConverter()
            result = converter.convert(tmp_path)
            if hasattr(result, "document") and hasattr(result.document, "export_to_markdown"):
                text = result.document.export_to_markdown()
            elif hasattr(result, "export_to_markdown"):
                text = result.export_to_markdown()
            else:
                text = str(result)
            if text and text.strip():
                return text.strip()[:max_chars]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception:
        # Fall through to MarkItDown if Docling fails
        pass

    # 2. Try Microsoft MarkItDown
    try:
        from markitdown import MarkItDown
        import tempfile
        import os
        from pathlib import Path
        
        suffix = ".pdf"
        if filename:
            ext = Path(filename).suffix
            if ext:
                suffix = ext
                
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
            
        try:
            md = MarkItDown()
            result = md.convert(tmp_path)
            text = result.text_content or ""
            return text.strip()[:max_chars]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception:
        # 3. Fallback to standard plain text extraction
        try:
            res = extract_pdf_text(file_bytes, max_chars=max_chars)
            if not res:
                return file_bytes.decode("utf-8", errors="ignore")[:max_chars]
            return res
        except Exception:
            return file_bytes.decode("utf-8", errors="ignore")[:max_chars]


def should_use_native_text_primary(file_bytes: bytes) -> bool:
    text = extract_pdf_text(file_bytes, max_chars=12000)
    if len(text.strip()) < 2500:
        return False
    
    # Check for garbled/corrupted font text by counting architectural keywords
    keywords = ["door", "frame", "schedule", "hardware", "width", "height", "thickness", "type", "material", "finish", "opening", "closer", "lock", "latch", "hinge", "set", "mark", "room"]
    keyword_hits = sum(1 for kw in keywords if re.search(r'\b' + kw + r'\b', text, re.I))
    if keyword_hits < 3:
        return False
        
    has_door_signal = re.search(r"\bdoor\s+schedule\b|\bopening\s+(?:no|number|mark)\b|\bdoor\s+(?:no|number|mark)\b", text, re.I)
    has_hardware_signal = re.search(r"\bhardware\s+(?:set|sets|group|groups)\b|\bhw\s+set\b|\bhw\s+group\b|\bhardware\s+specification\b", text, re.I)
    return bool(has_door_signal or has_hardware_signal)


def normalize_door(d: dict[str, Any]) -> dict[str, Any]:
    remarks = _as_string_list(d.get("remarks"))
    remarks_text = " ".join(remarks)
    return {
        "mark": d.get("mark"),
        "room_or_location": d.get("room_or_location"),
        "door_type": d.get("door_type"),
        "opening_type": d.get("door_type"),
        "interior_or_exterior": None,
        "size": {"width": d.get("width"), "height": d.get("height"), "thickness": d.get("thickness")},
        "door_material": d.get("door_material"),
        "door_finish": d.get("door_finish"),
        "glazing": d.get("glazing"),
        "frame_type": d.get("frame_type"),
        "frame_material": d.get("frame_material"),
        "frame_finish": d.get("frame_finish"),
        "fire_rating": d.get("fire_rating"),
        "hardware_set": None if is_placeholder_set_label(d.get("hardware_set")) else clean_hardware_set_label(d.get("hardware_set")),
        "closer": d.get("closer"),
        "electric_or_access_control": d.get("electric_or_access_control"),
        "remarks": remarks,
        "existing_to_remain": (
            bool(d.get("existing_to_remain"))
            or bool(re.search(
                r"existing[\s_-]*to[\s_-]*remain|\bETR\b|e\.t\.r\.",
                " ".join([
                    remarks_text,
                    str(d.get("door_material") or ""),
                    str(d.get("door_type") or ""),
                    str(d.get("frame_material") or ""),
                    str(d.get("room_or_location") or "")
                ]),
                re.I
            ))
        ),
        "hardware_status": "review required",
        "install_complexity": "medium",
        "risk_level": "medium",
        "special_conditions": [],
        "issues": [],
        "recommendations": [],
        "rfi_required": False,
        "rfi_questions": [],
        "source_page": d.get("source_page"),
        "source_crop_id": d.get("source_crop_id"),
        "confidence": d.get("confidence") if isinstance(d.get("confidence"), (int, float)) else 0.7,
    }


def normalize_set(s: dict[str, Any]) -> dict[str, Any]:
    label = clean_hardware_set_label(s.get("hardware_set") or s.get("id"))
    raw_items = s.get("items") if isinstance(s.get("items"), list) else []
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for i, it in enumerate(raw_items):
        if not isinstance(it, dict):
            continue
        item = {
            "item_no": it.get("item_seq") or it.get("item_no") or i + 1,
            "qty": it.get("qty"),
            "unit": it.get("unit"),
            "desc": it.get("description") or it.get("desc") or "",
            "part": it.get("model_or_catalog") or it.get("part"),
            "mfr": it.get("manufacturer") or it.get("mfr"),
            "finish": it.get("finish"),
            "notes": it.get("notes"),
            "confidence": it.get("confidence") if isinstance(it.get("confidence"), (int, float)) else None,
        }
        meaningful = any(str(item.get(field) or "").strip() for field in ("qty", "unit", "desc", "part", "mfr", "finish", "notes"))
        if not meaningful:
            continue
        sig = f"{item.get('item_no') or ''}|{str(item.get('desc') or '').strip().lower()}|{str(item.get('part') or '').strip().lower()}"
        if sig in seen:
            continue
        seen.add(sig)
        items.append(item)
    raw_status = str(s.get("status") or "").lower().strip()
    if raw_status == "active":
        status = "complete" if items else "incomplete"
    elif raw_status in {"not_used", "void"}:
        status = "voided"
    elif raw_status == "existing":
        status = "complete" if items else "incomplete"
    elif raw_status == "review_required":
        status = "incomplete"
    else:
        status = "complete" if items else "incomplete"
    missing = [] if items or raw_status in {"not_used", "void"} else ["no hardware items extracted"]
    return {
        "hardware_set": label,
        "header_verbatim": s.get("set_title"),
        "referenced_by_doors": s.get("referenced_doors") if isinstance(s.get("referenced_doors"), list) else [],
        "status": status,
        "raw_status": raw_status or None,
        "items": items,
        "missing_or_unclear_items": missing,
        "special_coordination": [],
        "estimator_note": s.get("set_notes"),
        "confidence": s.get("confidence") if isinstance(s.get("confidence"), (int, float)) else 0.7,
    }


def dedupe_sets(sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for s in sets:
        if is_placeholder_set_label(s.get("hardware_set")):
            continue
        key = canonical_set_key(s.get("hardware_set")) or f"__unkeyed_{len(by_key)}"
        existing = by_key.get(key)
        if not existing:
            by_key[key] = s
            continue
        sigs = {f"{it.get('item_no') or ''}|{str(it.get('desc') or '').strip().lower()}" for it in existing.get("items") or []}
        for it in s.get("items") or []:
            sig = f"{it.get('item_no') or ''}|{str(it.get('desc') or '').strip().lower()}"
            if sig not in sigs:
                existing.setdefault("items", []).append(it)
                sigs.add(sig)
        for field in ("header_verbatim", "raw_status", "estimator_note"):
            if not existing.get(field) and s.get(field):
                existing[field] = s[field]
        if existing.get("status") != "complete" and s.get("status") == "complete":
            existing["status"] = "complete"
    return list(by_key.values())


def _set_sort_key(value: Any) -> tuple[int, int | str]:
    key = canonical_set_key(value)
    return (0, int(key)) if key.isdigit() else (1, key)


def known_hardware_set_ids(doors: list[dict[str, Any]], sets: list[dict[str, Any]]) -> list[str]:
    ids = {clean_hardware_set_label(d.get("hardware_set")) for d in doors if d.get("hardware_set")}
    ids.update(clean_hardware_set_label(s.get("hardware_set")) for s in sets if s.get("hardware_set"))
    return sorted((x for x in ids if x), key=_set_sort_key)


def should_run_hardware_rescue(doors: list[dict[str, Any]], sets: list[dict[str, Any]], *, truncated: bool = False) -> bool:
    referenced = {canonical_set_key(d.get("hardware_set")) for d in doors if d.get("hardware_set")}
    referenced.discard("")
    if not referenced:
        return False
    set_by_key = {canonical_set_key(s.get("hardware_set")): s for s in sets if s.get("hardware_set")}
    total_items = sum(len(s.get("items") or []) for s in sets)
    active_sets = [s for s in sets if str(s.get("status") or "").lower() not in {"voided", "not_used", "void"}]
    one_item_sets = [s for s in active_sets if len(s.get("items") or []) <= 1]
    empty_referenced = [
        key for key in referenced
        if not set_by_key.get(key) or not (set_by_key.get(key) or {}).get("items")
    ]
    if truncated and empty_referenced:
        return True
    if empty_referenced and total_items == 0:
        return True
    if len(referenced) >= 3 and total_items < max(4, len(referenced) // 2):
        return True
    if len(referenced) >= 5 and active_sets and total_items <= len(active_sets) * 2 and len(one_item_sets) >= max(3, len(active_sets) // 2):
        return True
    return bool(empty_referenced) and len(referenced) >= 3


def _item_signature(item: dict[str, Any]) -> str:
    return "|".join(
        str(item.get(field) or "").strip().lower()
        for field in ("qty", "unit", "desc", "part", "mfr", "finish")
    )


def merge_rescued_sets(existing_sets: list[dict[str, Any]], rescued_sets: list[dict[str, Any]], allowed_ids: list[str] | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_key, aliases = _build_set_lookup(existing_sets)
    allowed_keys = {canonical_set_key(value) for value in allowed_ids or [] if canonical_set_key(value)}
    allowed_aliases = set(allowed_keys)
    for value in allowed_ids or []:
        allowed_aliases.update(alias_set_keys(value))
    added_sets = 0
    added_items = 0

    for rescued in rescued_sets:
        key = canonical_set_key(rescued.get("hardware_set"))
        if not key:
            continue
        target = resolve_set(rescued.get("hardware_set"), by_key, aliases)
        if not target:
            rescued_aliases = alias_set_keys(rescued.get("hardware_set"))
            if allowed_aliases and not ({key, *rescued_aliases} & allowed_aliases):
                continue
            target = rescued
            target["hardware_set"] = clean_hardware_set_label(target.get("hardware_set"))
            existing_sets.append(target)
            by_key[key] = target
            for alias in alias_set_keys(target.get("hardware_set")):
                aliases.setdefault(alias, target)
            added_sets += 1
            added_items += len(target.get("items") or [])
            continue

        existing_sigs = {_item_signature(item) for item in target.get("items") or []}
        for item in rescued.get("items") or []:
            sig = _item_signature(item)
            if sig in existing_sigs:
                continue
            target.setdefault("items", []).append(item)
            existing_sigs.add(sig)
            added_items += 1

        for field in ("header_verbatim", "raw_status", "estimator_note"):
            if not target.get(field) and rescued.get(field):
                target[field] = rescued[field]
        if target.get("items"):
            target["status"] = "complete"
            target["missing_or_unclear_items"] = []

    return dedupe_sets(existing_sets), {"sets_added": added_sets, "items_added": added_items}


def rescue_hardware_sets_from_crops(file_bytes: bytes, filename: str, known_ids: list[str], logs: list[dict[str, Any]], api_key: str | None) -> tuple[list[dict[str, Any]], int]:
    try:
        crops = detect_hardware_crops(file_bytes, max_candidates=8, dpi=220)
    except Exception as exc:
        _log(logs, "warn", f"Completeness check unavailable: {exc}", "Completeness check")
        return [], 0

    if not crops:
        _log(logs, "warn", "Completeness check could not find readable hardware excerpts.", "Completeness check")
        return [], 0
    definition_pattern = re.compile(
        r"\b(?:SET|HW\s*SET|HARDWARE\s*SET)\s*#?\s*[A-Z]?\d+[A-Z]?\b|"
        r"\b(EXIT\s+DEVICE|CONTINUOUS\s+HINGE|LOCKSET|LATCHSET|CLOSER|THRESHOLD|WEATHERSTRIP|GASKET)\b",
        re.I,
    )
    strong_definition_crops = [
        crop for crop in crops
        if definition_pattern.search(crop.get("text") or "")
        and str(crop.get("source") or "").startswith("text:")
        and "column" not in str(crop.get("source") or "").lower()
        and "middle" not in str(crop.get("source") or "").lower()
    ]
    definition_crops = [
        crop for crop in crops
        if definition_pattern.search(crop.get("text") or "")
        and not str(crop.get("source") or "").lower().startswith("tile_")
    ]
    if strong_definition_crops:
        crops = strong_definition_crops[:4]
    elif definition_crops:
        crops = definition_crops[:6]

    _log(logs, "info", "Completeness check started.", "Completeness check")
    rescued_raw: list[dict[str, Any]] = []
    elapsed = 0
    batch_size = 3
    known_text = ", ".join(known_ids) if known_ids else "not known"

    for batch_start in range(0, len(crops), batch_size):
        batch = crops[batch_start:batch_start + batch_size]
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "These are high-resolution excerpts from the same door hardware schedule. "
                    "They may overlap. Extract every visible hardware set and line item, merge duplicate visible lines, "
                    "and do not infer anything that is not readable."
                ),
            }
        ]
        for idx, crop in enumerate(batch, start=batch_start + 1):
            hint = re.sub(r"\s+", " ", crop.get("text") or "").strip()[:900]
            content.append({"type": "input_text", "text": f"Excerpt {idx}. Page {crop.get('page')}. OCR hint: {hint or 'none'}"})
            content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + crop["base64_image"], "detail": "high"})
        content.append(
            {
                "type": "input_text",
                "text": (
                    f"Known hardware set IDs from the door schedule: {known_text}.\n"
                    "Return only JSON in the hardware_sets schema from the system instructions."
                ),
            }
        )

        try:
            call = _openai_json_call(
                "Completeness check",
                [
                    {"role": "system", "content": STAGED_HW_SYSTEM},
                    {"role": "user", "content": content},
                ],
                32000,
                "medium",
                logs,
                api_key=api_key,
            )
        except ExtractionError as exc:
            _log(logs, "warn", f"Completeness check skipped one excerpt batch: {exc}", "Completeness check")
            continue

        elapsed += int(call["elapsed"])
        raw_sets = call["parsed"].get("hardware_sets") or call["parsed"].get("sets") or []
        rescued_raw.extend(s for s in raw_sets if isinstance(s, dict))

    rescued = dedupe_sets([normalize_set(s) for s in rescued_raw])
    item_count = sum(len(s.get("items") or []) for s in rescued)
    _log(logs, "ok", f"Completeness check recovered {len(rescued)} set(s) and {item_count} item row(s).", "Completeness check")
    return rescued, elapsed


def rescue_hardware_sets_from_text(file_bytes: bytes, known_ids: list[str], focus_ids: list[str], logs: list[dict[str, Any]], api_key: str | None) -> tuple[list[dict[str, Any]], int]:
    text = extract_pdf_text(file_bytes, max_chars=45000)
    if len(text.strip()) < 500:
        return [], 0
    known_text = ", ".join(known_ids) if known_ids else "not known"
    focus_text = ", ".join(focus_ids) if focus_ids else "any set with missing line items"
    try:
        call = _openai_json_call(
            "Text completeness check",
            [
                {"role": "system", "content": STAGED_HW_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "The following is native PDF text from a door schedule / hardware schedule. "
                                "Use it as a fallback for searchable or borderless tables where image crops may miss line items. "
                                f"Known set IDs: {known_text}. Focus on incomplete set IDs: {focus_text}. "
                                "Extract visible hardware set, lock/latch/handle set, or hardware group definitions and line items. "
                                "Do not infer missing rows.\n\nPDF_TEXT:\n" + text
                            ),
                        }
                    ],
                },
            ],
            20000,
            "medium",
            logs,
            api_key=api_key,
        )
    except ExtractionError as exc:
        _log(logs, "warn", f"Text completeness check skipped: {exc}", "Text completeness check")
        return [], 0

    raw_sets = call["parsed"].get("hardware_sets") or call["parsed"].get("sets") or []
    rescued = dedupe_sets([normalize_set(s) for s in raw_sets if isinstance(s, dict)])
    item_count = sum(len(s.get("items") or []) for s in rescued)
    _log(logs, "ok", f"Text completeness check recovered {len(rescued)} set(s) and {item_count} item row(s).", "Text completeness check")
    return rescued, int(call["elapsed"])


def rescue_door_hardware_fields_from_crops(file_bytes: bytes, logs: list[dict[str, Any]], api_key: str | None) -> tuple[list[dict[str, Any]], int]:
    try:
        crops = detect_hardware_crops(file_bytes, max_candidates=6, dpi=220)
    except Exception as exc:
        _log(logs, "warn", f"Door schedule completeness check unavailable: {exc}", "Door completeness check")
        return [], 0
    if not crops:
        return [], 0

    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                "These are high-resolution excerpts from an image-heavy door schedule. "
                "Extract visible door schedule rows. Focus on door mark and hardware_set / hardware group columns. "
                "Do not infer missing values."
            ),
        }
    ]
    for idx, crop in enumerate(crops, start=1):
        content.append({"type": "input_text", "text": f"Excerpt {idx}. Page {crop.get('page')}. Source: {crop.get('source')}"})
        content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + crop["base64_image"], "detail": "high"})

    try:
        call = _openai_json_call(
            "Door completeness check",
            [
                {"role": "system", "content": STAGED_DOOR_SYSTEM},
                {"role": "user", "content": content},
            ],
            24000,
            "medium",
            logs,
            api_key=api_key,
        )
    except ExtractionError as exc:
        _log(logs, "warn", f"Door completeness check skipped: {exc}", "Door completeness check")
        return [], 0

    raw_doors = call["parsed"].get("doors") or call["parsed"].get("rows") or []
    rescued = [normalize_door(d) for d in raw_doors if isinstance(d, dict)]
    _log(logs, "ok", f"Door completeness check recovered {len(rescued)} candidate row(s).", "Door completeness check")
    return rescued, int(call["elapsed"])


def should_run_door_field_rescue(file_bytes: bytes, doors: list[dict[str, Any]]) -> bool:
    if len(doors) < 3:
        return False
    missing = [d for d in doors if not d.get("hardware_set")]
    if len(missing) < max(3, len(doors) // 2):
        return False
    text = extract_pdf_text(file_bytes, max_chars=8000)
    if len(text.strip()) < 200:
        return True
    upper = text.upper()
    return any(token in upper for token in ("HARDWARE SET", "HW SET", "HARDWARE GROUP", "HDWR SET"))


def merge_rescued_door_fields(doors: list[dict[str, Any]], rescued_doors: list[dict[str, Any]]) -> dict[str, int]:
    by_mark = {str(d.get("mark") or "").strip().upper(): d for d in doors if d.get("mark")}
    filled = 0
    added = 0
    for rescued in rescued_doors:
        mark = str(rescued.get("mark") or "").strip()
        if not mark:
            continue
        target = by_mark.get(mark.upper())
        if not target:
            if rescued.get("hardware_set"):
                doors.append(rescued)
                by_mark[mark.upper()] = rescued
                added += 1
            continue
        if not target.get("hardware_set") and rescued.get("hardware_set"):
            target["hardware_set"] = rescued.get("hardware_set")
            filled += 1
        for field in ("room_or_location", "door_type", "door_material", "frame_type", "fire_rating", "remarks"):
            if not target.get(field) and rescued.get(field):
                target[field] = rescued.get(field)
    return {"doors_added": added, "hardware_sets_filled": filled}


def referenced_empty_set_ids(doors: list[dict[str, Any]], sets: list[dict[str, Any]]) -> list[str]:
    set_by_key, aliases = _build_set_lookup(sets)
    missing: set[str] = set()
    for door in doors:
        value = door.get("hardware_set")
        if not value:
            continue
        matched = resolve_set(value, set_by_key, aliases)
        if not matched or not (matched.get("items") or []):
            missing.add(clean_hardware_set_label(value))
    return sorted(missing, key=_set_sort_key)


def map_doors_hardware(doors: list[dict[str, Any]], sets: list[dict[str, Any]], general_notes: list[str] = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    qa: list[dict[str, Any]] = []
    set_by_canon, set_aliases = _build_set_lookup(sets)
    
    # 1. Resolve existing_to_remain from general notes referenced in remarks
    if general_notes:
        note_map = {}
        for note in general_notes:
            match = re.match(r"^\s*(\d+)[\.\s\-]+(.*)$", note)
            if match:
                num = match.group(1)
                text = match.group(2).strip()
                note_map[num] = text
                
        for d in doors:
            if d.get("existing_to_remain"):
                continue
            remarks_list = d.get("remarks") or []
            is_existing = False
            for r in remarks_list:
                tokens = re.findall(r"\d+", str(r))
                for t in tokens:
                    note_text = note_map.get(t)
                    if note_text:
                        note_upper = note_text.upper()
                        if "EXISTING" in note_upper and ("REMAIN" in note_upper or "HARDWARE" in note_upper):
                            is_existing = True
                            break
                        if "ETR" in note_upper:
                            is_existing = True
                            break
                if is_existing:
                    break
            if is_existing:
                d["existing_to_remain"] = True

    # 2. Try resolving implicit hardware sets for doors where hardware_set is empty
    for d in doors:
        if not d.get("hardware_set"):
            resolved = None
            
            # Fallback 1: Match door_type (e.g. Type 'A' -> Group 'A')
            dt = str(d.get("door_type") or "").strip()
            if dt and len(dt) <= 15:
                matched = resolve_set(dt, set_by_canon, set_aliases)
                if matched:
                    resolved = matched.get("hardware_set")
                    d["hardware_set"] = resolved
                    d["raw_hardware_set"] = f"(resolved from door_type '{dt}')"
                    
            # Fallback 2: Match frame_type (e.g. Type 'A' -> Group 'A')
            if not resolved:
                ft = str(d.get("frame_type") or "").strip()
                if ft and len(ft) <= 15:
                    matched = resolve_set(ft, set_by_canon, set_aliases)
                    if matched:
                        resolved = matched.get("hardware_set")
                        d["hardware_set"] = resolved
                        d["raw_hardware_set"] = f"(resolved from frame_type '{ft}')"
                        
            # Fallback 3: Parse remarks for explicit group reference
            if not resolved:
                remarks_list = d.get("remarks")
                remarks_text = " ".join(str(x) for x in remarks_list) if isinstance(remarks_list, list) else str(remarks_list or "")
                match = re.search(r"\b(?:group|set|hw(?:\s*set)?|type|spec)\s*#?\s*([a-z0-9]+)\b", remarks_text, re.I)
                if match:
                    group_ref = match.group(1)
                    matched = resolve_set(group_ref, set_by_canon, set_aliases)
                    if matched:
                        resolved = matched.get("hardware_set")
                        d["hardware_set"] = resolved
                        d["raw_hardware_set"] = f"(resolved from remarks: '{match.group(0)}')"

            # Fallback 4: Match door mark (e.g. Mark '101A' -> Group '101A')
            if not resolved:
                mark = str(d.get("mark") or "").strip()
                if mark:
                    matched = resolve_set(mark, set_by_canon, set_aliases)
                    if matched:
                        resolved = matched.get("hardware_set")
                        d["hardware_set"] = resolved
                        d["raw_hardware_set"] = f"(resolved from door mark '{mark}')"

    for d in doors:
        if not d.get("hardware_set"):
            continue
        matched = resolve_set(d["hardware_set"], set_by_canon, set_aliases)
        if matched and matched.get("hardware_set") != d.get("hardware_set"):
            d["raw_hardware_set"] = d.get("hardware_set")
            d["hardware_set"] = matched.get("hardware_set")
            
    for s in sets:
        s["referenced_by_doors"] = [d.get("mark") for d in doors if d.get("hardware_set") == s.get("hardware_set")]
        
    have = {s.get("hardware_set") for s in sets}
    for d in doors:
        if d.get("hardware_set") and d.get("hardware_set") not in have:
            sets.append({
                "hardware_set": d.get("hardware_set"),
                "header_verbatim": None,
                "referenced_by_doors": [x.get("mark") for x in doors if x.get("hardware_set") == d.get("hardware_set")],
                "status": "missing",
                "raw_status": None,
                "items": [],
                "missing_or_unclear_items": ["hardware set referenced by doors but not found in spec"],
                "special_coordination": [],
                "estimator_note": None,
                "confidence": 0.3,
            })
            have.add(d.get("hardware_set"))
            qa.append({"kind": "missing_set", "set": d.get("hardware_set"), "mark": d.get("mark"), "message": f"Door {d.get('mark')} references hardware set {d.get('hardware_set')} but the set was not extracted."})

    set_by_id = {s.get("hardware_set"): s for s in sets}
    mapping: list[dict[str, Any]] = []
    for d in doors:
        by_others_text = " ".join([
            str(d.get("door_material") or ""),
            str(d.get("door_type") or ""),
            str(d.get("frame_material") or ""),
            str(d.get("frame_type") or ""),
            " ".join(d.get("remarks") or [])
        ]).upper()
        
        if "BY OTHERS" in by_others_text or "N.I.C." in by_others_text or "NIC" in by_others_text:
            mapping.append({
                "door_mark": d.get("mark"),
                "hardware_set": None,
                "item_no": None,
                "qty": None,
                "description": "(opening is by others / not in contract; not mapped)",
                "catalog_number": None,
                "manufacturer": None,
                "finish": None,
                "notes": None,
                "status": "BY_OTHERS"
            })
            continue

        if d.get("existing_to_remain"):
            mapping.append({"door_mark": d.get("mark"), "hardware_set": d.get("hardware_set"), "item_no": None, "qty": None, "description": "(existing door - hardware to remain; not mapped per rule)", "catalog_number": None, "manufacturer": None, "finish": None, "notes": None, "status": "EXISTING_TO_REMAIN"})
            continue
            
        # Check for coiling, overhead, sectional doors or roll-up security shutters
        coiling_text = " ".join([
            str(d.get("door_material") or ""),
            str(d.get("door_type") or ""),
            " ".join(d.get("remarks") or [])
        ]).upper()
        if not d.get("hardware_set") and any(token in coiling_text for token in ("COILING", "ROLL-UP", "ROLL UP", "ROLLING", "SHUTTER", "OVERHEAD", "SECTIONAL", "ASTA", "QMI")):
            mapping.append({
                "door_mark": d.get("mark"),
                "hardware_set": None,
                "item_no": None,
                "qty": None,
                "description": "(coiling/overhead door - hardware supplied by door manufacturer; not mapped)",
                "catalog_number": None,
                "manufacturer": None,
                "finish": None,
                "notes": None,
                "status": "COILING_SYSTEM"
            })
            continue
            
        if not d.get("hardware_set"):
            mapping.append({"door_mark": d.get("mark"), "hardware_set": None, "item_no": None, "qty": None, "description": "(no hardware set assigned)", "catalog_number": None, "manufacturer": None, "finish": None, "notes": None, "status": "NO_HW_SET"})
            qa.append({"kind": "no_hw_set", "mark": d.get("mark"), "message": f"Door {d.get('mark')} has no hardware set assigned."})
            continue
            
        # Check for compound hardware sets (e.g. "1, 2" or "1 & 2")
        hw_val = d.get("hardware_set")
        parts = [p.strip() for p in re.split(r"\s*(?:,|&|\band\b)\s*", str(hw_val), flags=re.I) if p.strip()]
        if len(parts) > 1:
            resolved_sets = []
            all_resolved = True
            for part in parts:
                matched_part = resolve_set(part, set_by_canon, set_aliases)
                if matched_part and matched_part.get("items"):
                    resolved_sets.append(matched_part)
                else:
                    all_resolved = False
                    break
            
            if all_resolved:
                combined_items = []
                for r_set in resolved_sets:
                    combined_items.extend(r_set.get("items") or [])
                for i, it in enumerate(combined_items):
                    mapping.append({
                        "door_mark": d.get("mark"),
                        "hardware_set": hw_val,
                        "item_no": it.get("item_no") or i + 1,
                        "qty": it.get("qty"),
                        "description": it.get("desc") or "",
                        "catalog_number": it.get("part"),
                        "manufacturer": it.get("mfr"),
                        "finish": it.get("finish"),
                        "notes": it.get("notes"),
                        "status": "OK"
                    })
                continue

        s = set_by_id.get(d.get("hardware_set"))
        if not s or not s.get("items"):
            mapping.append({"door_mark": d.get("mark"), "hardware_set": d.get("hardware_set"), "item_no": None, "qty": None, "description": "(hardware set has no extracted items)" if s else "(hardware set not found in spec)", "catalog_number": None, "manufacturer": None, "finish": None, "notes": None, "status": "FAILED_EXTRACTION_REVIEW_REQUIRED"})
            qa.append({"kind": "set_empty" if s else "missing_set", "set": d.get("hardware_set"), "mark": d.get("mark"), "message": f"Door {d.get('mark')}: hardware set {d.get('hardware_set')} has zero items." if s else f"Door {d.get('mark')} references missing set {d.get('hardware_set')}."})
            continue
            
        for i, it in enumerate(s.get("items") or []):
            mapping.append({"door_mark": d.get("mark"), "hardware_set": d.get("hardware_set"), "item_no": it.get("item_no") or i + 1, "qty": it.get("qty"), "description": it.get("desc") or "", "catalog_number": it.get("part"), "manufacturer": it.get("mfr"), "finish": it.get("finish"), "notes": it.get("notes"), "status": "OK"})
            
    return mapping, qa


def rollup_summary(doors: list[dict[str, Any]], sets: list[dict[str, Any]], scope: str, elapsed: int, meta: dict[str, Any]) -> dict[str, Any]:
    def is_access(d: dict[str, Any]) -> bool:
        v = str(d.get("electric_or_access_control") or "").strip()
        return bool(v and not re.match(r"^(no|none|n/a|null|-)$", v, re.I))

    def is_fire(d: dict[str, Any]) -> bool:
        v = str(d.get("fire_rating") or "").strip()
        return bool(v and not re.match(r"^(none|non|n/a|null|-)$", v, re.I))

    return {
        "scope_type": scope,
        "project_name": meta.get("project_name"),
        "project_number": meta.get("project_number"),
        "architect": meta.get("architect"),
        "address": meta.get("address"),
        "drawing": meta.get("drawing"),
        "date": meta.get("date"),
        "total_openings_found": len(doors),
        "total_hardware_sets_referenced": len({d.get("hardware_set") for d in doors if d.get("hardware_set")}),
        "hardware_sets_missing_or_unclear": len([s for s in sets if s.get("status") != "complete"]),
        "high_risk_openings": len([d for d in doors if d.get("risk_level") == "high"]),
        "medium_risk_openings": len([d for d in doors if d.get("risk_level") == "medium"]),
        "low_risk_openings": len([d for d in doors if d.get("risk_level") == "low"]),
        "complex_installations": len([d for d in doors if d.get("install_complexity") == "high"]),
        "access_control_openings": len([d for d in doors if is_access(d)]),
        "exterior_openings": len([d for d in doors if d.get("interior_or_exterior") == "Exterior"]),
        "fire_rated_openings": len([d for d in doors if is_fire(d)]),
        "overall_bid_risk": "Medium",
        "estimator_summary": f"Secure analysis extracted {len(doors)} opening(s) and {len(sets)} hardware set(s). Verify against source PDF before bidding.",
    }


def _marks(items: list[dict[str, Any]], n: int = 8) -> str:
    values = [str(x.get("mark") or "") for x in items if x.get("mark")]
    head = ", ".join(values[:n])
    return f"{head}, ...+{len(values) - n} more" if len(values) > n else head


def synthesize(doors: list[dict[str, Any]], sets: list[dict[str, Any]], scope: str, sheet_context: dict[str, Any]) -> dict[str, Any]:
    risks: list[dict[str, Any]] = []
    rfis: list[dict[str, Any]] = []
    notes: list[str] = []
    recs = {"supply_only_notes": [], "installation_only_notes": [], "supply_and_installation_notes": [], "exclusions_to_consider": [], "allowances_to_consider": [], "coordination_items": []}
    set_by_id = {s.get("hardware_set"): s for s in sets}

    def risk(sev: str, cat: str, issue: str, affected: list[str], rec: str) -> None:
        risks.append({"severity": sev, "category": cat, "issue": issue, "affected_openings": affected, "recommendation": rec, "status": "Open", "source": "heuristic"})

    def rfi(pri: str, cat: str, question: str, affected: list[str], rec: str, reason: str | None = None) -> None:
        rfis.append({"priority": pri, "category": cat, "question": question, "affected_openings": affected, "recommendation": rec, "status": "Open", "reason": reason or rec, "source": "heuristic"})

    no_set = [d for d in doors if not d.get("hardware_set")]
    if no_set:
        risk("high", "Hardware mapping", f"{len(no_set)} opening(s) have no hardware set assigned in the schedule.", [d.get("mark") for d in no_set], "Issue RFI to confirm hardware set assignments before bidding.")
        rfi("high", "Hardware mapping", f"The door schedule does not show a hardware set for: {_marks(no_set)}. Please confirm the intended hardware set for each.", [d.get("mark") for d in no_set], "Confirm assignments before bid close.")

    failed = [d for d in doors if d.get("hardware_set") and (not set_by_id.get(d.get("hardware_set")) or not (set_by_id.get(d.get("hardware_set")) or {}).get("items"))]
    if failed:
        ids = sorted({str(d.get("hardware_set")) for d in failed})
        risk("high", "Hardware set definitions", f"{len(ids)} hardware set(s) referenced by {len(failed)} door(s) have no extracted line items.", [d.get("mark") for d in failed], "Locate full hardware set definitions; carry as allowance until confirmed.")
        rfi("high", "Hardware set definitions", f"Provide the complete line-item list for hardware set(s): {', '.join(ids)}.", [d.get("mark") for d in failed], "Carry as allowance until confirmed.")

    fire = [d for d in doors if d.get("fire_rating") and not re.match(r"^(-|none|non|n/a)$", str(d.get("fire_rating")), re.I)]
    if fire:
        risk("medium", "Fire-rated openings", f"{len(fire)} fire-rated opening(s) require coordinated UL-listed door, frame and hardware assemblies.", [d.get("mark") for d in fire], "Confirm labels, positive latching, closers and gasketing requirements.")
        recs["allowances_to_consider"].append("Allowance for fire-rated assembly coordination, S-label gasketing and any UL field-modification charges.")

    ac_re = re.compile(r"\bCR\b|\bEL\b|\bDPS\b|\bRX\b|\bEH\b|\bAO\b|panic|card reader|access control|electrified|maglock|electric\s*strike|EPT|REX|automatic\s*operator", re.I)
    ac = [d for d in doors if ac_re.search(" ".join(_as_string_list(d.get("remarks"))) + " " + str(d.get("door_type") or "") + " " + str(d.get("room_or_location") or ""))]
    if ac:
        risk("high", "Access control / electrified", f"{len(ac)} opening(s) involve electrified or access-control hardware.", [d.get("mark") for d in ac], "Confirm Div 08 / 26 / 27 / 28 scope split before bidding.")
        rfi("high", "Access control / electrified", f"For electrified openings ({_marks(ac)}), confirm responsibility for 120 V power, low-voltage cabling, readers/head-end, fire alarm release, commissioning and programming.", [d.get("mark") for d in ac], "Carry Div 8 components only unless explicitly included.")
        recs["coordination_items"].append("Coordinate electrified hardware split: Div 08 hardware / Div 26 power / Div 27-28 low-voltage + head-end.")

    if len(doors) >= 5:
        keying_notes = sheet_context.get("keying_notes") if isinstance(sheet_context.get("keying_notes"), list) else []
        if keying_notes:
            notes.append(f"Keying notes captured from the drawings ({len(keying_notes)} line(s)); verify keyway, master structure, cylinder format and key counts.")
        else:
            rfi("medium", "Keying / cylinders", "Please provide the complete keying schedule, keyway, cylinder format, construction core requirement and key counts.", [], "Carry construction cylinders as an allowance until keying meeting is held.")
            recs["allowances_to_consider"].append("Allowance for construction cylinders and final keying meeting attendance.")

    if scope in {"Supply Only", "Supply & Installation"}:
        recs["supply_only_notes"].append("Submittal package: door, frame and hardware schedules with manufacturer cut sheets, keying schedule, electrified hardware riser, anchor templates.")
        recs["exclusions_to_consider"].append("Exclude 120 V power, low-voltage cabling, access-control head-end, intrusion detection programming, fire-alarm tie-in (NIC).")
        recs["exclusions_to_consider"].append("Exclude permits, demolition, painting, drywall patching at frame anchors, floor preparation at thresholds.")
    if scope in {"Installation Only", "Supply & Installation"}:
        recs["installation_only_notes"].append("Field-measure all openings before fabrication release. Verify rough-opening size, frame anchor type, and floor condition.")
        recs["installation_only_notes"].append("Storage and protection of doors / frames / hardware on site is by GC unless otherwise noted.")
    recs["coordination_items"].append("Attend pre-installation meeting with GC, EC, low-voltage, fire alarm and security trades.")
    recs["coordination_items"].append("Hold formal keying meeting with owner before cylinder fabrication.")

    if doors:
        notes.append(f"{len(doors)} opening(s) extracted from the schedule. Verify all marks against the source PDF before submitting bid.")
    if sets:
        notes.append(f"{len(sets)} hardware set(s) identified; {len([s for s in sets if s.get('items')])} have a complete extracted item list.")
    if sheet_context.get("general_notes"):
        notes.append(f"{len(sheet_context.get('general_notes') or [])} general note(s) captured from the door-schedule sheet.")
    if sheet_context.get("hardware_preamble"):
        notes.append(f"{len(sheet_context.get('hardware_preamble') or [])} hardware-preamble note(s) captured from hardware-set sheet(s).")

    return {"risks": risks, "rfis": rfis, "notes": notes, "recs": recs}


def extract_pdf_secure(file_bytes: bytes, filename: str, scope: str, run_rfis: bool = True, api_key: str | None = None) -> dict[str, Any]:
    logs: list[dict[str, Any]] = []
    if not file_bytes or b"%PDF-" not in file_bytes[:1024]:
        raise ExtractionError("Uploaded file does not look like a PDF.")

    scope = scope or "Supply & Installation"
    native_text_cache: str | None = None
    data_url_cache: str | None = None

    def native_text() -> str:
        nonlocal native_text_cache
        if native_text_cache is None:
            native_text_cache = extract_pdf_text_markdown(file_bytes, filename, max_chars=45000)
        return native_text_cache

    def pdf_data_url() -> str:
        nonlocal data_url_cache
        if data_url_cache is None:
            data_url_cache = "data:application/pdf;base64," + base64.b64encode(file_bytes).decode("ascii")
        return data_url_cache

    _log(logs, "info", f"Secure analysis started for {filename} ({len(file_bytes) / 1024:.0f} KB).", "start")
    use_native_text_primary = should_use_native_text_primary(file_bytes)

    try:
        door_content = (
            [{"type": "input_text", "text": f"Project scope: {scope}\n\nRead this native PDF text end-to-end. Extract every visible door schedule row per your system instructions. Preserve text exactly as shown - do not infer. Use null for unclear values.\n\nPDF_TEXT:\n{native_text()}\n\nReturn JSON: {{ \"doors\": [...] }}"}]
            if use_native_text_primary
            else [
                {"type": "input_file", "filename": filename, "file_data": pdf_data_url()},
                {"type": "input_text", "text": f"Project scope: {scope}\n\nRead the attached PDF end-to-end. Extract every visible door schedule row per your system instructions. Preserve text exactly as shown - do not infer. Use null for unclear values.\n\nReturn JSON: {{ \"doors\": [...] }}"},
            ]
        )
        call1 = _openai_json_call(
            "Door schedule review",
            [
                {"role": "system", "content": STAGED_DOOR_SYSTEM},
                {"role": "user", "content": door_content},
            ],
            32000,
            "medium" if use_native_text_primary else "high",
            logs,
            api_key=api_key,
        )
    except ExtractionError as exc:
        text = native_text()
        if not text.strip() or not _can_fallback_after_error(exc):
            raise
        _log(logs, "warn", "Door schedule review switched to native text fallback.", "Door schedule review")
        call1 = _openai_json_call(
            "Door schedule text fallback",
            [
                {"role": "system", "content": STAGED_DOOR_SYSTEM},
                {"role": "user", "content": [{"type": "input_text", "text": f"Project scope: {scope}\n\nThe full PDF request could not complete. Extract every visible door schedule row from this native PDF text. Preserve text exactly and do not infer.\n\nPDF_TEXT:\n{text}\n\nReturn JSON: {{ \"doors\": [...] }}"}]},
            ],
            32000,
            "medium",
            logs,
            api_key=api_key,
        )
    raw_doors = call1["parsed"].get("doors") or call1["parsed"].get("rows") or call1["parsed"].get("door_analysis") or []
    doors = [normalize_door(d) for d in raw_doors if isinstance(d, dict)]
    door_rescue_elapsed = 0
    door_rescue_stats = {"doors_added": 0, "hardware_sets_filled": 0}
    if should_run_door_field_rescue(file_bytes, doors):
        rescued_doors, door_rescue_elapsed = rescue_door_hardware_fields_from_crops(file_bytes, logs, api_key)
        if rescued_doors:
            door_rescue_stats = merge_rescued_door_fields(doors, rescued_doors)
            if door_rescue_stats["hardware_sets_filled"] or door_rescue_stats["doors_added"]:
                _log(logs, "ok", f"Door completeness check filled {door_rescue_stats['hardware_sets_filled']} hardware set value(s).", "Door completeness check")
    project_meta = {
        "project_name": call1["parsed"].get("project_name") or (call1["parsed"].get("project") or {}).get("name"),
        "architect": call1["parsed"].get("architect") or (call1["parsed"].get("project") or {}).get("architect"),
    }
    door_ctx = {
        "general_notes": [x for x in call1["parsed"].get("general_notes") or [] if isinstance(x, str) and x.strip()],
        "schedule_legend": call1["parsed"].get("schedule_legend") if isinstance(call1["parsed"].get("schedule_legend"), dict) else {},
        "keying_notes": [x for x in call1["parsed"].get("keying_notes") or [] if isinstance(x, str) and x.strip()],
    }

    try:
        hw_content = (
            [{"type": "input_text", "text": f"Project scope: {scope}\n\nRead this native PDF text end-to-end. Extract every visible hardware set / hardware group per your system instructions, with every visible line item. Do not map doors and do not create RFIs in this step.\n\nAlso capture sheet-level context: hardware_preamble, keying_notes, and hardware_legend.\n\nPDF_TEXT:\n{native_text()}\n\nReturn JSON: {{ \"hardware_preamble\": [...], \"keying_notes\": [...], \"hardware_legend\": {{...}}, \"hardware_sets\": [...] }}"}]
            if use_native_text_primary
            else [
                {"type": "input_file", "filename": filename, "file_data": pdf_data_url()},
                {"type": "input_text", "text": f"Project scope: {scope}\n\nRead the attached PDF end-to-end. Extract every visible hardware set / hardware group per your system instructions, with every line item. Do not map doors and do not create RFIs in this step.\n\nAlso capture sheet-level context: hardware_preamble, keying_notes, and hardware_legend.\n\nReturn JSON: {{ \"hardware_preamble\": [...], \"keying_notes\": [...], \"hardware_legend\": {{...}}, \"hardware_sets\": [...] }}"},
            ]
        )
        call2 = _openai_json_call(
            "Hardware set review",
            [
                {"role": "system", "content": STAGED_HW_SYSTEM},
                {"role": "user", "content": hw_content},
            ],
            48000,
            "medium" if use_native_text_primary else "high",
            logs,
            api_key=api_key,
        )
    except ExtractionError as exc:
        text = native_text()
        if not text.strip() or not _can_fallback_after_error(exc):
            raise
        _log(logs, "warn", "Hardware set review switched to native text fallback.", "Hardware set review")
        call2 = _openai_json_call(
            "Hardware set text fallback",
            [
                {"role": "system", "content": STAGED_HW_SYSTEM},
                {"role": "user", "content": [{"type": "input_text", "text": f"Project scope: {scope}\n\nThe full PDF request could not complete. Extract every visible hardware set / hardware group and line item from this native PDF text. Do not map doors.\n\nPDF_TEXT:\n{text}\n\nReturn JSON: {{ \"hardware_preamble\": [...], \"keying_notes\": [...], \"hardware_legend\": {{...}}, \"hardware_sets\": [...] }}"}]},
            ],
            32000,
            "medium",
            logs,
            api_key=api_key,
        )
    raw_sets = call2["parsed"].get("hardware_sets") or call2["parsed"].get("sets") or []
    sets = dedupe_sets([normalize_set(s) for s in raw_sets if isinstance(s, dict)])
    hw_ctx = {
        "hardware_preamble": [x for x in call2["parsed"].get("hardware_preamble") or [] if isinstance(x, str) and x.strip()],
        "keying_notes": [x for x in call2["parsed"].get("keying_notes") or [] if isinstance(x, str) and x.strip()],
        "hardware_legend": call2["parsed"].get("hardware_legend") if isinstance(call2["parsed"].get("hardware_legend"), dict) else {},
    }
    rescue_elapsed = 0
    rescue_attempted = False
    rescue_stats = {"sets_added": 0, "items_added": 0}
    if should_run_hardware_rescue(doors, sets, truncated=bool(call2["truncated"])):
        rescue_attempted = True
        rescue_known_ids = known_hardware_set_ids(doors, sets)
        rescued_sets, rescue_elapsed = rescue_hardware_sets_from_crops(
            file_bytes,
            filename,
            rescue_known_ids,
            logs,
            api_key,
        )
        if rescued_sets:
            sets, rescue_stats = merge_rescued_sets(sets, rescued_sets, allowed_ids=rescue_known_ids)
            if rescue_stats["items_added"]:
                _log(logs, "ok", f"Completeness check added {rescue_stats['items_added']} hardware item row(s).", "Completeness check")
        still_empty = referenced_empty_set_ids(doors, sets)
        if still_empty:
            text_sets, text_elapsed = rescue_hardware_sets_from_text(
                file_bytes,
                rescue_known_ids,
                still_empty,
                logs,
                api_key,
            )
            rescue_elapsed += text_elapsed
            if text_sets:
                sets, text_stats = merge_rescued_sets(sets, text_sets, allowed_ids=rescue_known_ids)
                rescue_stats["sets_added"] += text_stats["sets_added"]
                rescue_stats["items_added"] += text_stats["items_added"]

    def dedupe_strings(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            key = item.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(item)
        return out

    legend = {str(k).strip().upper(): str(v).strip() for k, v in {**door_ctx["schedule_legend"], **hw_ctx["hardware_legend"]}.items() if str(v).strip()}
    sheet_context = {
        "general_notes": dedupe_strings(door_ctx["general_notes"]),
        "hardware_preamble": dedupe_strings(hw_ctx["hardware_preamble"]),
        "keying_notes": dedupe_strings([*door_ctx["keying_notes"], *hw_ctx["keying_notes"]]),
        "legend": legend,
    }
    mapping, qa_issues = map_doors_hardware(doors, sets, general_notes=sheet_context.get("general_notes"))
    elapsed_core = int(call1["elapsed"] + door_rescue_elapsed + call2["elapsed"] + rescue_elapsed)
    project_summary = rollup_summary(doors, sets, scope, elapsed_core, project_meta)

    project_risks: list[dict[str, Any]] = []
    rfi_log: list[dict[str, Any]] = []
    call3_elapsed = 0
    call3_skipped = not run_rfis
    if run_rfis:
        try:
            payload = {
                "scope": scope,
                "sheet_context": sheet_context,
                "doors": [{"mark": d.get("mark"), "room_or_location": d.get("room_or_location"), "door_type": d.get("door_type"), "size": d.get("size"), "door_material": d.get("door_material"), "fire_rating": d.get("fire_rating"), "hardware_set": d.get("hardware_set"), "closer": d.get("closer"), "electric_or_access_control": d.get("electric_or_access_control"), "remarks": d.get("remarks"), "existing_to_remain": d.get("existing_to_remain")} for d in doors],
                "hardware_sets": [{"hardware_set": s.get("hardware_set"), "status": s.get("status"), "raw_status": s.get("raw_status"), "item_count": len(s.get("items") or []), "item_descriptions": [it.get("desc") for it in s.get("items") or [] if it.get("desc")]} for s in sets],
                "mapping_qa": qa_issues,
            }
            call3 = _openai_json_call(
                "Bid review",
                [
                    {"role": "system", "content": STAGED_RFI_SYSTEM},
                    {"role": "user", "content": [{"type": "input_text", "text": "Review the following extracted data (already in canonical form). Produce only real-issue RFIs and coordination notes per your system instructions. Do not invent issues for clean rows.\n\nEXTRACTED_DATA:\n" + json.dumps(payload) + '\n\nReturn JSON: { "rfis": [...] }'}]},
                ],
                16000,
                "medium",
                logs,
                api_key=api_key,
            )
            call3_elapsed = call3["elapsed"]
            rfis = call3["parsed"].get("rfis") if isinstance(call3["parsed"].get("rfis"), list) else []
            for item in rfis:
                if not isinstance(item, dict):
                    continue
                rfi_log.append({"priority": str(item.get("severity") or "medium").lower(), "category": item.get("category") or "General", "question": item.get("issue") or "", "affected_openings": item.get("affected_doors") if isinstance(item.get("affected_doors"), list) else [], "recommendation": item.get("recommendation") or "", "status": "Open", "reason": item.get("issue") or ""})
                project_risks.append({"severity": str(item.get("severity") or "medium").lower(), "category": item.get("category") or "General", "issue": item.get("issue") or "", "affected_openings": item.get("affected_doors") if isinstance(item.get("affected_doors"), list) else [], "recommendation": item.get("recommendation") or "", "status": "Open"})
        except ExtractionError as exc:
            call3_skipped = True
            _log(logs, "warn", f"Bid review could not complete: {exc}. Continuing with estimator recommendations.", "Bid review")
    else:
        _log(logs, "info", "Bid review skipped.", "Bid review")

    synth = synthesize(doors, sets, scope, sheet_context)
    recs = synth["recs"]
    for issue in qa_issues:
        msg = issue.get("message")
        if msg and msg not in recs["coordination_items"]:
            recs["coordination_items"].append(msg)
    # Keep LLM RFIs first, then heuristic coverage.
    project_risks.extend(synth["risks"])
    rfi_log.extend(synth["rfis"])

    total_items = sum(len(s.get("items") or []) for s in sets)
    total_elapsed = elapsed_core + call3_elapsed
    _log(logs, "ok", f"Secure analysis done - {len(doors)} doors - {len(sets)} sets - {total_items} items - {len(project_risks)} risks - {len(rfi_log)} RFIs - {total_elapsed}s total.", "done")
    return {
        "analysis": {
            "project_summary": project_summary,
            "door_analysis": doors,
            "hardware_set_review": sets,
            "door_hardware_mapping": mapping,
            "sheet_context": sheet_context,
            "project_risks": project_risks,
            "rfi_log": rfi_log,
            "estimator_notes": synth["notes"],
            "bid_recommendations": recs,
        },
        "qa": {
            "pdf_type": "SECURE_BACKEND_STAGED_PIPELINE",
            "pipeline": "secure-backend-staged",
            "pipeline_steps": [
                {"step": 1, "kind": "llm", "label": "Door schedule extraction", "elapsed_seconds": call1["elapsed"], "truncated": call1["truncated"], "output_count": len(doors)},
                {"step": 2, "kind": "llm", "label": "Door completeness check", "skipped": not bool(door_rescue_elapsed), "elapsed_seconds": door_rescue_elapsed, "output_count": door_rescue_stats["hardware_sets_filled"]},
                {"step": 3, "kind": "llm", "label": "Hardware set extraction", "elapsed_seconds": call2["elapsed"], "truncated": call2["truncated"], "output_count": len(sets)},
                {"step": 4, "kind": "llm", "label": "Completeness check", "skipped": not rescue_attempted, "elapsed_seconds": rescue_elapsed, "output_count": rescue_stats["items_added"]},
                {"step": 5, "kind": "code", "label": "Door -> hardware mapping", "output_count": len(mapping)},
                {"step": 6, "kind": "code", "label": "Rollup"},
                {"step": 7, "kind": "llm", "label": "RFI / coordination review", "skipped": call3_skipped, "elapsed_seconds": call3_elapsed, "output_count": len(rfi_log)},
            ],
            "model": settings.openai_model,
            "elapsed_seconds": total_elapsed,
            "mapping_qa_issues": qa_issues,
            "raw_transcription": {"doors": [{"mark": d.get("mark")} for d in doors], "hardware_sets": [{"id": s.get("hardware_set"), "item_count": len(s.get("items") or [])} for s in sets]},
            "truncated": bool(call1["truncated"] or call2["truncated"]),
            "reasoning_succeeded": True,
            "extraction_complete": not call1["truncated"] and not call2["truncated"],
            "extraction_failures": [],
        },
        "logs": logs,
    }
