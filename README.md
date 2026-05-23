# Door Schedule Monorepo

Production-oriented monorepo for the door schedule extraction tools.

## Apps

| App | Path | Purpose |
| --- | --- | --- |
| Door Schedule LLM RAG | `apps/door-schedule-llm-rag` | Streamlit/Python extraction pipeline, QA, RAG instructions, exports. |
| FastBid24 Door Analyzer | `apps/fastbid24-door-analyzer` | Static React browser app for the FastBid24 analyzer experience. |

## Shared Local Data

| Path | Purpose |
| --- | --- |
| `data/pdfs` | Local input PDFs for extraction and QA runs. Ignored by git. |
| `docs` | Product and architecture notes. |

## Run Locally

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

Then open:

```text
http://127.0.0.1:8503/
```

## Deployment Direction

- Deploy `apps/fastbid24-door-analyzer` as a static app, for example Cloudflare Pages.
- Deploy `apps/door-schedule-llm-rag` as the Python/Streamlit extraction app, for example a Docker-based service.
- Keep secrets in each deployment platform, never committed in the repo.
