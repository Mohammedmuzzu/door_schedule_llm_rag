"""Prompt templates for whole-PDF direct OpenAI witness extraction."""


DIRECT_PDF_PROMPT = """
You are extracting construction door schedule and Division 8 hardware data from
the attached PDF. The PDF is the source of truth: use both the extracted text
and page images available to you.

Return ONLY valid JSON with this exact top-level shape:
{
  "doors": [
    {
      "door_number": "...",
      "source_page": 1,
      "room_name": null,
      "door_type": null,
      "door_width": null,
      "door_height": null,
      "door_thickness": null,
      "door_material": null,
      "door_finish": null,
      "frame_type": null,
      "frame_material": null,
      "frame_finish": null,
      "hardware_set": null,
      "fire_rating": null,
      "remarks": null
    }
  ],
  "hardware": [
    {
      "hardware_set_id": "...",
      "source_page": 1,
      "hardware_set_name": null,
      "qty": null,
      "qty_raw": null,
      "unit": "EA",
      "description": "...",
      "catalog_number": null,
      "finish_code": null,
      "manufacturer_code": null,
      "notes": null
    }
  ]
}

Rules:
- Extract only real door schedule rows and real hardware component rows.
- Do not extract title blocks, drawing metadata, generic notes, floor-plan callouts, or proposal line items as door schedule rows.
- Preserve exact source strings for dimensions, material, finish, hardware set IDs, catalog numbers, and notes.
- If a field is absent or unreadable, set it to null. Do not guess.
- source_page is the 1-based PDF page number when you can identify it; otherwise null.
- For doors, include rows only when the PDF shows a door/opening mark plus physical schedule attributes such as dimensions, material, type, frame, rating, or hardware set.
- For hardware, include components only under visible set/group/list context or clear hardware paragraphs.
"""
