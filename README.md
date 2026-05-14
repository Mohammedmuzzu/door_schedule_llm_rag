---
title: Door Schedule LLM RAG
emoji: 🚪
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8501
---

# Door Schedule LLM RAG

Streamlit Docker Space for extracting door schedules and hardware schedules from PDFs using cloud LLMs, PDF parsers, and local RAG instructions.

## Required Space Secrets

Set these in **Settings > Variables and secrets** on Hugging Face:

- `OPENAI_API_KEY`
- `LLM_PROVIDER=openai`
- `DEPLOYMENT_ENV=production`

Optional:

- `OPENAI_MODEL=gpt-4o-mini`
- `MAX_PAGE_CHARS=16000`
- Supabase/S3 values from `door_schedule_llm_rag/.env.example` if you want exports persisted outside the Space.
