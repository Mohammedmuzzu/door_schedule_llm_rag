# Setup

## Run The Streamlit App

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\apps\door-schedule-llm-rag
& "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
```

## Optional: Seed RAG Instructions

```powershell
cd c:\Users\muzaf\my_lab\sushmita_proj\apps\door-schedule-llm-rag
& "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe" -B scripts\seed_rag.py
```

## PDF Inputs

The default local PDF corpus is:

```text
c:\Users\muzaf\my_lab\sushmita_proj\data\pdfs
```

Override with:

```powershell
$env:PDF_FOLDER="C:\path\to\pdfs"
```

## LLM Providers

Configure provider settings in `.env` or in Streamlit secrets for deployment.

- `LLM_PROVIDER=openai`
- `LLM_PROVIDER=groq`
- `LLM_PROVIDER=ollama`
