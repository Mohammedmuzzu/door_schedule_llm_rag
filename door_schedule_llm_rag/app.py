import streamlit as st
import os
import tempfile
import pandas as pd
from pathlib import Path
import logging
import sys

from config import (
    LLM_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL,
    GROQ_API_KEY, GROQ_MODEL, OLLAMA_MODEL,
    DEPLOYMENT_ENV,
)
from llm_extract import llm_config
from pipeline import run_pipeline

# Configure page
st.set_page_config(page_title="Door Schedule Extractor", layout="wide", page_icon="🚪")
st.title("🚪 Door & Hardware Schedule Extractor")


# --- Capture Logs to UI ---
class StreamlitLogHandler(logging.Handler):
    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.logs = []

    def emit(self, record):
        msg = self.format(record)
        self.logs.append(msg)
        # Keep last 15 lines so the UI log window doesn't get massively long
        display_text = "\n".join(self.logs[-15:])
        # Update the UI element
        self.placeholder.code(display_text, language="text")


# ═══════════════════════════════════════════════════════════════════
#  Available model options per provider
# ═══════════════════════════════════════════════════════════════════
PROVIDER_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"],
    "ollama": [],  # populated dynamically
}


def _get_ollama_models():
    """Fetch installed Ollama models for the dropdown."""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return ["qwen3-coder:30b", "qwen2.5:7b", "llama3.1:8b", "mistral:7b"]


# ═══════════════════════════════════════════════════════════════════
#  Sidebar — LLM Provider & Model Selection
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("🤖 LLM Configuration")

    # Provider selector
    if DEPLOYMENT_ENV == "production":
        provider_options = ["openai"]
        provider_labels = {"openai": "☁️ OpenAI (GPT)"}
    else:
        provider_options = ["openai", "groq", "ollama"]
        provider_labels = {
            "openai": "☁️ OpenAI (GPT-4o-mini, GPT-4o)",
            "groq": "⚡ Groq (Fast cloud inference)",
            "ollama": "🖥️ Ollama (Local, no API needed)",
        }

    # Default to whatever .env says
    default_provider_idx = provider_options.index(LLM_PROVIDER) if LLM_PROVIDER in provider_options else 0

    selected_provider = st.selectbox(
        "LLM Provider",
        options=provider_options,
        format_func=lambda x: provider_labels.get(x, x),
        index=default_provider_idx,
        key="llm_provider",
    )

    # Show API key status
    if selected_provider == "openai":
        if OPENAI_API_KEY:
            st.success("✅ OpenAI API Key configured")
        else:
            st.error("❌ No OpenAI API Key in .env")
    elif selected_provider == "groq":
        if GROQ_API_KEY:
            st.success("✅ Groq API Key configured")
        else:
            st.error("❌ No Groq API Key in .env")
    elif selected_provider == "ollama":
        st.info("🖥️ Using local Ollama server")

    # Model selector (dynamic based on provider)
    if selected_provider == "ollama":
        model_options = _get_ollama_models()
    else:
        model_options = PROVIDER_MODELS.get(selected_provider, [])

    # Find default model
    default_models = {
        "openai": OPENAI_MODEL,
        "groq": GROQ_MODEL,
        "ollama": OLLAMA_MODEL,
    }
    default_model = default_models.get(selected_provider, "")
    default_model_idx = model_options.index(default_model) if default_model in model_options else 0

    selected_model = st.selectbox(
        "Model",
        options=model_options,
        index=default_model_idx,
        key="llm_model",
    )

    # Apply selection to runtime config
    llm_config.set(selected_provider, selected_model)

    st.divider()

    # Speed/accuracy hints
    speed_hints = {
        "gpt-4o-mini": "⚡ Fast, cheap (~$0.01/PDF), great accuracy",
        "gpt-4o": "🎯 Best accuracy, moderate cost (~$0.05/PDF)",
        "gpt-4.1-mini": "⚡ Latest mini model, fast and cheap",
        "gpt-4.1-nano": "💨 Fastest, cheapest, good for simple PDFs",
        "llama-3.3-70b-versatile": "⚡ Fast cloud 70B, free tier available",
        "llama-3.1-8b-instant": "💨 Ultra-fast 8B, free tier",
        "qwen3-coder:30b": "🖥️ MoE 30B local — smart but slow on 12GB VRAM",
        "qwen2.5:7b": "🖥️ Good local model, fits in VRAM",
        "llama3.1:8b": "🖥️ Solid local model, fits in VRAM",
        "mistral:7b": "🖥️ Fast local model, fits in VRAM",
    }
    hint = speed_hints.get(selected_model, "")
    if hint:
        st.caption(hint)

    st.divider()

    st.subheader("📋 Extraction Options")
    use_rag = st.checkbox("Enable RAG Retrieval", value=True)

    st.divider()
    st.markdown("""
    **Output Details**:
    The pipeline processes PDFs to extract:
    1. Door Schedules
    2. Hardware Components

    Results are exported as Excel + CSV.
    """)

tab1, tab2 = st.tabs(["📄 Single File Upload", "📁 Bulk Directory Process"])

with tab1:
    st.subheader("Process a Single PDF")
    uploaded_file = st.file_uploader("Upload Door Schedule PDF", type="pdf")

    if uploaded_file and st.button("🚀 Run Extraction", key="run_single"):
        import time
        import shutil

        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / uploaded_file.name
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.info(f"Processing `{uploaded_file.name}` with **{provider_labels[selected_provider]}** → `{selected_model}`")

        log_placeholder = st.empty()
        handler = StreamlitLogHandler(log_placeholder)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"))

        pipeline_logger = logging.getLogger("pipeline")
        agent_logger = logging.getLogger("agent")
        extractor_logger = logging.getLogger("page_extractor")
        llm_logger = logging.getLogger("llm")

        pipeline_logger.addHandler(handler)
        agent_logger.addHandler(handler)
        extractor_logger.addHandler(handler)
        llm_logger.addHandler(handler)

        start_t = time.time()
        with st.spinner("Extracting... this may take a few minutes depending on the LLM provider."):
            df_doors, df_hw = run_pipeline(
                pdf_folder=temp_dir,
                output_dir=temp_dir,
                use_rag=use_rag,
                pdf_files=[temp_path],
            )

        pipeline_logger.removeHandler(handler)
        agent_logger.removeHandler(handler)
        extractor_logger.removeHandler(handler)
        llm_logger.removeHandler(handler)

        total_time = time.time() - start_t
        st.success(f"✅ Extraction Complete in {total_time:.1f} seconds using `{selected_model}`!")

        st.subheader("🚪 Doors")
        st.dataframe(df_doors.astype(str), use_container_width=True)
        st.subheader("⚙️ Hardware")
        st.dataframe(df_hw.astype(str), use_container_width=True)

        # Read Excel into memory BEFORE cleaning up temp dir
        excel_path = Path(temp_dir) / "extraction_results_llm.xlsx"
        excel_bytes = None
        if excel_path.exists():
            excel_bytes = excel_path.read_bytes()

        # Clean up temp dir (ignore errors from Windows file locks)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        if excel_bytes:
            st.download_button(
                label="⬇️ Download Excel Export",
                data=excel_bytes,
                file_name=f"{uploaded_file.name}_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

with tab2:
    st.subheader("Process Local Directory")
    st.write("Enter the absolute path to a local folder containing PDFs.")

    dir_path = st.text_input("Folder Path", value=str(Path.home() / "Documents"))

    if st.button("🚀 Run Bulk Extraction", key="run_bulk"):
        if not os.path.isdir(dir_path):
            st.error("Invalid directory path.")
        else:
            out_dir = str(Path(dir_path) / "extracted_data")
            st.info(f"Processing PDFs in `{dir_path}` with **{provider_labels[selected_provider]}** → `{selected_model}`")

            log_placeholder = st.empty()
            handler = StreamlitLogHandler(log_placeholder)
            handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"))

            pipeline_logger = logging.getLogger("pipeline")
            agent_logger = logging.getLogger("agent")
            extractor_logger = logging.getLogger("page_extractor")
            llm_logger = logging.getLogger("llm")

            pipeline_logger.addHandler(handler)
            agent_logger.addHandler(handler)
            extractor_logger.addHandler(handler)
            llm_logger.addHandler(handler)

            with st.spinner("Extracting... this will take some time."):
                df_doors, df_hw = run_pipeline(
                    pdf_folder=dir_path,
                    output_dir=out_dir,
                    use_rag=use_rag,
                )

            pipeline_logger.removeHandler(handler)
            agent_logger.removeHandler(handler)
            extractor_logger.removeHandler(handler)
            llm_logger.removeHandler(handler)

            st.success(f"✅ Bulk Extraction Complete! Results saved to `{out_dir}`")

            st.subheader("🚪 Doors")
            st.dataframe(df_doors.astype(str), use_container_width=True)
            st.subheader("⚙️ Hardware")
            st.dataframe(df_hw.astype(str), use_container_width=True)

            excel_path = Path(out_dir) / "extraction_results_llm.xlsx"
            if excel_path.exists():
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Full Excel Export",
                        data=f,
                        file_name="bulk_extraction_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
