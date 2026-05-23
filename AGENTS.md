# Project: Door Schedule Monorepo

## Virtual Environment (MANDATORY)

**All Python commands MUST use the virtual environment at:**

```text
c:\Users\muzaf\my_lab\computervision\
```

- Python: `c:\Users\muzaf\my_lab\computervision\Scripts\python.exe`
- Pip: `c:\Users\muzaf\my_lab\computervision\Scripts\pip.exe`
- Streamlit: `c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe`

To activate:

```powershell
& "c:\Users\muzaf\my_lab\computervision\Scripts\Activate.ps1"
```

**NEVER use bare `python`, `pip`, or `streamlit` commands.** They resolve to the system-wide Windows Store Python, which does NOT have the project dependencies installed.

## Monorepo Structure

- `apps/door-schedule-llm-rag/` - Python Streamlit extraction app
  - `app.py` - Streamlit UI
  - `pipeline.py` - extraction pipeline orchestrator
  - `llm_extract.py` - LLM backends
  - `agent.py` - per-page extraction agent
  - `page_extractor.py` - PDF text/table extraction
  - `config.py` - configuration
  - `.env` - local API keys/settings, ignored by git
- `apps/fastbid24-door-analyzer/` - static FastBid24 browser app
  - `index.html` - browser entry point
  - `app.jsx` - React app source
  - `styles.css` - UI styling
  - `prompts/` - staged pipeline prompt documentation
  - `serve.ps1` - local static server launcher
- `data/pdfs/` - local input PDFs, ignored by git
- `docs/` - product and architecture notes

## LLM Providers

The Python extraction app supports 3 LLM providers, switchable at runtime via the Streamlit sidebar:

1. OpenAI
2. Groq
3. Ollama

## Running The Apps

### Door Schedule LLM RAG

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\apps\door-schedule-llm-rag
& "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
```

### FastBid24 Door Analyzer

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj
.\apps\fastbid24-door-analyzer\serve.ps1
```
