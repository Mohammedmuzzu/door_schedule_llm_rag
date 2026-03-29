# Setup steps (do once)

## Option A: OpenRouter (recommended if Ollama is blocked)

Uses cloud API; no local install. Get a free key at **https://openrouter.ai**.

```powershell
cd door_schedule_llm_rag
$env:OPENROUTER_API_KEY = "sk-or-v1-xxxxxxxx"
python run_llm_pipeline.py
```

Or set `OPENROUTER_API_KEY` in your environment / `.env`. Model: `openrouter/free` (auto-selects best free model).

## Option B: Ollama (local)

- Download: **https://ollama.com** → install for Windows.
- After install, run `ollama pull llama3.2`.

```powershell
cd door_schedule_llm_rag
python run_llm_pipeline.py
```

## Output

Results are written to **`extracted_data/`**:

- `extraction_results_llm.xlsx` — Door Schedule, Hardware Components, Milestone1 Aggregate, etc.
- `door_schedule_llm.csv`, `hardware_components_llm.csv`

## Structured extraction (default: on)

By default, the pipeline extracts **tables + text + layout hints** so the LLM knows WHERE and WHAT it's picking from:
- Tables → markdown format with column headers (e.g. `=== TABLE 1 (9 rows × 12 cols) ===`)
- Plain text → labeled as "ADDITIONAL TEXT" for hardware descriptions, notes
- Layout hints → header region when available

To use plain text only: `$env:USE_STRUCTURED_EXTRACTION = "0"`

### Table extraction backends

| Backend | Best for | Install |
|---------|----------|---------|
| **pdfplumber** | Mixed/borderless layouts (default) | Included |
| **camelot** | Bordered tables, better cell alignment | `pip install "camelot-py[cv]"` (needs OpenCV, Ghostscript) |
| **auto** | Try pdfplumber, use Camelot if better | Camelot optional |

Set backend: `$env:TABLE_EXTRACTION_BACKEND = "pdfplumber"` | `"camelot"` | `"auto"`

See `docs/TABLE_EXTRACTION_RESEARCH.md` for full comparison.

## Quick test

```powershell
python run_llm_pipeline.py --max 1
```
