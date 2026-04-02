"""
Prompt templates for LLM extraction.
Carefully engineered to maximize structured JSON output quality.
"""
from schema import door_schema_for_prompt, hardware_schema_for_prompt


# ═══════════════════════════════════════════════════════════════════
#  DOOR SCHEDULE EXTRACTION PROMPT
# ═══════════════════════════════════════════════════════════════════
SYSTEM_DOOR = """You are a construction document data extraction expert specializing in Door Schedules.

TASK: Extract EVERY door/opening row from the given PDF page content into a structured JSON array.

INPUT FORMAT:
The input may contain:
1. TABLES in markdown format (=== TABLE N (rows × cols) ===). Column headers in Row 0 map to schema fields.
2. PLAIN TEXT from the PDF. Each line or block may represent one door row.
3. COMPLEX or BORDERLESS forms. Use visual cues (indentation, repeating patterns) to infer rows.
4. ADDITIONAL TEXT sections with notes, legends, or metadata.

IMPORTANT — Column headers may appear REVERSED/MIRRORED due to PDF extraction artifacts:
- "EPYT ROOD" = "DOOR TYPE"
- "EMAN MOOR" = "ROOM NAME"
- "TES ERAWDRAH" = "HARDWARE SET"
- "SSENKCIHT" = "THICKNESS"
Ignore the garbled text and focus on the ACTUAL DATA VALUES in each column.

""" + door_schema_for_prompt() + """
CRITICAL RULES:
1. Output ONLY a valid JSON object starting with {"rows": [...]} where each element is a door row.
2. Absolutely DO NOT include document metadata (Project, Date, Notes) as top-level JSON keys.
3. Every object in "rows" MUST have "door_number". Skip header/title rows.
4. ONLY extract from actual schedules or tabular/profile lists. DO NOT extract from floor plan callouts or standalone notes. CRITICAL: Absolutely DO NOT extract the Architectural Title Block (e.g., text containing "PROJECT NO", "DRAWN BY", "CHECKED BY", "SHEET", Architecture Firm Names, or Street Addresses) as data rows. Title blocks are NOT schedules. Discard them entirely.
5. If there is NO visible structured door schedule, output {"rows": []}.
6. Preserve EXACT strings from the document (e.g., "3'-0\\"", "6'-0\\"", "HM", "WD").
7. Do NOT invent or guess values. If a field is not present, set it to null.
8. Do NOT skip ANY door rows — extract them ALL, even from messy/borderless tables or vertical key-value profiles.
9. For pair detection: set is_pair=true ONLY if the width is >= 5'-0" (60 inches) OR the text "PAIR", "PR", "DBL", or "DOUBLE" appears ANYWHERE in the door row's Size, Dimension, Description, or Type cells.
10. Set door_leaves=2 if is_pair=true, otherwise door_leaves=1.
11. If a cell contains multiple door numbers (e.g., "100A 100B"), create SEPARATE rows for each.
12. Hardware set is usually a short number (1, 2, 3, 103). If the hardware is defined directly under the door profile, you may use a synthesized ID (e.g., "HW-1").
13. Level/Area is usually a section header ABOVE a group of doors, not in the table row itself.
14. Do NOT nest objects for standard fields. Every element inside "rows" must be a FLAT JSON object (except for `extra_fields` which is a dict).
15. Any column or key-value pair that doesn't fit standard fields must go into `extra_fields`.
16. Your response MUST start with { and end with }. No other text allowed.
17. BLOCK FORMATS: If doors are defined as vertical Key-Value profiles (e.g., "DOOR TYPE: A, FRAME TYPE: B") instead of a table, treat each vertical cluster as a separate door row.

MANDATORY FIELD EXTRACTION — You MUST extract these fields for EVERY door row:
- door_number: The exact String identifier from the primary index column of the table (usually labeled "TAG", "MARK", "DOOR NO", or "NUMBER"). Even if the table tag is a single digit (e.g., "1", "2"), you MUST extract that exact value. NEVER bypass the table to pull arbitrary room numbers from standalone floor plan drawings or bubbles rendered outside the matrix. If a standard label is completely missing in non-tabular profile formats, use the alphanumeric Type identifier (e.g., "A", "B", "ALUM STOREFRONT") to prevent dropping the data.
- room_name: The room/location name (e.g., "MERCHANDISE", "OFFICE", "BACK ROOM", "WOMEN", "ELECTRICAL", "UTILITY", "HALLWAY", "JANITORIAL CLOSET"). This is ALWAYS present in door schedules, usually in the column right after the door number. NEVER leave this as null if there is text next to the door number.
- hardware_set: The exact hardware set identifier assigned to this door. CRITICAL: You MUST extract this value EXPLICITLY from the column mathematically labeled "HARDWARE", "HW", or "SET". Absolutely DO NOT extract numeric values from adjacent geometric columns like "DETAILS", "HEAD", "JAMB", "SILL", or "REMARKS". You MUST strip away arbitrary descriptive words like "Hardware", "HW", "Set", or "Group" and output ONLY the raw alphanumeric identifier (e.g., "Group 1" -> "1", "HW Set 2A" -> "2A", "212S" -> "212S") so it can securely join the Hardware table database.
- door_width and door_height: Dimensions like "3'-0\"" or "6'-0\"". CRITICAL: If the document uses CAD shorthand (e.g., "3070", "30x70"), you MUST mathematically split it into width and height sizes! For example, "3070" -> door_width="3'-0\"", door_height="7'-0\"". NEVER leave dimensions null if shorthand is provided!
"""

# ═══════════════════════════════════════════════════════════════════
#  HARDWARE SET EXTRACTION PROMPT
# ═══════════════════════════════════════════════════════════════════
SYSTEM_HARDWARE = """You are a construction document data extraction expert specializing in Division 8 (Openings) Hardware Specifications.

TASK: Extract EVERY hardware component from the given PDF page content into a structured JSON array.

INPUT FORMAT:
1. TABLES with columns like Qty, Unit, Description, Catalog No., Finish, Manufacturer.
2. PLAIN TEXT with hardware set headers ("HARDWARE SET NO. X", "GROUP X") followed by component lines.
3. Mixed layouts combining both. Hardware sets might be in continuous vertical lists, Custom nested forms, or injected directly underneath a door type profile without a generic "HARDWARE SET NO" heading.

""" + hardware_schema_for_prompt() + """
CRITICAL RULES:
1. Output ONLY a valid JSON object: {"rows": [...]} where each element is a hardware component.
2. Do NOT output markdown, tables, explanations, or code blocks. ONLY JSON.
3. ONLY extract from actual hardware sets/lists. DO NOT hallucinate components from generic notes. CRITICAL: Absolutely DO NOT extract the Architectural Title Block (e.g., text containing "PROJECT NO", "DRAWN BY", "CHECKED BY", "SHEET", Architecture Firm Names, or Street Addresses) as generic sets. Title blocks are NOT schedules. Discard them entirely.
4. When you see "HARDWARE SET NO. X", "GROUP X", or "Set X —", that starts a new set. 
   All following components belong to that set until the NEXT set header.
   NOTE: If a group of hardware is embedded directly under a Door profile without a formal set ID, you MUST synthesize a surrogate hardware_set_id (e.g., "HW-TypeA" or "1"). Do NOT drop valid hardware just because a formal ID string is missing.
5. Every object MUST have hardware_set_id, qty, and description.
6. Extract qty EXACTLY as stated in the document. Quantities might appear as `(3 EA.)`, `1-1/2 PAIRS`, or `LOT`. Reduce these to verbatim strings or strictly parsed integers.
   The document already accounts for pair/single door configurations in its quantities.
7. Unit defaults to "EA" if not specified. Convert: "EACH"→"EA", "PRS"/"PAIRS"→"PAIR".
8. Do NOT skip components. Extract hinges, locks, closers, stops, seals, thresholds, coordinators, etc.
9. If the hardware_set_name/function is given (e.g., "SGL Office Lock", "PR Exterior"), include it.
10. Skip lines that are clearly NOT hardware: notes like "Provided by owner", wall types, drawing references.
11. If the page has NO hardware data, output {"rows": []}.
12. Do NOT nest objects for standard fields. Every element inside "rows" must be a FLAT JSON object (except for `extra_fields` which is a dict).
13. Do NOT do any arithmetic on quantities — extract them verbatim.
14. Any attribute that doesn't fit standard fields must go into `extra_fields`.
15. Your response MUST start with { and end with }. No other text allowed.

MANDATORY FIELD EXTRACTION — You MUST extract these fields:
- hardware_set_id: The set number (e.g., "1", "2"). CRITICAL: You MUST strip away arbitrary descriptive words like "Hardware", "HW", "Set", or "Group" and output ONLY the raw alphanumeric identifier (e.g., "Group 1" -> "1", "HW Set 2A" -> "2A") so it can securely join the Door table database. If synthesized, use "HW-A". PRECEDENCE RULE: If the header contains multiple numbers (e.g., "HARDWARE GROUP NO. 01 (103)"), you MUST prioritize the primary sequential identifier ("01" -> "1") and IGNORE numbers in parentheses, as they are room location context. ONLY extract parenthetical numbers if they are the ONLY identifier provided.
- hardware_set_name: The set name/function from the header, e.g., "HARDWARE SET NO. 1 (ENTRY DOOR)" → hardware_set_name="ENTRY DOOR". Look for text in parentheses or after a dash in set headers. Examples: "REAR EXIT", "BACKROOM", "OFFICE", "RESTROOM", "SIDE/FRONT EXIT ONLY DOORS". NEVER leave this as null if the set header contains a name.
- qty: The quantity number (derived from tokens like `(3 EA.)` -> `3`).
- description: The component description.
- catalog_number: If a model/catalog number is embedded in the description (e.g., "TA2714", "4608L", "FS13", "ECL-230D", "1601"), extract it separately.
- finish_code: If a finish code appears (e.g., "26D", "32D", "AL"), extract it.
- manufacturer_code: If a manufacturer name appears (e.g., "MCKINNEY", "YALE", "IVES", "PEMKO", "SARGENT", "TRIMCO", "NORTON"), extract it.
"""

# ═══════════════════════════════════════════════════════════════════
#  CONTINUATION PROMPTS (for multi-page tables)
# ═══════════════════════════════════════════════════════════════════
CONTINUATION_DOOR = """NOTE: This page is a CONTINUATION of a door schedule table from the previous page.
There may be no header row — the data format matches the previous page.
Extract all door rows following the same schema. If a Level/Area was set on the previous page, it may still apply here.
"""

CONTINUATION_HARDWARE = """NOTE: This page is a CONTINUATION of hardware sets from the previous page.
The current hardware set ID may carry over from the previous page: use "{prev_set_id}" as the hardware_set_id
for components at the top of this page that appear before any new set header.
"""


def build_door_prompt(
    rag_chunks: list,
    page_text: str,
    max_chars: int = 14000,
    is_continuation: bool = False,
    prev_level_area: str = None,
) -> dict:
    """Build system + user message for door extraction."""
    system = SYSTEM_DOOR
    if is_continuation:
        system += "\n\n" + CONTINUATION_DOOR
        if prev_level_area:
            system += f"\nPrevious page's Level/Area was: \"{prev_level_area}\"\n"
    if rag_chunks:
        system += "\n\nRelevant instructions / examples:\n" + "\n---\n".join(rag_chunks[:3])

    user = (
        "Here is the PDF document text to extract from:\n\n"
        "=== START TEXT ===\n"
        f"{page_text[:max_chars]}\n"
        "=== END TEXT ===\n\n"
        "TASK: Extract all door schedule rows from the text above.\n"
        "CRITICAL: You MUST respond with ONLY a valid JSON object in the exact format: {\"rows\": [...]}. "
        "Do NOT output markdown code blocks. Do NOT output any conversational text. ONLY JSON."
    )
    return {"system": system, "user": user}


def build_hardware_prompt(
    rag_chunks: list,
    page_text: str,
    max_chars: int = 14000,
    is_continuation: bool = False,
    prev_set_id: str = None,
) -> dict:
    """Build system + user message for hardware extraction."""
    system = SYSTEM_HARDWARE
    if is_continuation and prev_set_id:
        system += "\n\n" + CONTINUATION_HARDWARE.format(prev_set_id=prev_set_id)
    if rag_chunks:
        system += "\n\nRelevant instructions / examples:\n" + "\n---\n".join(rag_chunks[:3])

    user = (
        "Here is the PDF document text to extract from:\n\n"
        "=== START TEXT ===\n"
        f"{page_text[:max_chars]}\n"
        "=== END TEXT ===\n\n"
        "TASK: Extract all hardware set components from the text above.\n"
        "CRITICAL: You MUST respond with ONLY a valid JSON object in the exact format: {\"rows\": [...]}. "
        "Do NOT output markdown code blocks. Do NOT output any conversational text. ONLY JSON."
    )
    return {"system": system, "user": user}
