"""
Configuration for Door Schedule + Division 8 Extraction Pipeline.
Override via environment variables or .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from this directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

PERSONAL_DIR = BASE_DIR.parent
PDF_FOLDER = os.environ.get("PDF_FOLDER") or str(PERSONAL_DIR / "pdfs")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR") or str(BASE_DIR / "extracted_data")
RAG_DATA_DIR = os.environ.get("RAG_DATA_DIR") or str(BASE_DIR / "rag_data")
INSTRUCTIONS_DIR = BASE_DIR / "instructions"

def get_env(key, default=""):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


def get_bool_env(key, default=False):
    value = get_env(key, "1" if default else "0")
    return str(value).strip().lower() in _TRUE_ENV_VALUES


def get_int_env(key, default=0):
    value = get_env(key, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_float_env(key, default=0.0):
    value = get_env(key, str(default))
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


DEPLOYMENT_ENV = get_env("DEPLOYMENT_ENV", "local")

# ── LLM Provider ──
LLM_PROVIDER = get_env("LLM_PROVIDER", "ollama").lower()

# ── Groq ──
GROQ_API_KEY = get_env("GROQ_API_KEY", "")
GROQ_MODEL = get_env("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── OpenAI ──
OPENAI_API_KEY = get_env("OPENAI_API_KEY", "")
OPENAI_MODEL = get_env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_RESCUE_MODEL = get_env("OPENAI_RESCUE_MODEL", "gpt-4o")
OPENAI_ALLOW_MODEL_ESCALATION = get_bool_env("OPENAI_ALLOW_MODEL_ESCALATION", False)
OPENAI_AUTO_ESCALATE_VISION = get_bool_env("OPENAI_AUTO_ESCALATE_VISION", False)
OPENAI_DIRECT_PDF_MODEL = get_env("OPENAI_DIRECT_PDF_MODEL", "")
OPENAI_DIRECT_PDF_MAX_MB = get_float_env("OPENAI_DIRECT_PDF_MAX_MB", 50.0)
OPENAI_DIRECT_PDF_MAX_OUTPUT_TOKENS = get_int_env("OPENAI_DIRECT_PDF_MAX_OUTPUT_TOKENS", 0)
OPENAI_DIRECT_PDF_TIMEOUT = get_int_env("OPENAI_DIRECT_PDF_TIMEOUT", 900)
OPENAI_QA_JUDGE_MODEL = get_env("OPENAI_QA_JUDGE_MODEL", OPENAI_RESCUE_MODEL)
OPENAI_RATELIMIT_RETRIES = get_int_env("OPENAI_RATELIMIT_RETRIES", 6)
OPENAI_RATELIMIT_MAX_WAIT = get_int_env("OPENAI_RATELIMIT_MAX_WAIT", 60)

# ── Ollama ──
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_FALLBACK_MODELS = os.environ.get("OLLAMA_FALLBACK_MODELS", "")
OLLAMA_NUM_CTX = get_int_env("OLLAMA_NUM_CTX", 0)
OLLAMA_VISION_MODELS = get_env("OLLAMA_VISION_MODELS", "qwen3-vl:8b,gemma4:latest,gemma4:e4b,llava:latest")

# ── RAG (ChromaDB — auto-rebuilds on boot from instructions/*.md) ──
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_COLLECTION_DOOR = "door_schedule_instructions"
CHROMA_COLLECTION_HARDWARE = "hardware_schedule_instructions"
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "3"))

# ── Supabase Storage (S3-compatible) ──
# Get these from: Supabase Dashboard → Settings → Storage → S3 Connection
AWS_ACCESS_KEY_ID = get_env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = get_env("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = get_env("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = get_env("S3_BUCKET_NAME", "")
S3_ENDPOINT_URL = get_env("S3_ENDPOINT_URL", "")  # e.g. https://<project-ref>.supabase.co/storage/v1/s3

# ── Extraction Settings ──
_env_max_chars = int(os.environ.get("MAX_PAGE_CHARS", "35000"))
# Floor avoids tiny prompts; cap honors MAX_PAGE_CHARS from env (e.g. Docker Space sets 16000).
MAX_PAGE_CHARS = max(4000, _env_max_chars)
# Temperature for LLM calls (low = deterministic)
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.05"))
# Confidence threshold below which we retry extraction
RETRY_THRESHOLD = float(os.environ.get("RETRY_THRESHOLD", "0.3"))
LLM_MAX_RETRIES = get_int_env("LLM_MAX_RETRIES", 2)
LLM_CONTEXT_TOKENS = get_int_env("LLM_CONTEXT_TOKENS", 0)
LLM_MAX_OUTPUT_TOKENS = get_int_env("LLM_MAX_OUTPUT_TOKENS", 0)
LLM_OLLAMA_FALLBACK = get_bool_env("LLM_OLLAMA_FALLBACK", False)

# ── Hybrid direct-PDF witness ──
HYBRID_DIRECT_PDF = get_env("HYBRID_DIRECT_PDF", "0")
HYBRID_DIRECT_PDF_MODE = get_env("HYBRID_DIRECT_PDF_MODE", "off")

# UI model choices
OPENAI_DEFAULT_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4.5-preview", "o1", "o1-mini"]
GROQ_MODEL_OPTIONS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"]
OLLAMA_DEFAULT_MODELS = ["qwen3-coder:30b", "qwen2.5:7b", "llama3.1:8b", "mistral:7b"]
PROVIDER_MODELS = {
    "openai": [],
    "groq": GROQ_MODEL_OPTIONS,
    "ollama": [],
}
MODEL_SPEED_HINTS = {
    "gpt-5.5": "Flagship model (most capable for complex tasks)",
    "gpt-5.5-instant": "Fast default 5.5 model",
    "gpt-5.4": "Optimized for tool use and large contexts",
    "gpt-rosalind": "Advanced scientific and deep reasoning model",
    "gpt-4o-mini": "Fast, cheap, strong accuracy",
    "gpt-4o": "Best accuracy, moderate cost",
    "gpt-4.5-preview": "Experimental next-gen model",
    "o1": "Advanced reasoning model (slower, very accurate)",
    "o1-mini": "Fast reasoning model",
    "gpt-5": "Next-generation frontier model",
    "gpt-5-turbo": "Fast next-generation frontier model",
    "llama-3.3-70b-versatile": "Fast cloud 70B, free tier available",
    "llama-3.1-8b-instant": "Ultra-fast 8B, free tier",
    "qwen3-coder:30b": "Local MoE 30B; smart but slow on 12GB VRAM",
    "qwen2.5:7b": "Good local model, fits in VRAM",
    "llama3.1:8b": "Solid local model, fits in VRAM",
    "mistral:7b": "Fast local model, fits in VRAM",
}

# ── Create output dirs ──
for d in (OUTPUT_DIR, RAG_DATA_DIR, INSTRUCTIONS_DIR):
    Path(d).mkdir(parents=True, exist_ok=True)

PYTHON_EXE = str(Path(BASE_DIR).parent.parent / "computervision" / "Scripts" / "python.exe")
