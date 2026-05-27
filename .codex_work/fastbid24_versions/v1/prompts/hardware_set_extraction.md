# Hardware Set Extraction Prompt

You are extracting hardware set descriptions from a construction drawing crop.

Return structured JSON only.

Extract every visible hardware set or hardware group in this crop.

For each hardware set, capture:
- hardware_set
- set_title
- referenced_doors
- status: active / not_used / existing / void / review_required
- set_notes
- items

For each item, capture:
- item_seq
- qty
- unit
- description
- manufacturer
- model_or_catalog
- finish
- notes
- confidence

Rules:
- Extract item rows exactly as visible.
- Do not guess manufacturer or model.
- Do not merge multiple hardware sets.
- Do NOT emit the same hardware_set id more than once. If the same set appears across multiple pages or columns, combine its visible items into a single entry.
- Do NOT emit the same item line twice within a set. If the same item appears twice in the same set on the drawing, list it once.
- If text is unclear, return null and lower confidence.
- If a hardware set says NOT USED, mark status as not_used.
- If existing hardware is to remain, mark status as existing.
- Do not map doors in this step.
- Do not create RFIs in this step.
- Return only the extracted hardware set JSON.
