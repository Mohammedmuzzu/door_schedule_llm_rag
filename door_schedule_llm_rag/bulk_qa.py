import os
import sys
import logging
import re
import pandas as pd
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING)

from pipeline import run_pipeline, discover_pdfs

def extract_expected_heuristics(pdf_path: Path):
    expected_doors = 0
    expected_hardware = 0
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        raw_text = chr(10).join([page.get_text() for page in doc])
        doc.close()
        
        expected_doors = len(re.findall(r'\b\d{3,4}[A-Za-z]?\b', raw_text)) // 3 # heuristic
        expected_hardware = len(set(re.findall(r'(?i)(?:set[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|group[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|hardware set no\.)', raw_text)))
    except:
        pass
    return expected_doors, expected_hardware

def is_machine_generated(pdf_path: Path):
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        text = ""
        for i in range(min(5, len(doc))):
            text += doc[i].get_text()
        doc.close()
        return len(text.strip()) > 300
    except:
        return False

def main():
    print("="*80)
    print("🚀 TARGETED QA EXTRACTION: MACHINE GENERATED PDFs")
    print("="*80)
    
    pdf_dir = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs")
    all_pdfs = discover_pdfs(str(pdf_dir))
    
    machine_pdfs = [(p, p_id) for p, p_id in all_pdfs if is_machine_generated(p)]
    print(f"Found {len(machine_pdfs)} Machine Generated PDFs to QA test.")
    
    results = []
    
    for pdf_path, project_id in machine_pdfs[:5]:
        name = f"{project_id} - {pdf_path.name}"
        print(f"\nProcessing: {name}")
        
        try:
            df_d, df_h = run_pipeline(
                pdf_files=[pdf_path],
                output_dir=f"qa_out/bulk/{project_id}",
                use_rag=True,
            )
            
            door_count = len(df_d)
            hw_count = len(df_h)
            
            exp_d, exp_h = extract_expected_heuristics(pdf_path)
            
            schema_score = 100
            missing_cols = []
            if door_count > 0:
                for col in ['door_thickness', 'door_material', 'door_finish', 'frame_material', 'frame_finish', 'elevation', 'door_width', 'door_height']:
                    if col in df_d.columns:
                        if df_d[col].notna().sum() == 0:
                            missing_cols.append(col)
                            schema_score -= 10
                    else:
                        missing_cols.append(f"{col} (NOT IN DF)")
                        schema_score -= 10
            
            hw_set_ids = []
            if hw_count > 0 and 'hardware_set_id' in df_h.columns:
                hw_set_ids = sorted(df_h['hardware_set_id'].unique().tolist())
                
            execution_recall = f"{(len(hw_set_ids) / max(1, exp_h))*100:.1f}%" if exp_h > 0 else "N/A"
            
            results.append({
                "project": project_id,
                "file": pdf_path.name,
                "extracted_doors": door_count,
                "extracted_hw_components": hw_count,
                "extracted_hw_sets": len(hw_set_ids),
                "expected_hw_sets_heuristic": exp_h,
                "schema_score": schema_score,
                "recall": execution_recall,
                "missing_cols": ", ".join(missing_cols),
                "status": "✅" if not missing_cols and door_count > 0 else "⚠️"
            })
            print(f"  ✅ Done. Extracted: {door_count} Doors, {len(hw_set_ids)} HW Sets (Recall: {execution_recall})")
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({
                "project": project_id,
                "file": pdf_path.name,
                "status": "❌ ERROR",
                "missing_cols": str(e)
            })

    # Save and Print Report
    df_report = pd.DataFrame(results)
    df_report.to_csv("bulk_qa_report.csv", index=False)
    
    print("\n" + "="*80)
    print("FINAL QA REPORT SUMMARY")
    print("="*80)
    for _, r in df_report.iterrows():
        print(f"{r['status']} {r['project']} [{r['file']}]: {r.get('extracted_doors', 0)} Doors, Recall: {r.get('recall', 'Error')} | Schema: {r.get('schema_score', 0)}%")
        
if __name__ == "__main__":
    main()
