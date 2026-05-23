"""Prompt templates for visual page-text fallback extraction."""


VISION_TEXT_EXTRACTION_SYSTEM_PROMPT = (
    "This is an architectural PDF page. Extract ALL text content you can see, "
    "especially any door schedule tables, hardware schedules, or specification data. "
    "Output the content as structured text, preserving table rows and columns. "
    "If you see a door schedule table, list each door with its number, dimensions, "
    "frame type, hardware set, and any other visible fields. "
    "If you see hardware sets, list each set with its components, quantities, and manufacturers."
)

VISION_TEXT_EXTRACTION_USER_PROMPT = "[Attached page image for visual extraction]"
