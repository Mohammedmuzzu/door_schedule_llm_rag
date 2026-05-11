"""
Visual comparison script: Renders PDF pages to images and prints extracted data
so we can do an apple-to-apple comparison for QA.
"""
import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(".env")

from pipeline import run_pipeline
from llm_extract import llm_config

def render_pages(pdf_path, output_dir, dpi=150):
    """Render all pages to images."""
    doc = fitz.open(pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i in range(min(len(doc), 10)):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        img_path = os.path.join(output_dir, f"page_{i+1}.png")
        pix.save(img_path)
        paths.append(img_path)
        print(f"  Rendered page {i+1} -> {img_path}")
    return paths

def analyze_pdf(pdf_path, output_dir):
    """Extract and render a single PDF for comparison."""
    pdf_name = Path(pdf_path).stem
    print(f"\n{'='*60}")
    print(f"Analyzing: {pdf_name}")
    print(f"{'='*60}")
    
    # Render pages
    img_dir = os.path.join(output_dir, pdf_name)
    render_pages(pdf_path, img_dir)
    
    # Run extraction
    llm_config.set("openai", "gpt-4o-mini")
    df_doors, df_hw = run_pipeline(pdf_files=[Path(pdf_path)], use_rag=True)
    
    # Print results
    print(f"\n--- DOORS ({len(df_doors)} rows) ---")
    if not df_doors.empty:
        key_cols = [c for c in ["door_number", "room_name", "hardware_set", "door_width", "door_height", "door_material"] if c in df_doors.columns]
        print(df_doors[key_cols].to_string(index=False))
    
    print(f"\n--- HARDWARE ({len(df_hw)} rows) ---")
    if not df_hw.empty:
        key_cols = [c for c in ["hardware_set_id", "hardware_set_name", "qty", "description"] if c in df_hw.columns]
        print(df_hw[key_cols].to_string(index=False))
    
    # Save JSON for review
    doors_json = df_doors.to_json(orient="records", indent=2) if not df_doors.empty else "[]"
    hw_json = df_hw.to_json(orient="records", indent=2) if not df_hw.empty else "[]"
    
    json_path = os.path.join(img_dir, "extraction.json")
    with open(json_path, "w") as f:
        json.dump({"doors": json.loads(doors_json), "hardware": json.loads(hw_json)}, f, indent=2)
    print(f"\nSaved extraction to {json_path}")
    
    return df_doors, df_hw

if __name__ == "__main__":
    pdfs_dir = r"c:\Users\muzaf\my_lab\sushmita_proj\pdfs"
    output_dir = os.path.join(os.path.dirname(__file__), "..", "qa_visual_compare")
    
    # Analyze the PDFs that scored lowest
    problem_pdfs = [
        os.path.join(pdfs_dir, "project 1_less10doors.pdf"),
        os.path.join(pdfs_dir, "project 3_lessthan10door.pdf"),
    ]
    
    for pdf_path in problem_pdfs:
        if os.path.exists(pdf_path):
            analyze_pdf(pdf_path, output_dir)
        else:
            print(f"NOT FOUND: {pdf_path}")
