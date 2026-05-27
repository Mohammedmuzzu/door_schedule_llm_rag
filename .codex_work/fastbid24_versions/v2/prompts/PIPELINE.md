# FastBid24 Door Analyzer — Pipeline

| Step | Type | Purpose |
|------|------|---------|
| Call 1 | LLM call | Door schedule extraction |
| Call 2 | LLM call | Hardware set extraction |
| Step 3 | Code | Mapping (door → hardware set) |
| Step 4 | Code | Rollup (quantities, totals) |
| Call 3 | LLM call (optional) | RFIs / estimator review |
| Step 5 | Code | Excel generation |

## Prompt files
- `prompts/door_schedule_extraction.md` — Call 1
- `prompts/hardware_set_extraction.md` — Call 2
- `prompts/door_hardware_mapping.md` — Code: mapping logic spec
- `prompts/rfi_coordination_review.md` — Call 3 (optional)
