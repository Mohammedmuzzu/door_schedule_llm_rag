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

DEPLOYMENT_ENV = get_env("DEPLOYMENT_ENV", "local")

# ── LLM Provider ──
LLM_PROVIDER = get_env("LLM_PROVIDER", "ollama").lower()

# ── Groq ──
GROQ_API_KEY = get_env("GROQ_API_KEY", "")
GROQ_MODEL = get_env("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── OpenAI ──
OPENAI_API_KEY = get_env("OPENAI_API_KEY", "")
OPENAI_MODEL = get_env("OPENAI_MODEL", "gpt-4o-mini")

# ── Ollama ──
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_FALLBACK_MODELS = os.environ.get("OLLAMA_FALLBACK_MODELS", "")

# ── RAG ──
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_COLLECTION_DOOR = "door_schedule_instructions"
CHROMA_COLLECTION_HARDWARE = "hardware_schedule_instructions"
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "3"))

# ── Extraction Settings ──
_env_max_chars = int(os.environ.get("MAX_PAGE_CHARS", "35000"))
MAX_PAGE_CHARS = max(35000, _env_max_chars)
# Temperature for LLM calls (low = deterministic)
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.05"))
# Confidence threshold below which we retry extraction
RETRY_THRESHOLD = float(os.environ.get("RETRY_THRESHOLD", "0.3"))

# ── Create output dirs ──
for d in (OUTPUT_DIR, RAG_DATA_DIR, INSTRUCTIONS_DIR):
    Path(d).mkdir(parents=True, exist_ok=True)

PYTHON_EXE = str(Path(BASE_DIR).parent.parent / "computervision" / "Scripts" / "python.exe")
