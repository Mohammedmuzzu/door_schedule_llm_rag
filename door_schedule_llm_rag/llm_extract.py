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

# When True, the pipeline falls back to Ollama (local) on OpenAI/Groq failure.
# On hosts where Ollama is slow, wrong-model-pulled, or simply not running,
# this fallback wastes minutes per call with 3× 180s timeouts. Default is
# disabled; override by setting LLM_OLLAMA_FALLBACK=1 in the environment.
import os as _os  # local alias to avoid touching top-of-file import set
ENABLE_OLLAMA_FALLBACK = _os.environ.get("LLM_OLLAMA_FALLBACK", "0") == "1"

# Rate-limit backoff (OpenAI): these retries run *in addition* to MAX_RETRIES.
# Rationale: we'd rather wait ~2 minutes for the rate limit to clear than
# fall through to a broken Ollama which could burn 10+ minutes.
OPENAI_RATELIMIT_RETRIES = 6
OPENAI_RATELIMIT_MAX_WAIT = 60  # seconds per attempt
_OLLAMA_HEALTHY: Optional[bool] = None  # lazy-cached health check

_NULL_LIKE = {
    "",
    "-",
    "--",
    "---",
    "----",
    "—",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "UNKNOWN",
    "NOT SHOWN",
    "NOT PROVIDED",
    "TBD",
    "?",
}

_HW_COMPONENT_TERMS = re.compile(
    r"\b(?:HINGE|BUTT|PIVOT|CLOSER|LOCK|LOCKSET|LATCH|LATCHSET|MORTISE|CYLINDER|"
    r"DEADBOLT|DEADLOCK|STRIKE|THRESHOLD|WEATHER\s*STRIP|WEATHERSTRIP|SEAL|GASKET|"
    r"KICK\s*PLATE|KICKPLATE|PUSH\s*PLATE|PULL\s*PLATE|STOP|SILENCER|PANIC|EXIT\s*DEVICE|"
    r"COORDINATOR|FLUSH\s*BOLT|SURFACE\s*BOLT|BOLT|OVERHEAD\s*STOP|POWER\s*TRANSFER|"
    r"ELECTRIC\s*STRIKE|ASTRAGAL|HOLDER|VIEWER|OPERATOR|CLOSING\s*DEVICE)\b",
    re.IGNORECASE,
)
_HW_NOISE_TERMS = re.compile(
    r"\b(?:DOOR\s+SCHEDULE|WINDOW\s+SCHEDULE|HARDWARE\s+SCHEDULE|SEE\s+HARDWARE|"
    r"REFER\s+TO\s+HARDWARE|PROJECT\s+NO|DRAWN\s+BY|CHECKED\s+BY|SHEET\s+NO|"
    r"REVISION|GENERAL\s+NOTES?|TITLE\s+BLOCK|ARCHITECT|ENGINEER|SCALE|DATE|"
    r"ROOM\s+NAME|DOOR\s+NO|DOOR\s+NUMBER|FRAME\s+TYPE|FIRE\s+RATING|FINISH\s+TAG|"
    r"EQUIPMENT\s*/\s*FIXTURE|LEGEND)\b",
    re.IGNORECASE,
)
_EQUIPMENT_NOISE_TERMS = re.compile(
    r"\b(?:TV|TELEVISION|ORGANIZER|TRASH\s+CAN|GLOVE\s+BOX|SHARPS|HEIGHT\s+MEASURER|"
    r"GRAB\s+BARS?|HAND\s+SANITIZER|SOAP\s+DISPENSER|PAPER\s+TOWEL|TOILET\s+PAPER|"
    r"CORK\s+BOARD|UTILITY\s+PLASTIC\s+CART|OTOSCOPE|SPECULA|MIRROR|ADA\s+SIGNAGE|"
    r"HIGH\s+TABLE|WATER\s+DISPENSER|REFRIGERATOR|FREEZER|UNDER\s+CABINET|CHAIR|"
    r"EQUIPMENT|FIXTURE|FURNITURE|APPLIANCE)\b",
    re.IGNORECASE,
)
_HW_HEADER_ONLY = {
    "DESCRIPTION",
    "COMPONENT",
    "ITEM",
    "QTY",
    "QUANTITY",
    "UNIT",
    "FINISH",
    "MFR",
    "MANUFACTURER",
    "CATALOG",
    "CATALOG NUMBER",
    "HARDWARE",
    "HARDWARE SET",
    "HARDWARE GROUP",
    "SEE HARDWARE SCHED",
    "SEE HARDWARE SCHEDULE",
}


def _blank_if_unknown(value):
    """Normalize low-confidence placeholder strings to None."""
    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip()
        return None if clean.upper() in _NULL_LIKE else clean
    return value


def _clean_extra_fields(extra):
    if not isinstance(extra, dict):
        return {}
    return {k: _blank_if_unknown(v) for k, v in extra.items() if _blank_if_unknown(v) is not None}


def is_probable_hardware_component(row: dict) -> bool:
    """Return False for obvious title/header/note rows hallucinated as hardware."""
    desc = str(_blank_if_unknown(row.get("description")) or "").strip()
    hw_id = str(_blank_if_unknown(row.get("hardware_set_id")) or "").strip()
    catalog = str(_blank_if_unknown(row.get("catalog_number")) or "").strip()
    manufacturer = str(_blank_if_unknown(row.get("manufacturer_code")) or "").strip()
    qty = _blank_if_unknown(row.get("qty"))
    qty_raw = _blank_if_unknown(row.get("qty_raw"))
    desc_upper = re.sub(r"\s+", " ", desc.upper()).strip(" .:-")
    hw_upper = re.sub(r"\s+", " ", hw_id.upper()).strip(" .:-")
    combined_upper = " ".join(
        str(_blank_if_unknown(row.get(field)) or "").upper()
        for field in ("description", "catalog_number", "manufacturer_code", "notes")
    )
    if not desc_upper:
        return False
    if desc_upper in _HW_HEADER_ONLY:
        return False
    has_component_word = bool(_HW_COMPONENT_TERMS.search(desc_upper))
    if _EQUIPMENT_NOISE_TERMS.search(combined_upper):
        return False
    if re.fullmatch(r"E\d+[A-Z]?", hw_upper) and not has_component_word:
        return False
    if hw_upper in {"", "?", "HARDWARE", "HARDWARE SCHEDULE", "SCHEDULE"} and not catalog and not manufacturer:
        if not has_component_word:
            return False
    if _HW_NOISE_TERMS.search(desc_upper):
        return False
    if _HW_NOISE_TERMS.search(combined_upper):
        return False
    if desc_upper.startswith(("SEE ", "REFER ", "NOTE:", "NOTES:", "GENERAL NOTE")):
        return False

    has_part_evidence = bool(catalog or manufacturer or qty or qty_raw)
    # Vendor-specific rows sometimes omit a generic noun but include catalog,
    # manufacturer, or quantity evidence. Keep those, but reject naked labels.
    if not has_component_word and not has_part_evidence:
        return False
    return True


def _estimate_tokens(*parts: object) -> int:
    """Cheap cross-provider token estimate. Good enough for budget routing."""
    chars = sum(len(str(part or "")) for part in parts)
    return max(1, chars // 4)


def _model_context_limit(model: str) -> int:
    override = _os.environ.get("LLM_CONTEXT_TOKENS")
    if override:
        try:
            return max(4096, int(override))
        except ValueError:
            pass

    name = (model or "").lower()
    if name.startswith(("gpt-4o", "gpt-4.1", "gpt-5", "o1", "o3")):
        return 128000
    if "llama-3.3" in name or "70b" in name:
        return 128000
    if "qwen3-vl" in name or "qwen3" in name:
        return 32768
    if "qwen2.5" in name:
        return 32768
    if "llama3.1" in name:
        return 128000
    return 8192


def _max_output_cap(model: str) -> int:
    override = _os.environ.get("LLM_MAX_OUTPUT_TOKENS")
    if override:
        try:
            return max(512, int(override))
        except ValueError:
            pass
    name = (model or "").lower()
    if name.startswith(("gpt-4o", "gpt-4.1", "gpt-5", "o1", "o3")):
        return 12000
    if "qwen3-vl" in name:
        return 4096
    if "qwen" in name or "llama" in name or "mistral" in name:
        return 6144
    return 4096


def _output_token_budget(model: str, system: str, user: str, base64_image: Optional[str] = None) -> int:
    prompt_tokens = _estimate_tokens(system, user) + (1200 if base64_image else 0)
    ctx = _model_context_limit(model)
    cap = _max_output_cap(model)
    # Keep a reserve so providers do not reject dense architectural pages.
    available = max(512, ctx - prompt_tokens - 768)
    return max(512, min(cap, available))


def _ollama_num_ctx(model: str, system: str, user: str, base64_image: Optional[str], output_tokens: int) -> int:
    override = _os.environ.get("OLLAMA_NUM_CTX")
    if override:
        try:
            return max(4096, int(override))
        except ValueError:
            pass
    needed = _estimate_tokens(system, user) + output_tokens + (1600 if base64_image else 0) + 512
    return max(4096, min(_model_context_limit(model), needed))


def _ollama_is_healthy() -> bool:
    """Cheap health probe so we don't waste minutes on a dead Ollama."""
    global _OLLAMA_HEALTHY
    if _OLLAMA_HEALTHY is not None:
        return _OLLAMA_HEALTHY
    try:
        r = requests.get(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags",
            timeout=2,
        )
        _OLLAMA_HEALTHY = r.status_code == 200 and bool(r.json().get("models"))
    except Exception:
        _OLLAMA_HEALTHY = False
    if not _OLLAMA_HEALTHY:
        logger.info(
            "Ollama probe failed — fallback disabled for this process "
            "(set LLM_OLLAMA_FALLBACK=1 and ensure `ollama serve` is running to enable)."
        )
    return _OLLAMA_HEALTHY


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

    active_model = llm_config.groq_model or GROQ_MODEL
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": _output_token_budget(active_model, system, user, base64_image),
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
def _resolve_openai_model(base64_image: Optional[str], force_model: Optional[str]) -> str:
    """Resolve the best OpenAI model based on user selection, vision needs, and rescue escalations."""
    current_model = llm_config.openai_model
    
    # 1. If agent explicitly requested gpt-4o (heuristic rescue/escalation)
    if force_model == "gpt-4o":
        rescue_model = _os.environ.get("OPENAI_RESCUE_MODEL", "gpt-4o")
        if current_model == "gpt-4o-mini":
            return rescue_model
        elif current_model.endswith("-mini") or ".mini" in current_model:
            return rescue_model
        elif current_model == "gpt-5.5-instant":
            return "gpt-5.5"
        elif current_model == "o1-mini":
            return "o1"
        else:
            return current_model  # Trust the user's flagship model choice
            
    # 2. If forced some other specific model
    if force_model:
        return force_model
        
    # 3. Vision requirement (mini struggles with complex blueprints)
    if base64_image and current_model == "gpt-4o-mini":
        return "gpt-4o"
        
    # 4. Default: User's UI selection
    return current_model


def _openai_chat(system: str, user: str, force_json: bool = True, base64_image: Optional[str] = None, force_model: Optional[str] = None) -> str:
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

    # Model routing is handled upstream by _resolve_openai_model
    active_model = force_model if force_model else llm_config.openai_model
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }
    
    output_tokens = _output_token_budget(active_model, system, user, base64_image)

    # Newer reasoning models (o1, o3, gpt-5+) deprecated max_tokens and do not support temperature overrides
    if active_model.startswith(("o1", "o3", "gpt-5")):
        payload["max_completion_tokens"] = output_tokens
    else:
        payload["max_tokens"] = output_tokens
        payload["temperature"] = LLM_TEMPERATURE

    # Two independent retry budgets:
    #   * `attempt`: logical failures (network errors, empty responses)
    #   * `ratelimit_attempt`: HTTP 429s — these are transient throttles,
    #     not failures, so we happily wait much longer. Previously both
    #     counters shared a single loop, causing the pipeline to give up
    #     on the 3rd 429 (~35s total) instead of waiting through the
    #     minute-level OpenAI rate window.
    attempt = 0
    ratelimit_attempt = 0
    while True:
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=300)
            if r.status_code == 429:
                if ratelimit_attempt >= OPENAI_RATELIMIT_RETRIES:
                    logger.warning(
                        "[OpenAI] Rate limit retries exhausted after %d attempts. Giving up.",
                        ratelimit_attempt,
                    )
                    return ""
                wait = min(2 ** ratelimit_attempt * 5, OPENAI_RATELIMIT_MAX_WAIT)
                ratelimit_attempt += 1
                logger.warning(
                    "[OpenAI] Rate limit hit. Waiting %ds (attempt %d/%d)...",
                    wait, ratelimit_attempt, OPENAI_RATELIMIT_RETRIES,
                )
                time.sleep(wait)
                continue
            r.raise_for_status()
            choice = r.json()["choices"][0]
            content = choice["message"].get("content")
            if content and content.strip():
                return content
            logger.warning("[OpenAI] Empty content detected. Finish reason: %s, Refusal: %s",
                           choice.get("finish_reason"), choice["message"].get("refusal"))
            # fall through to attempt counter so we don't loop forever on empties
            attempt += 1
            if attempt > MAX_RETRIES:
                return ""
            time.sleep(2)
        except Exception as e:
            logger.warning("[OpenAI] Call failed (attempt %d): %s", attempt + 1, e)
            attempt += 1
            if attempt > MAX_RETRIES:
                return ""
            time.sleep(2)


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


def _is_ollama_vision_model(model_name: str) -> bool:
    name = (model_name or "").lower()
    return any(token in name for token in ("vl", "vision", "llava", "bakllava", "moondream", "minicpm-v", "gemma4"))


def _ollama_vision_chain(available: List[str]) -> List[str]:
    configured = _os.environ.get("OLLAMA_VISION_MODELS", "qwen3-vl:8b,gemma4:latest,gemma4:e4b,llava:latest")
    preferred = [m.strip() for m in configured.split(",") if m.strip()]
    chain = [m for m in preferred if m in available]
    chain.extend(m for m in available if _is_ollama_vision_model(m) and m not in chain)
    return chain


def _build_model_chain(base64_image: Optional[str] = None) -> List[str]:
    chain = [OLLAMA_MODEL]
    if OLLAMA_FALLBACK_MODELS:
        for m in OLLAMA_FALLBACK_MODELS.split(","):
            m = m.strip()
            if m and m not in chain:
                chain.append(m)
    available = _get_available_models()
    if base64_image:
        vision_chain = _ollama_vision_chain(available)
        if vision_chain:
            chain = vision_chain + [m for m in chain if m not in vision_chain]
    for m in available:
        if m not in chain:
            chain.append(m)
    return chain


def _ollama_chat(system: str, user: str, model: Optional[str] = None, force_json: bool = True, base64_image: Optional[str] = None) -> str:
    """Call Ollama chat API with automatic model fallback."""
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    models_to_try = [model] if model else _build_model_chain(base64_image=base64_image)

    for model_name in models_to_try:
        image_payload = base64_image
        if image_payload and not _is_ollama_vision_model(model_name):
            logger.info("[%s] is not a vision model; retrying as text-only if reached.", model_name)
            image_payload = None

        effective_system = system
        if "qwen3" in model_name.lower():
            effective_system = "/no_think\n" + system

        msg = {"role": "user", "content": user}
        if image_payload:
            msg["images"] = [image_payload]

        output_tokens = _output_token_budget(model_name, effective_system, user, image_payload)

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": effective_system},
                msg,
            ],
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                "num_predict": output_tokens,
                "num_ctx": _ollama_num_ctx(model_name, effective_system, user, image_payload, output_tokens),
            },
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

def _llm_chat(system: str, user: str, force_json: bool = True, base64_image: Optional[str] = None, force_model: Optional[str] = None) -> str:
    """
    Call the configured LLM provider.
    Uses runtime llm_config overrides (from Streamlit UI) if set.
    Fallback chain: configured provider → Ollama (local).
    """
    provider = llm_config.provider

    if provider == "openai":
        active_model = _resolve_openai_model(base64_image, force_model)
        logger.info("Using OpenAI (%s)", active_model)
        ans = _openai_chat(system, user, force_json=force_json, base64_image=base64_image, force_model=active_model)
        if ans:
            return ans
        logger.warning("OpenAI failed.")

    elif provider == "groq":
        model = llm_config.groq_model
        logger.info("Using Groq (%s)", model)
        ans = _groq_chat(system, user, force_json=force_json, base64_image=base64_image)
        if ans:
            return ans
        logger.warning("Groq failed.")

    # Local Ollama fallback. Gated behind a probe and an env flag because
    # a misconfigured Ollama can burn 9+ minutes per call on 180s × 3 retries.
    if provider == "ollama" or (ENABLE_OLLAMA_FALLBACK and _ollama_is_healthy()):
        logger.info("Using Ollama (%s)", llm_config.ollama_model)
        return _ollama_chat(system, user, force_json=force_json, base64_image=base64_image)

    if provider != "ollama":
        logger.warning("Ollama fallback skipped (unhealthy or LLM_OLLAMA_FALLBACK unset).")
    return ""


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
    "thickness": "door_thickness", "door_thickness": "door_thickness", "door thickness": "door_thickness", "thk": "door_thickness",
    "material": "door_material", "door_material": "door_material", "door material": "door_material", "dr matl": "door_material",
    "finish": "door_finish", "door_finish": "door_finish", "door finish": "door_finish", "dr fin": "door_finish", "dr finish": "door_finish",
    "frame_material": "frame_material", "frame material": "frame_material", "fr matl": "frame_material",
    "frame_finish": "frame_finish", "frame finish": "frame_finish", "fr fin": "frame_finish", "fr finish": "frame_finish",
    "elevation": "elevation", "elev": "elevation", "door elev": "elevation",
    "hardware set": "hardware_set", "hardware_set": "hardware_set",
    "hw set": "hardware_set", "hdwr set": "hardware_set",
    "fire rating": "fire_rating", "fire_rating": "fire_rating",
    "fire rate": "fire_rating",
    "comments": "remarks", "remarks": "remarks", "notes": "remarks",
    "door_slab_material": "door_slab_material", "slab material": "door_slab_material",
    "vision panel": "vision_panel", "vision_panel": "vision_panel",
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
    "set no": "hardware_set_id", "set no.": "hardware_set_id",
    "group": "hardware_set_id", "group no": "hardware_set_id", "group no.": "hardware_set_id",
    "hw": "hardware_set_id", "hdwr": "hardware_set_id", "hdwe": "hardware_set_id",
    "hardware_set_name": "hardware_set_name", "function": "hardware_set_name",
    "qty": "qty", "quantity": "qty",
    "qty_raw": "qty_raw", "quantity_raw": "qty_raw", "quantity raw": "qty_raw",
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


def extract_doors_llm(system: str, user: str, base64_image: Optional[str] = None, force_model: Optional[str] = None) -> List[dict]:
    """
    Call LLM for door extraction and return validated door rows.
    Applies deterministic pair detection.
    """
    content = _llm_chat(system, user, base64_image=base64_image, force_model=force_model)
    if not content:
        return []

    rows = _extract_json_array(content)
    out = []

    for r in rows:
        if not isinstance(r, dict):
            continue
        r = {k: _blank_if_unknown(v) for k, v in r.items()}
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
                r["extra_fields"] = _clean_extra_fields(extra)


            row = DoorScheduleRow(
                door_number=door_number,
                level_area=_blank_if_unknown(r.get("level_area")),
                room_name=_blank_if_unknown(r.get("room_name")),
                door_type=_blank_if_unknown(r.get("door_type")),
                frame_type=_blank_if_unknown(r.get("frame_type")),
                frame_width=_blank_if_unknown(r.get("frame_width")),
                frame_height=_blank_if_unknown(r.get("frame_height")),
                door_width=_blank_if_unknown(width),
                door_height=_blank_if_unknown(r.get("door_height")),
                hardware_set=clean_hw_id(_blank_if_unknown(r.get("hardware_set"))) or None,
                fire_rating=_blank_if_unknown(r.get("fire_rating")),
                head_jamb_sill_detail=_blank_if_unknown(r.get("head_jamb_sill_detail")),
                keyed_notes=_blank_if_unknown(r.get("keyed_notes")),
                remarks=_blank_if_unknown(r.get("remarks")),
                door_slab_material=_blank_if_unknown(r.get("door_slab_material")),
                vision_panel=_blank_if_unknown(r.get("vision_panel")),
                glazing_type=_blank_if_unknown(r.get("glazing_type")),
                finish=_blank_if_unknown(r.get("finish")),
                door_thickness=_blank_if_unknown(r.get("door_thickness")),
                door_material=_blank_if_unknown(r.get("door_material")),
                door_finish=_blank_if_unknown(r.get("door_finish")),
                frame_material=_blank_if_unknown(r.get("frame_material")),
                frame_finish=_blank_if_unknown(r.get("frame_finish")),
                elevation=_blank_if_unknown(r.get("elevation")),
                is_pair=is_pair,
                door_leaves=2 if is_pair else 1,
                extra_fields=_clean_extra_fields(r.get("extra_fields", {})),
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


def extract_hardware_llm(system: str, user: str, base64_image: Optional[str] = None, force_model: Optional[str] = None) -> List[dict]:
    """
    Call LLM for hardware extraction and return validated component rows.
    Quantities are preserved AS-IS from the document.
    """
    content = _llm_chat(system, user, base64_image=base64_image, force_model=force_model)
    if not content:
        return []

    rows = _extract_json_array(content)
    out = []

    for r in rows:
        if not isinstance(r, dict):
            continue

        r = {k: _blank_if_unknown(v) for k, v in r.items()}
        hw_id = clean_hw_id(r.get("hardware_set_id"))
        desc = str(r.get("description") or "").strip()
        if not hw_id and not desc:
            continue

        # Skip header rows
        if desc.upper() in ("DESCRIPTION", "COMPONENT", "ITEM"):
            continue

        qty_raw = _blank_if_unknown(r.get("qty_raw")) or _blank_if_unknown(r.get("qty"))
        candidate_for_filter = {
            **r,
            "hardware_set_id": hw_id,
            "description": desc,
            "qty_raw": qty_raw,
        }
        if not is_probable_hardware_component(candidate_for_filter):
            logger.debug("Filtered non-component hardware row: set=%r desc=%r", hw_id, desc)
            continue

        try:
            row = HardwareComponentRow(
                hardware_set_id=hw_id or "?",
                hardware_set_name=_blank_if_unknown(r.get("hardware_set_name")),
                qty=r.get("qty"),
                qty_raw=str(qty_raw).strip() if qty_raw is not None else None,
                unit=_blank_if_unknown(r.get("unit")),
                description=desc or "-",
                catalog_number=_blank_if_unknown(r.get("catalog_number")),
                finish_code=_blank_if_unknown(r.get("finish_code")),
                manufacturer_code=_blank_if_unknown(r.get("manufacturer_code")),
                notes=_blank_if_unknown(r.get("notes")),
                extra_fields=_clean_extra_fields(r.get("extra_fields", {})),
            )
            out.append(row.model_dump())
        except Exception as e:
            logger.debug("Validation warning for hardware: %s", e)
            out.append({
                "hardware_set_id": hw_id or "?",
                "qty": HardwareComponentRow.clean_qty(r.get("qty")),
                "qty_raw": str(qty_raw).strip() if qty_raw is not None else None,
                "unit": _blank_if_unknown(r.get("unit")),
                "description": desc or "-",
                **{k: v for k, v in r.items()
                   if k not in ("hardware_set_id", "qty", "qty_raw", "unit", "description")},
            })

    return out
