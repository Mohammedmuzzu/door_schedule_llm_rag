# Door Schedule LLM RAG

Python/Streamlit app for extracting door schedules, hardware schedules, risks, RFIs, and exports from architectural PDFs.

This app is isolated in the monorepo under:

```text
apps/door-schedule-llm-rag
```

## App Contents

- `app.py` - main Streamlit UI.
- `pipeline.py` - extraction pipeline orchestration.
- `llm_extract.py` - OpenAI, Groq, and Ollama LLM backends.
- `page_extractor.py` - PDF text/table extraction.
- `verification.py` - extraction validation and review flags.
- `instructions/` - RAG instruction source documents.
- `scripts/` - QA, full-corpus, dashboard, and utility runners.
- `tests/` - regression and hardening tests.

## Local Data

The default local PDF folder is:

```text
../../data/pdfs
```

Override it with:

```powershell
$env:PDF_FOLDER="C:\path\to\pdfs"
```

## Run Locally

All Python commands must use the shared project virtual environment.

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\apps\door-schedule-llm-rag
& "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
```

## Validate Syntax

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj
& "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe" -B -m py_compile apps\door-schedule-llm-rag\config.py apps\door-schedule-llm-rag\pipeline.py apps\door-schedule-llm-rag\llm_extract.py
```

## Docker

Build from this app directory:

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\apps\door-schedule-llm-rag
docker build -t door-schedule-llm-rag .
```

The Docker image runs `streamlit run app.py` on port `8501`.
