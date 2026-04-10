"""Quick QA test for the projects from the feedback sheet."""
import sys
import logging
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
        
        # Check key columns
        missing_cols = []
        if door_count > 0:
            for col in ['door_thickness', 'door_material', 'door_finish', 'frame_material', 'frame_finish', 'elevation', 'door_width', 'door_height']:
                if col in df_d.columns:
                    non_null = df_d[col].notna().sum()
                    if non_null == 0:
                        missing_cols.append(col)
                else:
                    missing_cols.append(f"{col} (NOT IN DF)")
        
        # Check hardware set IDs 
        hw_set_ids = []
        if hw_count > 0 and 'hardware_set_id' in df_h.columns:
            hw_set_ids = sorted(df_h['hardware_set_id'].unique().tolist())
        
        result = {
            "name": name,
            "doors": door_count,
            "hardware": hw_count,
            "missing_cols": missing_cols,
            "hw_set_ids": hw_set_ids,
        }
        results.append(result)
        print(f"  Doors: {door_count}, Hardware: {hw_count}")
        print(f"  Missing cols: {missing_cols or 'None'}")
        print(f"  HW Set IDs: {hw_set_ids or 'N/A'}")
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"name": name, "error": str(e)})

print("\n" + "="*60)
print("QA SUMMARY")
print("="*60)
for r in results:
    if "error" in r:
        print(f"  {r['name']}: ERROR - {r['error']}")
    else:
        status = "✅" if not r['missing_cols'] and r['doors'] > 0 else "⚠️"
        print(f"  {status} {r['name']}: {r['doors']} doors, {r['hardware']} hw | Missing: {r['missing_cols'] or 'None'} | HW IDs: {r['hw_set_ids'] or 'N/A'}")
