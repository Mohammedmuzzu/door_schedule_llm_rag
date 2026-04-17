import os
import sys
import logging
import fitz
from pathlib import Path
from pipeline import run_pipeline, discover_pdfs

def is_machine_generated(pdf_path: Path):
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for i in range(min(5, len(doc))):
            text += doc[i].get_text()
        doc.close()
        return len(text.strip()) > 300
    except:
        return False

def main():
    print("Finding Machine Generated PDFs...")
    pdf_dir = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs")
    all_pdfs = discover_pdfs(str(pdf_dir))
    
    machine_pdfs = []
    text_based = []
    for pdf_path, project_id in all_pdfs:
        is_mg = is_machine_generated(pdf_path)
        if is_mg:
            machine_pdfs.append((pdf_path, project_id))
            print(f"✅ Machine-gen: {project_id} - {pdf_path.name}")
        else:
            print(f"🖼️ Scanned/Image: {project_id} - {pdf_path.name}")
            
    print(f"\nFound {len(machine_pdfs)} Machine Generated PDFs out of {len(all_pdfs)}.")
    
if __name__ == "__main__":
    main()
