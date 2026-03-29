# Project: Door Schedule LLM RAG Extractor

## Virtual Environment (MANDATORY)

**All Python commands MUST use the virtual environment at:**

```
c:\Users\muzaf\my_lab\computervision\
```

- Python: `c:\Users\muzaf\my_lab\computervision\Scripts\python.exe`
- Pip: `c:\Users\muzaf\my_lab\computervision\Scripts\pip.exe`
- Streamlit: `c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe`

To activate: `& "c:\Users\muzaf\my_lab\computervision\Scripts\Activate.ps1"`

**NEVER use bare `python`, `pip`, or `streamlit` commands.** They resolve to the system-wide Windows Store Python, which does NOT have the project dependencies installed.

## Project Structure

- `door_schedule_llm_rag/` — Main application code
  - `app.py` — Streamlit UI (run with `streamlit run app.py`)
  - `pipeline.py` — Extraction pipeline orchestrator
  - `llm_extract.py` — LLM backends (OpenAI, Groq, Ollama)
  - `agent.py` — Per-page extraction agent
  - `page_extractor.py` — PDF text/table extraction
  - `config.py` — Configuration (reads from `.env`)
  - `.env` — API keys and settings
- `pdfs/` — Input PDF files (door schedules)

## LLM Providers

The project supports 3 LLM providers, switchable at runtime via the Streamlit sidebar:
1. **OpenAI** (GPT-4o-mini, GPT-4o) — fastest, most accurate
2. **Groq** — fast cloud inference, free tier
3. **Ollama** — local inference, no API key needed

## Running the App

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\door_schedule_llm_rag
& "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
```
