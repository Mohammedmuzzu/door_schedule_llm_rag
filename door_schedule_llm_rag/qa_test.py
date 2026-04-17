"""Quick QA test for the projects from the feedback sheet."""
import sys
import logging
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING)

from pipeline import run_pipeline

PROJECTS = {
    "Project 32": Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -32_lessthan10doors\Project -32\A602 - Door Schedule.pdf"),
    "Project 33": Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -33_lessthan10doors\Project -33\A610 - Door Schedule.pdf"),
    "Project 34": Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -34_lessthan10doors\Project -34\ID-601 Door Schedule.pdf"),
    "Project 35": Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -35_lessthan10doors\Project -35\A6.10 - Door Schedule.pdf"),
    "Project 36": Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -36_lessthan10doors\Project -36\A8.0 - Door Schedule.pdf"),
}

results = []
for name, pdf_path in PROJECTS.items():
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({pdf_path.name})")
    print(f"{'='*60}")
    try:
        df_d, df_h = run_pipeline(
            pdf_files=[pdf_path],
            output_dir=f"qa_out/{name.replace(' ', '_')}",
            use_rag=True,
        )
        door_count = len(df_d)
        hw_count = len(df_h)
        
        # Calculate Extraction Recall & Precision Checks
        expected_doors = 0
        expected_hardware = 0
        
        # Super simple heuristic count of raw PDF strings (this would ideally use pdfplumber directly)
        import fitz
        try:
            doc = fitz.open(pdf_path)
            raw_text = chr(10).join([page.get_text() for page in doc])
            expected_doors = len(re.findall(r'\b\d{3,4}[A-Za-z]?\b', raw_text)) // 3 # rough heuristic
            expected_hardware = len(set(re.findall(r'(?i)(?:set[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|group[ \t]*[:\-\#.]?[ \t]*[\d\w.-]+|hardware set no\.)', raw_text)))
        except:
            pass

        # Check key columns (Schema Adherence)
        schema_adherence_score = 100
        missing_cols = []
        if door_count > 0:
            for col in ['door_thickness', 'door_material', 'door_finish', 'frame_material', 'frame_finish', 'elevation', 'door_width', 'door_height']:
                if col in df_d.columns:
                    non_null = df_d[col].notna().sum()
                    if non_null == 0:
                        missing_cols.append(col)
                        schema_adherence_score -= 10
                else:
                    missing_cols.append(f"{col} (NOT IN DF)")
                    schema_adherence_score -= 10
        
        # Check hardware set IDs 
        hw_set_ids = []
        if hw_count > 0 and 'hardware_set_id' in df_h.columns:
            hw_set_ids = sorted(df_h['hardware_set_id'].unique().tolist())
            
        execution_recall = f"{(len(hw_set_ids) / max(1, expected_hardware))*100:.1f}%" if expected_hardware > 0 else "N/A"
        
        result = {
            "name": name,
            "doors": door_count,
            "hardware_components": hw_count,
            "hardware_sets": len(hw_set_ids),
            "missing_cols": missing_cols,
            "schema_score": schema_adherence_score,
            "recall": execution_recall,
            "hw_set_ids": hw_set_ids,
        }
        results.append(result)
        print(f"  Doors: {door_count}, Hardware Sets: {len(hw_set_ids)} (Components: {hw_count})")
        print(f"  Schema Adherence: {schema_adherence_score}% | Recall: {execution_recall}")
        print(f"  Missing cols: {missing_cols or 'None'}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append({"name": name, "error": str(e)})

print("\n" + "="*60)
print("QA SUMMARY")
print("="*60)
for r in results:
    if "error" in r:
        print(f"  {r['name']}: ERROR - {r['error']}")
    else:
        status = "✅" if not r['missing_cols'] and r['doors'] > 0 else "⚠️"
        print(f"  {status} {r['name']}: {r['doors']} doors | {r['hardware_sets']} HW Sets | Schema: {r['schema_score']}% | Recall: {r['recall']} | Missing: {r['missing_cols'] or 'None'}")
