# Hardware Set Extraction Prompt

You are extracting hardware set descriptions from a construction drawing crop.

Return structured JSON only.

First, capture any sheet-level context visible alongside the hardware sets:
- hardware_preamble: array of free-text notes that appear above, beside, or below the hardware sets — e.g. "All hardware to comply with ANSI A156.x", manufacturer/finish standards, substitution rules, scope notes for electrified hardware, "EC to provide 120 V", etc. One string per logical note. Verbatim. Empty array if none.
- keying_notes: array of keying-related instructions visible on the hardware-set sheet(s) (master/sub-master structure, keyway brand, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, allowance counts, etc.). Verbatim. Empty array if none.
- hardware_legend: object mapping any abbreviations defined on the hardware sheet (e.g. "REX", "DPS", "EPT", "AO") to their expanded meanings. Empty object if no legend.

Then extract every visible hardware set or hardware group in this crop.

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
- For hardware_preamble, keying_notes, and hardware_legend: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent legend meanings.
- Return only the extracted hardware set JSON.

Return JSON in this shape:
{ "hardware_preamble": [string], "keying_notes": [string], "hardware_legend": { [abbrev: string]: string }, "hardware_sets": [ ... ] }
