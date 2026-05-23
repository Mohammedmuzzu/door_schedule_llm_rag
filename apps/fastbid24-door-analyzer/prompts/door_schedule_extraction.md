# Door Schedule Extraction Prompt

You are extracting a door schedule from a construction drawing.

Return structured JSON only.

First, capture project-level header information from any cover sheet, title block, or schedule header visible in the drawing:
- project_name
- architect

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

Return JSON only in this shape:
{ "project_name": string|null, "architect": string|null, "doors": [ ... ] }
