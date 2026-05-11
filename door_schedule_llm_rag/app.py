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
from app_admin import render_master_data_manager
from app_estimation import render_estimation_dashboard

# Configure page (MUST be the first Streamlit command)
st.set_page_config(page_title="Door Schedule Extractor", layout="wide", page_icon="🚪")

# ── Auto-seed RAG store on first launch ──
# `ensure_seeded()` is idempotent: it only re-seeds when collections are
# missing. On Streamlit Cloud containers (which wipe `rag_data/` between
# deploys) this re-runs on first page hit; on long-running servers it's a
# no-op after the first call.
@st.cache_resource
def _auto_seed_rag():
    """Seed RAG store once per server lifecycle and return a status dict."""
    try:
        from rag_store import ensure_seeded, status as rag_status
        ensure_seeded()
        return rag_status()
    except Exception as e:
        return {"available": 0, "error": str(e)}

_rag_status_dict = _auto_seed_rag()

st.title("🚪 Door & Hardware Schedule Extractor")

# Hide Streamlit UI Chrome (Menu, Footer, Header)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


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
    st.subheader("🩺 System Health")
    # Collect live status (re-computed each rerun — cheap)
    _rag_now = {"available": 0}
    try:
        from rag_store import status as _rag_status_live
        _rag_now = _rag_status_live()
    except Exception:
        pass
    try:
        from mineru_backend import is_available as _mineru_is_available
        _mineru_on = _mineru_is_available()
    except Exception:
        _mineru_on = False
    try:
        import verification  # noqa: F401
        _verify_on = True
    except Exception:
        _verify_on = False

    rag_emoji = "✅" if _rag_now.get("available") else "⚠️"
    st.markdown(f"{rag_emoji} **RAG** — {'online' if _rag_now.get('available') else 'disabled'}")
    if _rag_now.get("available"):
        st.caption(
            f"instructions: door={_rag_now.get('instructions_door', 0)}, "
            f"hw={_rag_now.get('instructions_hardware', 0)} | "
            f"examples: door={_rag_now.get('examples_door', 0)}, "
            f"hw={_rag_now.get('examples_hardware', 0)} | "
            f"anomalies={_rag_now.get('anomalies', 0)}"
        )

    st.markdown(f"{'✅' if _verify_on else '❌'} **Self-verification** — "
                f"{'active (evidence-routed rescue)' if _verify_on else 'offline'}")

    st.markdown(f"{'✅' if _mineru_on else '➖'} **MinerU fallback** — "
                f"{'installed' if _mineru_on else 'not installed (optional)'}")

    # Latest run pointer
    try:
        from run_store import list_recent_runs
        _recent = list_recent_runs(limit=1)
        if _recent:
            r = _recent[0]
            st.caption(
                f"last run: {r['pdf']} → {r['doors']}d/{r['hw']}hw "
                f"({r.get('elapsed_s', '?')}s, {r.get('started', '')})"
            )
    except Exception:
        pass

    st.divider()
    st.markdown("""
    **Output Details**:
    The pipeline processes PDFs to extract:
    1. Door Schedules
    2. Hardware Components

    Results are exported as Excel + CSV.
    """)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📄 Single File Upload",
    "📁 Bulk Directory Process",
    "📊 Recent Runs",
    "🧮 Project Estimation",
    "⚙️ Master Data Manager",
    "⚖️ QA Benchmark"
])

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
        st.dataframe(df_doors.astype(str), width="stretch")
        st.subheader("⚙️ Hardware")
        st.dataframe(df_hw.astype(str), width="stretch")

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
            st.dataframe(df_doors.astype(str), width="stretch")
            st.subheader("⚙️ Hardware")
            st.dataframe(df_hw.astype(str), width="stretch")

            excel_path = Path(out_dir) / "extraction_results_llm.xlsx"
            if excel_path.exists():
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Full Excel Export",
                        data=f,
                        file_name="bulk_extraction_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )


with tab3:
    st.subheader("📊 Recent Runs")
    st.caption(
        "Every PDF extraction writes a durable JSONL log to `rag_data/runs/`. "
        "Use this tab to audit what the system did on any historical run — "
        "per-page confidence, evidence, and whether the self-verification "
        "layer fired a rescue."
    )
    try:
        from run_store import list_recent_runs
        runs = list_recent_runs(limit=30)
    except Exception as e:
        st.error(f"Run store unavailable: {e}")
        runs = []

    if not runs:
        st.info("No runs yet. Process a PDF from the other tabs to see logs here.")
    else:
        df_runs = pd.DataFrame(runs)
        col_order = ["started", "pdf", "provider", "model", "doors", "hw",
                     "elapsed_s", "status", "path"]
        df_runs = df_runs[[c for c in col_order if c in df_runs.columns]]
        st.dataframe(df_runs.astype(str), width="stretch", hide_index=True)

        selected = st.selectbox(
            "Open run log (JSONL)",
            options=[r["path"] for r in runs],
            format_func=lambda p: Path(p).name,
        )
        if selected and Path(selected).exists():
            import json as _json

            events = []
            with open(selected, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(_json.loads(line))
                    except Exception:
                        continue
            st.markdown(f"**Events in** `{Path(selected).name}` ({len(events)})")
            st.json(events)
            st.download_button(
                "⬇️ Download run log",
                data=Path(selected).read_bytes(),
                file_name=Path(selected).name,
                mime="application/x-ndjson",
            )

with tab4:
    render_estimation_dashboard()

with tab5:
    render_master_data_manager()

with tab6:
    from app_qa_dashboard import render_qa_dashboard
    render_qa_dashboard()

