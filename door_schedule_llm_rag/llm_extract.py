"""
LLM extraction: call Ollama and parse JSON array of door/hardware rows.
Handles retries, JSON repair, and validation.
"""
import json
import re
import logging
import time
from typing import List, Optional

import requests

from config import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    GROQ_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    LLM_TEMPERATURE,
    OLLAMA_FALLBACK_MODELS,
)
from schema import DoorScheduleRow, HardwareComponentRow, detect_pair_from_width

logger = logging.getLogger("llm")

MAX_RETRIES = 2


# ═══════════════════════════════════════════════════════════════════
#  Runtime LLM Configuration (overridable from Streamlit UI)
# ═══════════════════════════════════════════════════════════════════
class LLMConfig:
    """Runtime-overridable LLM settings. Defaults come from .env/config.py."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset to .env defaults."""
        self.provider = LLM_PROVIDER
        self.openai_model = OPENAI_MODEL
        self.groq_model = GROQ_MODEL
        self.ollama_model = OLLAMA_MODEL

    def set(self, provider: str, model: str = None):
        """Override provider and optionally model at runtime."""
        self.provider = provider.lower()
        if model:
            if self.provider == "openai":
                self.openai_model = model
            elif self.provider == "groq":
                self.groq_model = model
            elif self.provider == "ollama":
                self.ollama_model = model


# Singleton — importable from anywhere
llm_config = LLMConfig()


# ═══════════════════════════════════════════════════════════════════
#  Groq Backend
# ═══════════════════════════════════════════════════════════════════
def _groq_chat(system: str, user: str, force_json: bool = True, base64_image: Optional[str] = None) -> str:
    """Call Groq API using requests directly so we don't need the SDK."""
    if not GROQ_API_KEY:
        logger.error("Groq API key missing!")
        return ""
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    user_content = user
    if base64_image:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": LLM_TEMPERATURE,
    }
        
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 429:
                logger.warning("[Groq] Rate limit hit. Waiting 5s...")
                time.sleep(5)
                continue
            r.raise_for_status()
            content = r.json()["choices"][0]["message"].get("content")
            if content and content.strip():
                return content
        except Exception as e:
            logger.warning("[Groq] Call failed: %s", e)
            if attempt < MAX_RETRIES:
                time.sleep(2)
    return ""


# ═══════════════════════════════════════════════════════════════════
#  OpenAI Backend
# ═══════════════════════════════════════════════════════════════════
def _openai_chat(system: str, user: str, force_json: bool = True, base64_image: Optional[str] = None) -> str:
    """Call OpenAI API (GPT-4o-mini, GPT-4o, etc.)."""
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key missing!")
        return ""

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    user_content = user
    if base64_image:
        user_content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]

    # Smart escalation: If the table string is dense (>5,000 chars), 
    # we force gpt-4o for pure text semantic mapping even if there's no image.
    active_model = "gpt-4o" if (base64_image or len(user) > 5000) else OPENAI_MODEL
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": 12000,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            # Increased timeout for intensive high-res image reasoning
            r = requests.post(url, headers=headers, json=payload, timeout=300)
            if r.status_code == 429:
                wait = min(2 ** attempt * 5, 60)
                logger.warning("[OpenAI] Rate limit hit. Waiting %ds...", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            choice = r.json()["choices"][0]
            content = choice["message"].get("content")
            if content and content.strip():
                return content
            logger.warning("[OpenAI] Empty content detected. Finish reason: %s, Refusal: %s", 
                           choice.get("finish_reason"), choice["message"].get("refusal"))
        except Exception as e:
            logger.warning("[OpenAI] Call failed (attempt %d): %s", attempt + 1, e)
            if attempt < MAX_RETRIES:
                time.sleep(2)
    return ""


# ═══════════════════════════════════════════════════════════════════
#  Ollama Backend (local, with model fallback)
# ═══════════════════════════════════════════════════════════════════
def _get_available_models() -> List[str]:
    """Auto-discover all models installed in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=5)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return []


def _build_model_chain() -> List[str]:
    chain = [OLLAMA_MODEL]
    if OLLAMA_FALLBACK_MODELS:
        for m in OLLAMA_FALLBACK_MODELS.split(","):
            m = m.strip()
            if m and m not in chain:
                chain.append(m)
    available = _get_available_models()
    for m in available:
        if m not in chain:
            chain.append(m)
    return chain


def _ollama_chat(system: str, user: str, model: Optional[str] = None, force_json: bool = True, base64_image: Optional[str] = None) -> str:
    """Call Ollama chat API with automatic model fallback."""
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    models_to_try = [model] if model else _build_model_chain()

    for model_name in models_to_try:
        effective_system = system
        if "qwen3" in model_name.lower():
            effective_system = "/no_think\n" + system

        msg = {"role": "user", "content": user}
        if base64_image:
            msg["images"] = [base64_image]

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": effective_system},
                msg,
            ],
            "stream": False,
            "options": {"temperature": LLM_TEMPERATURE, "num_predict": 4096},
        }
        if force_json:
            payload["format"] = "json"

        for attempt in range(MAX_RETRIES + 1):
            try:
                r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT)
                r.raise_for_status()
                content = (r.json().get("message") or {}).get("content")
                if content and content.strip():
                    return content
                logger.warning("[%s] Empty response (attempt %d)", model_name, attempt + 1)
            except requests.exceptions.Timeout:
                logger.warning("[%s] Timeout after %ds (attempt %d)", model_name, OLLAMA_TIMEOUT, attempt + 1)
                if attempt < MAX_RETRIES:
                    time.sleep(1)
            except requests.exceptions.RequestException as e:
                logger.error("[%s] Failed: %s", model_name, e)
                break

        if len(models_to_try) > 1:
            logger.warning("Model '%s' failed. Trying next...", model_name)

    return ""


# ═══════════════════════════════════════════════════════════════════
#  Unified LLM call & Normalization
# ═══════════════════════════════════════════════════════════════════

def clean_hw_id(raw_id: str) -> str:
    """Strip 'HW.', 'HW-', 'SET', 'GROUP', etc. to leave clean alphanumeric."""
    if not raw_id or str(raw_id).lower() in ("none", "null", "undefined", "n/a"):
        return ""
    s = str(raw_id).upper().strip()
    s = re.sub(r'^(HW[\.\-\s]*|HARDWARE[\.\-\s]*|SET[\.\-\s]*|GROUP[\.\-\s]*)', '', s)
    s = s.strip('. -')
    return s

def _llm_chat(system: str, user: str, force_json: bool = True, base64_image: Optional[str] = None) -> str:
    """
    Call the configured LLM provider.
    Uses runtime llm_config overrides (from Streamlit UI) if set.
    Fallback chain: configured provider → Ollama (local).
    """
    provider = llm_config.provider

    if provider == "openai":
        model = "gpt-4o" if base64_image else llm_config.openai_model
        
        logger.info("Using OpenAI (%s)", model)
        ans = _openai_chat(system, user, force_json=force_json, base64_image=base64_image)
        if ans:
            return ans
        logger.warning("OpenAI failed, falling back to Ollama")

    elif provider == "groq":
        model = llm_config.groq_model
        logger.info("Using Groq (%s)", model)
        ans = _groq_chat(system, user, force_json=force_json, base64_image=base64_image)
        if ans:
            return ans
        logger.warning("Groq failed, falling back to Ollama")

    logger.info("Using Ollama (%s)", llm_config.ollama_model)
    return _ollama_chat(system, user, force_json=force_json, base64_image=base64_image)


def _clean_json(s: str) -> str:
    """
    Attempt to repair common JSON issues from LLM output:
    - Trailing commas
    - Single quotes instead of double
    - Unquoted keys
    - Missing closing brackets
    """
    if not s: return ""
    s = s.strip()
    s = s.strip('`')
    
    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Ensure closing bracket
    open_brackets = s.count("[") - s.count("]")
    if open_brackets > 0:
        s += "]" * open_brackets
    open_braces = s.count("{") - s.count("}")
    if open_braces > 0:
        s += "}" * open_braces

    return s


def _repair_json(raw: str) -> str:
    """
    Attempt to repair common JSON issues from LLM output:
    - Trailing commas
    - Single quotes instead of double
    - Unquoted keys
    - Missing closing brackets
    """
    s = raw.strip()

    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Ensure closing bracket
    open_brackets = s.count("[") - s.count("]")
    if open_brackets > 0:
        s += "]" * open_brackets
    open_braces = s.count("{") - s.count("}")
    if open_braces > 0:
        s += "}" * open_braces

    return s


# ── Field name normalization ──
_FIELD_MAP = {
    "number": "door_number", "door_number": "door_number",
    "door number": "door_number", "door_no": "door_number",
    "mark": "door_number", "door mark": "door_number", "door_mark": "door_number",
    "id": "door_number", "door_id": "door_number", "door id": "door_number",
    "room name": "room_name", "room_name": "room_name", "location": "room_name",
    "room": "room_name",
    "door type": "door_type", "door_type": "door_type", "type": "door_type",
    "frame type": "frame_type", "frame_type": "frame_type", "frame": "frame_type",
    "frame material": "frame_type",
    "width": "door_width", "door_width": "door_width", "door width": "door_width",
    "height": "door_height", "door_height": "door_height", "door height": "door_height",
    "hardware set": "hardware_set", "hardware_set": "hardware_set",
    "hw set": "hardware_set", "hdwr set": "hardware_set",
    "fire rating": "fire_rating", "fire_rating": "fire_rating",
    "fire rate": "fire_rating",
    "comments": "remarks", "remarks": "remarks", "notes": "remarks",
    "material": "door_slab_material", "door_slab_material": "door_slab_material",
    "slab material": "door_slab_material",
    "finish": "finish", "vision panel": "vision_panel", "vision_panel": "vision_panel",
    "glazing": "glazing_type", "glazing_type": "glazing_type",
    "level": "level_area", "level_area": "level_area", "area": "level_area",
    "is_pair": "is_pair", "is pair": "is_pair",
    "door_leaves": "door_leaves", "leaves": "door_leaves",
    "frame_width": "frame_width", "frame width": "frame_width",
    "frame_height": "frame_height", "frame height": "frame_height",
    "head_jamb_sill_detail": "head_jamb_sill_detail",
    "keyed_notes": "keyed_notes",
    # Hardware fields
    "hardware_set_id": "hardware_set_id", "set": "hardware_set_id",
    "set_id": "hardware_set_id", "set id": "hardware_set_id",
    "hardware_set_name": "hardware_set_name", "function": "hardware_set_name",
    "qty": "qty", "quantity": "qty",
    "unit": "unit",
    "description": "description", "desc": "description", "component": "description",
    "catalog_number": "catalog_number", "catalog number": "catalog_number",
    "catalog no": "catalog_number", "catalog no.": "catalog_number", "model": "catalog_number",
    "finish_code": "finish_code", "finish code": "finish_code",
    "manufacturer_code": "manufacturer_code", "manufacturer": "manufacturer_code",
    "mfr": "manufacturer_code",
}


def _normalize_row(row: dict) -> dict:
    """Normalize field names from LLM variations to our schema."""
    normalized = {"extra_fields": {}}
    for key, value in row.items():
        clean_key = key.lower().strip()
        if clean_key == "extra_fields" and isinstance(value, dict):
            normalized["extra_fields"].update(value)
            continue

        norm_key = _FIELD_MAP.get(clean_key)
        if norm_key:
            normalized[norm_key] = value
        else:
            normalized["extra_fields"][key] = value
            
    # If no extra fields were found, we can leave it empty
    return normalized


def _find_rows_in_json(obj, depth: int = 0) -> Optional[List[dict]]:
    """
    Recursively search a parsed JSON object for an array of dicts.
    Handles nested structures like {"Door Schedule": {"Doors": [...]}}.
    """
    if depth > 3:
        return None

    if isinstance(obj, list):
        # Handle empty lists correctly
        if not obj:
            return []
        # If it's a list of dicts, it's our target array
        if isinstance(obj[0], dict):
            # Qwen sometimes nests inside {"Door Schedule": {"Doors": [...]}}
            # Return normalized rows directly
            return [_normalize_row(r) for r in obj if isinstance(r, dict)]
        return None

    if isinstance(obj, dict):
        # If this dict looks like a single row, return it as a list
        row_keys = {"door_number", "number", "hardware_set_id", "set_id", "opening", "room", "door"}
        if any(k.lower() in row_keys for k in obj.keys()):
            return [_normalize_row(obj)]

        # Find arrays in dict properties
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return [_normalize_row(r) for r in v if isinstance(r, dict)]
            
        # Recursive deep search if not found
        for v in obj.values():
            if isinstance(v, dict):
                result = _find_rows_in_json(v, depth + 1)
                if result is not None:
                    return result

    return None


def _extract_json_array(raw: str) -> List[dict]:
    """Pull a JSON array from LLM output, with repair attempts.
    Handles both bare arrays [...] and wrapped objects {"rows": [...]}.
    """
    raw = raw.strip()
    if not raw:
        return []

    # Strip reasoning blocks (e.g. <think>...</think> from Qwen3 / DeepSeek-R1)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip markdown code block wrappers
    if "```json" in raw:
        raw = raw.split("```json", 1)[1]
        if "```" in raw:
            raw = raw.split("```", 1)[0]
        raw = raw.strip()
    elif "```" in raw:
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1].strip()
        elif len(parts) == 2:
            raw = parts[1].strip()

    # Try parsing the whole thing first (handles {"rows": [...]})
    try:
        parsed = json.loads(raw)
        found = _find_rows_in_json(parsed)
        if found is not None:
            return found
    except json.JSONDecodeError:
        pass

    # Find the JSON array manually
    match = re.search(r"\[[\s\S]*\]", raw)
    if not match:
        match_obj = re.search(r"\{[\s\S]*\}", raw)
        if match_obj:
            raw = "[" + match_obj.group(0) + "]"
        else:
            return []
    else:
        raw = match.group(0)

    # Try parsing
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except json.JSONDecodeError:
        pass

    # Try with repair
    repaired = _repair_json(raw)
    try:
        result = json.loads(repaired)
        if isinstance(result, list):
            return result
        return []
    except json.JSONDecodeError as e:
        logger.debug("JSON parse failed even after repair: %s", e)
        return []


def extract_doors_llm(system: str, user: str, base64_image: Optional[str] = None) -> List[dict]:
    """
    Call LLM for door extraction and return validated door rows.
    Applies deterministic pair detection.
    """
    content = _llm_chat(system, user, base64_image=base64_image)
    if not content:
        return []

    rows = _extract_json_array(content)
    out = []

    for r in rows:
        if not isinstance(r, dict):
            continue
        door_number = str(r.get("door_number") or "").strip()
        if not door_number:
            continue

        # Skip header-like entries
        if door_number.upper() in ("DOOR", "MARK", "NO", "NUMBER", "DOOR NUMBER", "DOOR NO"):
            continue

        # Deterministic pair detection (override LLM's guess)
        width = r.get("door_width")
        dtype = r.get("door_type")
        is_pair = detect_pair_from_width(width, dtype)

        try:
            # ── Pre-process: Promote known schema fields from extra_fields ──
            extra = r.get("extra_fields")
            if isinstance(extra, dict):
                PROMOTABLE = {
                    "door_thickness", "door_material", "door_finish",
                    "frame_material", "frame_finish", "elevation",
                    "door_type", "room_name", "fire_rating",
                    "hardware_set", "door_width", "door_height",
                    "frame_type", "finish", "remarks",
                }
                for key in list(extra.keys()):
                    if key in PROMOTABLE and extra[key] is not None:
                        # Only promote if the top-level value is empty/null
                        if r.get(key) is None:
                            r[key] = extra.pop(key)
                        else:
                            extra.pop(key)  # Discard duplicate


            row = DoorScheduleRow(
                door_number=door_number,
                level_area=r.get("level_area"),
                room_name=r.get("room_name"),
                door_type=r.get("door_type"),
                frame_type=r.get("frame_type"),
                frame_width=r.get("frame_width"),
                frame_height=r.get("frame_height"),
                door_width=width,
                door_height=r.get("door_height"),
                hardware_set=clean_hw_id(r.get("hardware_set")),
                fire_rating=r.get("fire_rating"),
                head_jamb_sill_detail=r.get("head_jamb_sill_detail"),
                keyed_notes=r.get("keyed_notes"),
                remarks=r.get("remarks"),
                door_slab_material=r.get("door_slab_material"),
                vision_panel=r.get("vision_panel"),
                glazing_type=r.get("glazing_type"),
                finish=r.get("finish"),
                door_thickness=r.get("door_thickness"),
                door_material=r.get("door_material"),
                door_finish=r.get("door_finish"),
                frame_material=r.get("frame_material"),
                frame_finish=r.get("frame_finish"),
                elevation=r.get("elevation"),
                is_pair=is_pair,
                door_leaves=2 if is_pair else 1,
                extra_fields=r.get("extra_fields", {}),
            )
            out.append(row.model_dump())
        except Exception as e:
            logger.debug("Validation warning for door %s: %s", door_number, e)
            # Still include with minimal fields
            out.append({
                "door_number": door_number,
                "is_pair": is_pair,
                "door_leaves": 2 if is_pair else 1,
                **{k: v for k, v in r.items() if k != "door_number"},
            })

    return out


def extract_hardware_llm(system: str, user: str, base64_image: Optional[str] = None) -> List[dict]:
    """
    Call LLM for hardware extraction and return validated component rows.
    Quantities are preserved AS-IS from the document.
    """
    content = _llm_chat(system, user, base64_image=base64_image)
    if not content:
        return []

    rows = _extract_json_array(content)
    out = []

    for r in rows:
        if not isinstance(r, dict):
            continue

        hw_id = clean_hw_id(r.get("hardware_set_id"))
        desc = str(r.get("description") or "").strip()
        if not hw_id and not desc:
            continue

        # Skip header rows
        if desc.upper() in ("DESCRIPTION", "COMPONENT", "ITEM"):
            continue

        try:
            row = HardwareComponentRow(
                hardware_set_id=hw_id or "?",
                hardware_set_name=r.get("hardware_set_name"),
                qty=r.get("qty"),
                unit=r.get("unit"),
                description=desc or "—",
                catalog_number=r.get("catalog_number"),
                finish_code=r.get("finish_code"),
                manufacturer_code=r.get("manufacturer_code"),
                notes=r.get("notes"),
                extra_fields=r.get("extra_fields", {}),
            )
            out.append(row.model_dump())
        except Exception as e:
            logger.debug("Validation warning for hardware: %s", e)
            out.append({
                "hardware_set_id": hw_id or "?",
                "qty": max(1, int(float(r.get("qty") or 1))),
                "unit": "EA",
                "description": desc or "—",
                **{k: v for k, v in r.items()
                   if k not in ("hardware_set_id", "qty", "unit", "description")},
            })

    return out
