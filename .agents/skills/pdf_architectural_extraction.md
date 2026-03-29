---
name: PDF Architectural Extraction Master Logic
description: Robust logic pattern for extracting door and hardware schedules from diverse architectural floor plans and specification sheets.
---

# 🏗️ PDF Architectural Extraction Skills (Doors & Hardware)

When prompted to build, debug, or evaluate architectural LLM-based extractions (especially Division 8 Openings), you **must** consider the following non-standard variances to ensure a generalized and robust pipeline.

## 1. Architectural Formats Vary Wildly
Do not assume every submittal or schedule is a table. Documents usually fall into three formats:
1. **Tabular Matrix**: Standard rows and columns. (E.g., Door #, Width, Height)
2. **Key-Value Vertical Profiles**: Doors are defined in solitary text blocks. (E.g., `DOOR TYPE: XYZ`, `FRAME TYPE: ABC`).
3. **Blended Embeds**: Hardware specifications are injected directly underneath the related door type without a generic "HARDWARE SET NO. X" heading.

## 2. Generalization Rules for Prompts & Code
To extract successfully across all architectural styles without hardcoding limits per-PDF, your systemic instructions to the LLM must cover:

### 🚪 Door Rules
- **Non-Numeric Door Marks**: The concept of a `door_number` shouldn't force digits. In architectural detail sheets, doors are often labeled by alphabetical "Types" (e.g., `Type A`, `Type B`). Missing numbers should fallback to the Type name.
- **Block Extraction**: Explicitly instruct the LLM: *If the schedule defines doors as blocks or key-value summaries, treat each block as its own discrete "row".*
- **Room Names & Column Headers**: PDF parsers frequently garble headers (e.g., reversing text: `EMAN MOOR` instead of `ROOM NAME`). Extractors must be prompted to ignore header typos and infer based on column contextual values (e.g., "MERCHANDISE" -> Room Name).

### ⚙️ Hardware Rules
- **Implied Hardware Sets**: When hardware is blended underneath a Door Type block without a formalized set number, the LLM must **synthesize a surrogate hardware_set_id** (e.g., `HW-TypeA` or `1`) so the relational mapping in the application does not break.
- **Quantity Syntax**: Hardware quantities are rarely just integers. They appear as `(3 EA.)`, `1-1/2 PAIRS`, or `LOT`. LLMs must be instructed to reduce these to verbatim strings or strictly parsed integers.
- **Embedded Attributes**: Catalog numbers, finishes (e.g., `26D`, `32D`, `ALUM`), and manufacturers (e.g., `McKinney`, `Yale`) are almost always embedded as a single string inside a description column. 

## 3. Applying this Skill
Whenever constructing JSON schemas or multi-modal LLM prompts for extracting doors or hardware:
1. Make arrays/keys resilient to garbled headers.
2. Instruct the engine on resolving "Block Formats" vs "Tables".
3. Use Python dictionaries in your schema for `extra_fields` to swallow non-standard data gracefully.
