"""Debug the raw JSON output from the LLM to see what fields it actually returns."""
import json, logging, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

from page_extractor import extract_structured_page
from prompts import build_door_prompt
from rag_store import query_door_instructions
from llm_extract import _llm_chat, _extract_json_array
from pathlib import Path

pdf = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -33_lessthan10doors\Project -33\A610 - Door Schedule.pdf")
text, ptype, _ = extract_structured_page(pdf, 0)

chunks = query_door_instructions(text)
prompt = build_door_prompt(chunks, text, max_chars=8000)

content = _llm_chat(prompt["system"], prompt["user"])
rows = _extract_json_array(content)

print(f"Total rows returned: {len(rows)}")
print(f"\n--- Row 0 (all keys) ---")
if rows:
    print(json.dumps(rows[0], indent=2))
    print(f"\nKeys: {list(rows[0].keys())}")
    
    # Check if the new fields exist
    for field in ["door_thickness", "door_material", "door_finish", "frame_material", "frame_finish", "elevation"]:
        val = rows[0].get(field, "<<MISSING_KEY>>")
        print(f"  {field}: {val}")
