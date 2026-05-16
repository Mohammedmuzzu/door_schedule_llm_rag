"""Prompt fragments for retry, rescue, and verification extraction passes."""


BORDERLESS_DOOR_RETRY_HINT = (
    "\n\nCRITICAL CORRECTIVE ACTION: This is likely a BORDERLESS profile list "
    "(e.g. 'DRY STORAGE 105 3-0 8-10 Alum'). You MUST visually identify the isolated physical door "
    "numbers (like 105, 106, 208) even if there are no table borders, and extract every row. "
    "In inline text, the room name often comes before the door number; parse it properly."
)

HARDWARE_MISSING_SETS_HINT = (
    "\n\nCRITICAL CORRECTIVE ACTION: The previous extraction missed data. "
    "You extracted {extracted_sets} unique sets, but there are structural markers indicating up to "
    "{expected_sets} sets in this block. "
    "If there is a MULTI-COLUMN LAYOUT (side-by-side sets on the same line, e.g. GROUP#1  GROUP#2  GROUP#3), "
    "you MUST mentally split them horizontally! Extract ALL parallel sets distinctly. Do not drop data."
)

HARDWARE_INCOMPLETE_RETRY_HINT = (
    "\n\nNOTE: The previous extraction was incomplete. "
    "You MUST process the entire document. Look for all hardware set headers and component lines deep in the text."
)

FINAL_HARDWARE_ONLY_RESCUE_HINT = (
    "\n\nFINAL HARDWARE-ONLY RESCUE CHUNK: Ignore door schedule rows and title blocks. "
    "This chunk is from a dense hardware-set sheet. Extract ONLY hardware components "
    "grouped under each SET/GROUP header visible in this chunk. If sets are side-by-side "
    "in columns, split the columns mentally and preserve each set id."
)

EVIDENCE_DRIVEN_DOOR_RESCUE_HINT = (
    "\n\nEVIDENCE-DRIVEN DOOR RESCUE: The text contains door-number/dimension "
    "row patterns. Extract every actual door schedule row and ignore title "
    "blocks, hardware component lists, legends, and generic notes."
)

FINAL_DOOR_WINDOW_RESCUE_USER_TEMPLATE = (
    "=== START TEXT ===\n"
    "{page_text}\n"
    "=== END TEXT ===\n\n"
    "FINAL DOOR/WINDOW SCHEDULE RESCUE: Extract door/profile rows even if the primary "
    "mark is a short numeric profile ID (1, 2, 3) or a storefront/window/door type. "
    "Do NOT require room names. Treat each visible schedule/profile row as a door "
    "schedule row when it has dimensions, hardware, frame, or door/window type fields. "
    "Return the same JSON shape as the normal door extractor."
)

DOOR_SELF_VERIFICATION_HINT = (
    "\n\nSELF-VERIFICATION ALERT: Structural analysis of this page indicates "
    "~{expected} door rows (dimensions={dims}, row-like lines={rows}, "
    "door-number tokens={nums}), but the previous extraction produced {got}. "
    "You are being given ANOTHER chance with the page image attached. Use the "
    "image as ground truth: scan every row of the door schedule matrix, "
    "extract EVERY door mark (even if the native text layer is corrupt or "
    "missing). Output the full list - do not omit doors to keep the response "
    "short."
)

HARDWARE_SELF_VERIFICATION_HINT = (
    "\n\nSELF-VERIFICATION ALERT: Structural analysis of this page indicates "
    "~{expected_sets} hardware sets and ~{expected_components} components "
    "(HINGE/CLOSER/LOCK keyword hits), but the previous extraction produced "
    "{got_sets} sets / {got_components} components. Re-examine the page image "
    "carefully. Identify every SET/GROUP header (numeric or descriptive) and "
    "list EVERY component underneath it. Missing a set is worse than merging "
    "two - so err on the side of extracting more."
)


def hardware_missing_sets_hint(extracted_sets: int, expected_sets: int) -> str:
    return HARDWARE_MISSING_SETS_HINT.format(
        extracted_sets=extracted_sets,
        expected_sets=expected_sets,
    )


def final_door_window_rescue_user(page_text: str, max_chars: int) -> str:
    return FINAL_DOOR_WINDOW_RESCUE_USER_TEMPLATE.format(page_text=page_text[:max_chars])
