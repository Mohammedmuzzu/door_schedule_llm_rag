import sys
import logging
from pathlib import Path
from pipeline import discover_pdfs, run_pipeline

logging.basicConfig(level=logging.WARNING)
logging.getLogger("pipeline").setLevel(logging.ERROR)
logging.getLogger("page_extractor").setLevel(logging.ERROR)
logging.getLogger("llm_extract").setLevel(logging.ERROR)

def run_audit():
    pdf_folder = Path("c:/Users/muzaf/my_lab/sushmita_proj/pdfs")
    skills_dir = Path("c:/Users/muzaf/my_lab/sushmita_proj/skills")
    skills_dir.mkdir(exist_ok=True)
    report_path = skills_dir / "MASTER_BULK_AUDIT.md"

    pdfs = discover_pdfs(pdf_folder)
    print(f"Discovered {len(pdfs)} PDFs. Starting exhaustive bulk extraction audit...")

    out = []
    out.append("# 🚨 Master Bulk Extraction Audit Log\n")
    out.append("This document logs extraction anomalies across the entire corpus of machine-generated PDFs.\n")

    for idx, (pdf_path, pid) in enumerate(pdfs):
        print(f"[{idx+1}/{len(pdfs)}] Testing: {pdf_path.name}")
        try:
            # Silence internal prints using capture logic (just keeping it raw for brevity)
            df_doors, df_hw = run_pipeline(pdf_files=[pdf_path], use_rag=False)
            
            anomalies = []
            
            # 1. Zero Drop Anomaly
            if len(df_doors) > 0 and len(df_hw) == 0:
                anomalies.append("- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.")
            elif len(df_hw) > 0 and len(df_doors) == 0:
                anomalies.append("- ⚠️ **Zero Drop (Doors):** Hardware was extracted, but ZERO doors found.")
            elif len(df_hw) == 0 and len(df_doors) == 0:
                anomalies.append("- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).")
                
            # 2. Door Specific Anomalies
            if len(df_doors) > 0:
                # Missing Size
                if 'door_width' in df_doors.columns:
                    missing_widths = df_doors['door_width'].isna().sum() + (df_doors['door_width'].astype(str).str.lower() == 'nan').sum()
                    if missing_widths > 0:
                        anomalies.append(f"- 📏 **Missing Dimensions:** `{missing_widths}` doors isolated without explicit width attributes.")
                
                # Missing Identity
                if 'door_number' in df_doors.columns:
                    missing_ids = df_doors['door_number'].isna().sum() + (df_doors['door_number'].astype(str).str.lower() == 'nan').sum()
                    if missing_ids > 0:
                        anomalies.append(f"- 🆔 **Identity Crisis:** `{missing_ids}` doors lack a proper 'door_number'.")
                        
                # Hardware Orphans
                if len(df_hw) > 0 and 'hardware_set' in df_doors.columns and 'hardware_set_id' in df_hw.columns:
                    hw_glossary = df_hw['hardware_set_id'].astype(str).unique()
                    orphans = 0
                    for hw_str in df_doors['hardware_set'].dropna().astype(str):
                        if hw_str.lower() == 'nan': continue
                        match = False
                        for g in hw_glossary:
                            if g.lower() in hw_str.lower() or hw_str.lower() in g.lower():
                                match = True
                                break
                        if not match:
                            orphans += 1
                    if orphans > 0:
                        anomalies.append(f"- 👻 **Hardware Orphan Bleed:** `{orphans}` doors reference a Hardware Set that violates the Extracted Glossary.")
                        
            if anomalies:
                out.append(f"### 📄 _[{idx+1}/{len(pdfs)}]_ `{pdf_path.name}`")
                out.append(f"> **Yield:** {len(df_doors)} Doors, {len(df_hw)} HW Items")
                out.extend(anomalies)
                out.append("")
            else:
                out.append(f"### ✅ _[{idx+1}/{len(pdfs)}]_ `{pdf_path.name}`")
                out.append(f"> **Yield:** {len(df_doors)} Doors, {len(df_hw)} HW Items - **No Anomaly Detected**\n")
                
        except Exception as e:
            out.append(f"### 🛑 `{pdf_path.name}`\n- 💥 **CRITICAL CRASH:** `{str(e)}`\n")
            print(f"Crash on {pdf_path.name}: {e}")
            
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
        
    print(f"Bulk Audit Complete. See log at: {report_path}")

if __name__ == "__main__":
    run_audit()
