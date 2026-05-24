# FastBid24 Door Analyzer — Pipeline

Runtime extraction runs on the authenticated Render backend. This static file is public documentation only and intentionally contains no proprietary prompt text.

| Step | Type | Purpose |
|------|------|---------|
| Call 1 | LLM call | Door schedule extraction |
| Call 2 | LLM call | Hardware set extraction |
| Step 3 | Code | Mapping (door → hardware set) |
| Step 4 | Code | Rollup (quantities, totals) |
| Call 3 | LLM call (optional) | RFIs / estimator review |
| Step 5 | Code | Excel generation |

## Prompt files
- Prompt bodies are server-side only.
- Public files in this folder are placeholders so Cloud Pages does not expose prompt IP.
