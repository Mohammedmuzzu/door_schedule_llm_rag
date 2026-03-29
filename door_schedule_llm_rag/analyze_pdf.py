"""
Random PDF Analysis Tool
Selects a random PDF, runs the multi-backend extractor, calls the LLM, and logs deep observations.
"""
import sys
import random
import logging
from pathlib import Path
import json

sys.path.insert(0, ".")
from page_extractor import extract_structured_page, get_page_count, _score_content
from llm_extract import _ollama_chat, _extract_json_array, _normalize_row
from prompts import SYSTEM_DOOR, SYSTEM_HARDWARE
import config

logging.basicConfig(level=logging.WARNING)

def analyze_random_pdf():
    if len(sys.argv) > 1:
        selected_pdf = Path(sys.argv[1])
        if not selected_pdf.exists():
            print(f"File not found: {selected_pdf}")
            return
    else:
        pdf_dir = Path(config.PDF_FOLDER)
        pdfs = list(pdf_dir.rglob("*.pdf"))
        if not pdfs:
            print("No PDFs found.")
            return
        selected_pdf = random.choice(pdfs)
    print(f"\n============================================================")
    print(f"ANALYZING: {selected_pdf.name}")
    print(f"============================================================")
    
    n_pages = get_page_count(selected_pdf)
    print(f"Total pages: {n_pages}")
    
    for page_idx in range(n_pages):
        print(f"\n--- PAGE {page_idx + 1} ---")
        content, ptype, cont = extract_structured_page(selected_pdf, page_idx)
        print(f"Classification: {ptype.upper()} | Continuation: {cont}")
        print(f"Extracted content length: {len(content)} characters")
        print(f"Content score: {_score_content(content):.1f}")
        
        # Sneak peek of the content to see backend choice
        if content.startswith("[Source"):
            first_line = content.split('\n')[0]
            print(f"Primary Source: {first_line}")
        print(f"Content excerpt:\n{content[:500].encode('utf-8', 'ignore').decode('utf-8')}...\n")
            
        if ptype in ("door_schedule", "mixed"):
            print("\n  >> Testing DOOR Prompt...")
            user = (
                "Extract all door schedule rows from this PDF page content. "
                "Respond with ONLY a JSON object: {\"rows\": [...]}\n\n"
                + content[:config.MAX_PAGE_CHARS]
            )
            raw = _ollama_chat(SYSTEM_DOOR, user)
            print(f"  RAW LLM DOORS OUTPUT:\n{raw[:1000]}...\n")
            rows = _extract_json_array(raw)
            print(f"  Extracted {len(rows)} doors.")
            if rows:
                print(f"  Sample row: {json.dumps(rows[0], indent=2)}")

        if ptype in ("hardware_set", "mixed"):
            print("\n  >> Testing HARDWARE Prompt...")
            user = (
                "Extract all hardware set components from this PDF page content. "
                "Respond with ONLY a JSON object: {\"rows\": [...]}\n\n"
                + content[:config.MAX_PAGE_CHARS]
            )
            raw = _ollama_chat(SYSTEM_HARDWARE, user)
            print(f"  RAW LLM HARDWARE OUTPUT:\n{raw[:1000]}...\n")
            rows = _extract_json_array(raw)
            print(f"  Extracted {len(rows)} components.")
            if rows:
                print(f"  Sample component: {json.dumps(rows[0], indent=2)}")

if __name__ == "__main__":
    analyze_random_pdf()
