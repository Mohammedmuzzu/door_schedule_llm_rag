# Door Schedule Extraction Prompt

You are extracting a door schedule from a construction drawing.

Return structured JSON only.

First, capture project-level header information from any cover sheet, title block, or schedule header visible in the drawing:
- project_name
- architect

Also capture, if visible anywhere on the door-schedule sheet(s):
- general_notes: array of free-text notes adjacent to or above the door schedule. Include sheet-level "General Notes", "Door Schedule Notes", "Door Notes", finish notes, "see drawings for X" callouts, alternates, allowances, and scope statements that affect Division 8. One string per logical note. Preserve text verbatim.
- schedule_legend: object mapping each abbreviation defined on the schedule (e.g. "CR", "EL", "DPS", "RX", "AO", "EH") to its expanded meaning verbatim from the legend panel. Empty object if no legend is visible.
- keying_notes: array of any keying-related instructions visible on the door-schedule sheet (master/sub-master structure, keyway, SFIC vs LFIC, construction core, restricted keyway, owner-supplied cylinders, etc.). Verbatim. Empty array if none.

Then extract every visible door schedule row.

For each door, capture:
- mark
- room_or_location
- width
- height
- thickness
- door_type
- door_material
- door_finish
- frame_type
- frame_material
- frame_finish
- glazing
- fire_rating
- hardware_set
- closer
- electric_or_access_control
- remarks
- source_page
- source_crop_id
- confidence

Rules:
- Preserve text exactly as shown.
- Do not infer missing values.
- Use null if unclear.
- Do not complete missing door numbers.
- Do not assume hardware items from the hardware set name.
- Existing-to-remain doors must be marked as existing_to_remain.
- If the row is partially unclear, still extract visible fields and mark confidence below 0.75.
- For project_name and architect: read verbatim from the title block / cover sheet. Use null if not visible. Do not abbreviate or paraphrase.
- For general_notes, schedule_legend, and keying_notes: read verbatim from the drawing. Use empty array / empty object if nothing is visible. Do not invent abbreviation meanings — only include legend entries that are explicitly defined on the sheet.

Return JSON only in this shape:
{ "project_name": string|null, "architect": string|null, "general_notes": [string], "schedule_legend": { [abbrev: string]: string }, "keying_notes": [string], "doors": [ ... ] }
