"""
Targeted test: Run classify_page on the 17 failing PDFs
to see what the LLM classifier actually returns.
"""
import sys, re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.append(str(Path(__file__).resolve().parent.parent))

import fitz
import pdfplumber
from page_extractor import classify_page, extract_structured_page, PageType

PDFS_DIR = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs")

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


def find_pdf(project_id, filename):
    for d in PDFS_DIR.iterdir():
        if d.is_dir():
            clean = re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s_-]+", "_", d.name.lower()))
            if project_id in clean or clean in project_id:
                for f in d.rglob("*.pdf"):
                    if f.name == filename:
                        return f
    for f in PDFS_DIR.rglob("*.pdf"):
        if f.name == filename:
            return f
    return None


def main():
    print("=" * 90)
    print("  CLASSIFICATION + EXTRACTION DEBUG TEST")
    print("=" * 90)

    for project_id, filename in ZERO_EXTRACT_PDFS:  # Test ALL 17
        pdf_path = find_pdf(project_id, filename)
        if not pdf_path:
            print(f"\n  {project_id}/{filename}: NOT FOUND")
            continue

        print(f"\n{'='*80}")
        print(f"  {project_id} / {filename}")
        print(f"{'='*80}")

        n_pages = 0
        try:
            doc = fitz.open(str(pdf_path))
            n_pages = len(doc)
            doc.close()
        except:
            pass

        for page_idx in range(n_pages):
            print(f"\n  --- Page {page_idx + 1} ---")
            text, page_type, is_cont, b64 = extract_structured_page(
                pdf_path, page_idx, max_chars=35000, prev_page_type=None
            )
            print(f"  Classification: {page_type}")
            print(f"  Text length:    {len(text)}")
            print(f"  Is continuation:{is_cont}")
            print(f"  Has image:      {bool(b64)}")

            if page_type == PageType.OTHER:
                # Show what the text looks like
                print(f"  Text sample:    {text[:300]}...")
                print(f"  ** CLASSIFIED AS OTHER - THIS IS THE BUG **")


if __name__ == "__main__":
    main()
