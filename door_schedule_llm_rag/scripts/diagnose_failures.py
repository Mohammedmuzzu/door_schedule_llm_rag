"""
Diagnose all 17 ZERO_EXTRACT PDFs to understand root causes.
For each PDF:
  1. Extract raw text via pymupdf
  2. Check gibberish density
  3. Check gatekeeper keywords
  4. Check pdfplumber tables
  5. Try img2table OCR fallback
  6. Report diagnosis
"""
import sys, re, os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.append(str(Path(__file__).resolve().parent.parent))

import fitz
import pdfplumber

ZERO_EXTRACT_PDFS = [
    ("project_13", "Door Schedule & Hardware.pdf"),
    ("project_14", "A6.0.pdf"),
    ("project_16", "Door Schedule.pdf"),
    ("project_17", "Door Schedule.pdf"),
    ("project_17", "Hardware Schedule.pdf"),
    ("project_19", "Door Schedule.pdf"),
    ("project_23", "Door Schedule.pdf"),
    ("project_53", "Door Schedule.pdf"),
    ("project_62", "A400_ DOOR WINDOW SCHEDULE Rev.1 markup.pdf"),
    ("project_64", "Door Schedule.pdf"),
    ("project_71", "Door Schedule 2.pdf"),
    ("project_78", "Door & Hardware Schedule.pdf"),
    ("project_80", "Door Schedule.pdf"),
    ("project_15", "209-A4.2-Schedules Notes and Details REV 1.pdf"),
    ("project_17", "A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf"),
    ("project_26", "A600 - Door Schedule.pdf"),
    ("project_40", "Door Schedule.pdf"),
]

PDFS_DIR = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs")

def find_pdf(project_id, filename):
    """Find PDF file by project and name."""
    # Check subdirectories
    for d in PDFS_DIR.iterdir():
        if d.is_dir():
            clean = re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s_-]+", "_", d.name.lower()))
            if project_id in clean or clean in project_id:
                for f in d.rglob("*.pdf"):
                    if f.name == filename:
                        return f
    # Check top-level
    for f in PDFS_DIR.glob("*.pdf"):
        if f.name == filename:
            return f
    # Fuzzy match
    for f in PDFS_DIR.rglob("*.pdf"):
        if filename.lower() in f.name.lower():
            return f
    return None

def is_gibberish(text):
    """Check if text has corrupted font encoding."""
    if not text or len(text) < 50:
        return True, 0.0, 0.0
    alpha_chars = sum(1 for c in text if c.isalnum())
    alpha_ratio = alpha_chars / len(text)
    vowels = sum(1 for c in text.lower() if c in 'aeiou')
    vowel_ratio = vowels / max(1, alpha_chars)
    return (alpha_ratio < 0.35 or vowel_ratio < 0.08), alpha_ratio, vowel_ratio

def check_gatekeeper_keywords(text):
    """Check for keywords that would pass the fast gatekeeper."""
    text_upper = text.upper()
    gate_keywords = ["DOOR", "SCHEDULE", "HARDWARE", "HW", "HDWE", "OPENING", "FRAME"]
    found = [kw for kw in gate_keywords if kw in text_upper]
    return found

def check_door_patterns(text):
    """Check for actual door number patterns."""
    patterns = [
        r'\b\d{3,4}[A-Za-z]?\b',  # 101, 101A
        r'\b[A-Z]\d{1,3}\b',       # A1, B12
        r'(?i)door\s*(?:no|number|#|mark)',
    ]
    hits = {}
    for pat in patterns:
        matches = re.findall(pat, text[:5000])
        if matches:
            hits[pat] = matches[:10]
    return hits

def diagnose_pdf(project_id, filename):
    """Full diagnostic on a single PDF."""
    pdf_path = find_pdf(project_id, filename)
    if not pdf_path:
        return {"status": "NOT_FOUND", "path": None}
    
    result = {
        "path": str(pdf_path),
        "pages": 0,
        "total_chars": 0,
        "gibberish": False,
        "alpha_ratio": 0,
        "vowel_ratio": 0,
        "gatekeeper_keywords": [],
        "door_patterns": {},
        "pdfplumber_tables": 0,
        "text_sample": "",
        "diagnosis": "",
    }
    
    # Extract text with pymupdf
    try:
        doc = fitz.open(str(pdf_path))
        result["pages"] = len(doc)
        all_text = []
        for page in doc:
            all_text.append(page.get_text())
        doc.close()
        full_text = "\n".join(all_text)
        result["total_chars"] = len(full_text)
        result["text_sample"] = full_text[:1500]
        
        gib, alpha, vowel = is_gibberish(full_text)
        result["gibberish"] = gib
        result["alpha_ratio"] = round(alpha, 3)
        result["vowel_ratio"] = round(vowel, 3)
        result["gatekeeper_keywords"] = check_gatekeeper_keywords(full_text)
        result["door_patterns"] = check_door_patterns(full_text)
    except Exception as e:
        result["diagnosis"] = f"PyMuPDF error: {e}"
        return result
    
    # Check pdfplumber tables
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    result["pdfplumber_tables"] += len(tables)
    except Exception as e:
        pass
    
    # Determine diagnosis
    if result["total_chars"] < 100:
        result["diagnosis"] = "SCANNED_IMAGE: Almost no extractable text. Needs full OCR."
    elif result["gibberish"]:
        result["diagnosis"] = "FONT_CORRUPTION: Text extracted but is gibberish (cid: codes). Gibberish filter should catch this."
    elif not result["gatekeeper_keywords"]:
        result["diagnosis"] = "GATEKEEPER_REJECT: No schedule keywords found. Pages classified as OTHER and skipped."
    elif result["pdfplumber_tables"] == 0 and len(result["door_patterns"]) == 0:
        result["diagnosis"] = "NO_TABULAR_DATA: Keywords present but no parseable table structure or door numbers."
    else:
        result["diagnosis"] = "UNKNOWN_FAILURE: Keywords and data seem present. LLM may have failed to parse the layout."
    
    return result


def main():
    print("=" * 100)
    print("  ZERO_EXTRACT FAILURE DIAGNOSIS REPORT")
    print("=" * 100)
    
    categories = {}
    
    for project_id, filename in ZERO_EXTRACT_PDFS:
        print(f"\n{'─' * 80}")
        print(f"  {project_id} / {filename}")
        print(f"{'─' * 80}")
        
        diag = diagnose_pdf(project_id, filename)
        
        if diag["status"] == "NOT_FOUND" if "status" in diag else False:
            print(f"  ❌ PDF NOT FOUND")
            continue
        
        print(f"  Pages:           {diag['pages']}")
        print(f"  Total chars:     {diag['total_chars']}")
        print(f"  Gibberish:       {diag['gibberish']} (alpha={diag['alpha_ratio']}, vowel={diag['vowel_ratio']})")
        print(f"  Gate keywords:   {diag['gatekeeper_keywords']}")
        print(f"  Door patterns:   {list(diag['door_patterns'].keys()) if diag['door_patterns'] else 'NONE'}")
        print(f"  Plumber tables:  {diag['pdfplumber_tables']}")
        print(f"  🔍 DIAGNOSIS:    {diag['diagnosis']}")
        
        # Print text sample for manual review
        sample = diag['text_sample'][:600].replace('\n', ' | ')
        print(f"  Text sample:     {sample[:300]}...")
        
        # Categorize
        cat = diag['diagnosis'].split(':')[0]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"{project_id}/{filename}")
    
    print("\n" + "=" * 100)
    print("  CATEGORY SUMMARY")
    print("=" * 100)
    for cat, pdfs in categories.items():
        print(f"\n  {cat} ({len(pdfs)} PDFs):")
        for p in pdfs:
            print(f"    - {p}")


if __name__ == "__main__":
    main()
