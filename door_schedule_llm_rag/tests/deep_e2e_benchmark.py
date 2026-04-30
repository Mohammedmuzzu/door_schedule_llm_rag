"""
Deep End-to-End Test: Runs extraction on ALL PDFs, then generates a
per-project comparison report that can be used for apple-to-apple
comparison against the source PDFs.

Output:
  qa_out/deep_e2e/
    ├── <project_id>/extraction_results_llm.xlsx   (per-project)
    ├── deep_e2e_report.csv                        (full summary)
    └── deep_e2e_report.xlsx                       (formatted report)
"""
import hashlib
import os, sys, io, re, time, logging, traceback
import pandas as pd
from pathlib import Path
from datetime import datetime

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True,
)
log = logging.getLogger("deep_e2e")

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pipeline import run_pipeline, discover_pdfs


def make_pdf_run_id(idx: int, pdf_path: Path, project_id: str) -> str:
    """Stable, unique output folder for one PDF benchmark run."""
    rel = str(pdf_path).lower().replace("\\", "/")
    digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:8]
    clean_file = re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s_.\-]+", "_", pdf_path.stem.lower()))
    clean_file = clean_file[:60] or "pdf"
    return f"{idx:03d}_{project_id}_{clean_file}_{digest}"

# ═══════════════════════════════════════════════════════════════
#  HEURISTIC ANALYSIS: Extract ground-truth signals from PDF
# ═══════════════════════════════════════════════════════════════

def analyse_pdf_ground_truth(pdf_path: Path) -> dict:
    """
    Opens the PDF with fitz and extracts heuristic ground-truth signals:
    - total text chars
    - is_scanned (True if <300 chars across first 5 pages)
    - candidate door numbers found via regex
    - candidate hardware set IDs
    - page count
    - has_tables (pdfplumber)
    """
    info = {
        "pages": 0,
        "total_chars": 0,
        "is_scanned": True,
        "candidate_door_nums": [],
        "candidate_hw_set_ids": [],
        "has_pdfplumber_tables": False,
        "text_sample": "",
    }
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        info["pages"] = len(doc)
        all_text = []
        for i, page in enumerate(doc):
            t = page.get_text()
            all_text.append(t)
        doc.close()

        full_text = "\n".join(all_text)
        info["total_chars"] = len(full_text)
        info["is_scanned"] = len(full_text.strip()) < 300
        info["text_sample"] = full_text[:500]

        # Candidate door numbers: 3-4 digit numbers optionally followed by a letter
        # Filter out years (19xx, 20xx) and common non-door numbers
        raw_nums = re.findall(r'\b(\d{3,4}[A-Za-z]?)\b', full_text)
        door_candidates = []
        for n in raw_nums:
            num_part = re.match(r'(\d+)', n).group(1)
            num = int(num_part)
            # Filter out years and very large numbers
            if 100 <= num <= 9999 and not (1900 <= num <= 2099):
                door_candidates.append(n)
        # Unique, sorted
        info["candidate_door_nums"] = sorted(set(door_candidates))

        # Hardware set IDs - various patterns
        hw_patterns = [
            r'(?:set|SET|Set)\s*[#:.\-]?\s*(\d+[A-Za-z]?)',
            r'(?:HW|hw|Hw)\s*[#:.\-]?\s*(\d+[A-Za-z]?)',
            r'(?:Hardware Set|HARDWARE SET)\s*(?:No\.?\s*)?(\d+[A-Za-z]?)',
        ]
        hw_ids = set()
        for pat in hw_patterns:
            for m in re.finditer(pat, full_text):
                hw_ids.add(m.group(1).upper())
        info["candidate_hw_set_ids"] = sorted(hw_ids)

    except Exception as e:
        log.warning("Failed to analyze %s: %s", pdf_path.name, e)

    # Try pdfplumber for tables
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:3]:  # Check first 3 pages
                tables = page.extract_tables()
                if tables and any(len(t) > 2 for t in tables):
                    info["has_pdfplumber_tables"] = True
                    break
    except:
        pass

    return info


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    OUT_DIR = Path("qa_out/deep_e2e")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_dir = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs")
    all_pdfs = discover_pdfs(str(pdf_dir))
    total = len(all_pdfs)

    print("=" * 80)
    print(f"  DEEP END-TO-END TEST: {total} PDFs")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = []
    
    for idx, (pdf_path, project_id) in enumerate(all_pdfs, 1):
        name = f"{project_id} / {pdf_path.name}"
        run_id = make_pdf_run_id(idx, pdf_path, project_id)
        print(f"\n[{idx}/{total}] {name}")

        # Step 1: Ground truth analysis
        gt = analyse_pdf_ground_truth(pdf_path)

        # Step 2: Run extraction
        t0 = time.time()
        try:
            proj_out = str(OUT_DIR / run_id)
            df_d, df_h = run_pipeline(
                pdf_files=[pdf_path],
                output_dir=proj_out,
                use_rag=True,
            )
            elapsed = time.time() - t0

            door_count = len(df_d) if not df_d.empty else 0
            hw_comp_count = len(df_h) if not df_h.empty else 0

            # Extracted HW set IDs
            extracted_hw_sets = []
            if hw_comp_count > 0 and "hardware_set_id" in df_h.columns:
                extracted_hw_sets = sorted(
                    df_h["hardware_set_id"].dropna().unique().tolist()
                )

            # Extracted door numbers
            extracted_door_nums = []
            if door_count > 0 and "door_number" in df_d.columns:
                extracted_door_nums = sorted(
                    df_d["door_number"].dropna().astype(str).unique().tolist()
                )

            # Schema completeness for doors
            schema_cols = [
                "door_number", "door_width", "door_height", "door_thickness",
                "door_material", "door_finish", "frame_material", "frame_finish",
                "elevation", "hardware_set", "fire_rating", "door_type",
            ]
            schema_filled = {}
            schema_score = 0
            if door_count > 0:
                for col in schema_cols:
                    if col in df_d.columns:
                        fill_pct = df_d[col].notna().mean() * 100
                        schema_filled[col] = round(fill_pct, 1)
                    else:
                        schema_filled[col] = 0.0
                schema_score = round(sum(schema_filled.values()) / len(schema_cols), 1)

            # HW component schema
            hw_schema_cols = [
                "hardware_set_id", "description", "qty",
                "manufacturer_code", "catalog_number", "finish_code",
            ]
            hw_schema_filled = {}
            hw_schema_score = 0
            if hw_comp_count > 0:
                for col in hw_schema_cols:
                    if col in df_h.columns:
                        fill_pct = df_h[col].notna().mean() * 100
                        hw_schema_filled[col] = round(fill_pct, 1)
                    else:
                        hw_schema_filled[col] = 0.0
                hw_schema_score = round(
                    sum(hw_schema_filled.values()) / len(hw_schema_cols), 1
                )

            # Determine status
            status = "OK"
            issues = []
            if gt["is_scanned"] and door_count == 0 and hw_comp_count == 0:
                status = "SCANNED_SKIP"
                issues.append("Scanned/image PDF — OCR fallback")
            elif door_count == 0 and hw_comp_count == 0:
                status = "ZERO_EXTRACT"
                issues.append("No data extracted from machine-readable PDF")
            elif door_count == 0 and hw_comp_count > 0:
                status = "HW_ONLY"
            elif door_count > 0 and hw_comp_count == 0:
                # Check if the PDF probably has HW too
                if len(gt["candidate_hw_set_ids"]) > 2:
                    status = "MISSING_HW"
                    issues.append(f"PDF has ~{len(gt['candidate_hw_set_ids'])} HW sets in text but none extracted")
                else:
                    status = "DOORS_ONLY"
            else:
                status = "OK"
                
            if schema_score > 0 and schema_score < 70:
                issues.append(f"Low door schema fill: {schema_score}%")

            result = {
                "project_id": project_id,
                "run_id": run_id,
                "output_dir": proj_out,
                "file": pdf_path.name,
                "pdf_path": str(pdf_path),
                "pages": gt["pages"],
                "is_scanned": gt["is_scanned"],
                "total_chars": gt["total_chars"],
                "has_tables": gt["has_pdfplumber_tables"],
                "gt_candidate_doors": len(gt["candidate_door_nums"]),
                "gt_candidate_hw_sets": len(gt["candidate_hw_set_ids"]),
                "extracted_doors": door_count,
                "extracted_hw_components": hw_comp_count,
                "extracted_hw_sets": len(extracted_hw_sets),
                "door_schema_score": schema_score,
                "hw_schema_score": hw_schema_score,
                "elapsed_sec": round(elapsed, 1),
                "status": status,
                "issues": "; ".join(issues) if issues else "",
                "extracted_door_nums": ", ".join(extracted_door_nums[:30]),
                "extracted_hw_set_ids": ", ".join(str(x) for x in extracted_hw_sets[:20]),
                "gt_hw_set_ids": ", ".join(gt["candidate_hw_set_ids"][:20]),
            }

            # Per-column fill rates for doors
            for col, pct in schema_filled.items():
                result[f"door_{col}_fill%"] = pct
            for col, pct in hw_schema_filled.items():
                result[f"hw_{col}_fill%"] = pct

            results.append(result)
            
            print(f"  -> {door_count} doors, {len(extracted_hw_sets)} HW sets, "
                  f"{hw_comp_count} HW items | Schema: D={schema_score}% H={hw_schema_score}% "
                  f"| {elapsed:.0f}s | {status}")

        except Exception as e:
            elapsed = time.time() - t0
            tb = traceback.format_exc()
            log.error("FAILED: %s — %s", name, e)
            results.append({
                "project_id": project_id,
                "run_id": run_id,
                "output_dir": str(OUT_DIR / run_id),
                "file": pdf_path.name,
                "pdf_path": str(pdf_path),
                "pages": gt["pages"],
                "is_scanned": gt["is_scanned"],
                "total_chars": gt["total_chars"],
                "has_tables": gt.get("has_pdfplumber_tables", False),
                "gt_candidate_doors": len(gt.get("candidate_door_nums", [])),
                "gt_candidate_hw_sets": len(gt.get("candidate_hw_set_ids", [])),
                "extracted_doors": 0,
                "extracted_hw_components": 0,
                "extracted_hw_sets": 0,
                "door_schema_score": 0,
                "hw_schema_score": 0,
                "elapsed_sec": round(elapsed, 1),
                "status": "ERROR",
                "issues": str(e),
                "extracted_door_nums": "",
                "extracted_hw_set_ids": "",
                "gt_hw_set_ids": "",
            })
            print(f"  !! ERROR: {e}")

    # ═══════════════════════════════════════════════════════════════
    #  WRITE REPORTS
    # ═══════════════════════════════════════════════════════════════
    df_report = pd.DataFrame(results)

    # CSV
    csv_path = OUT_DIR / "deep_e2e_report.csv"
    df_report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # Excel with formatting
    xlsx_path = OUT_DIR / "deep_e2e_report.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        # Main summary
        summary_cols = [
            "run_id", "project_id", "file", "pages", "is_scanned", "has_tables",
            "gt_candidate_doors", "gt_candidate_hw_sets",
            "extracted_doors", "extracted_hw_sets", "extracted_hw_components",
            "door_schema_score", "hw_schema_score",
            "elapsed_sec", "status", "issues",
        ]
        existing_summary_cols = [c for c in summary_cols if c in df_report.columns]
        df_report[existing_summary_cols].to_excel(writer, sheet_name="Summary", index=False)

        # Door numbers detail
        detail_cols = [
            "run_id", "project_id", "file", "extracted_doors", "extracted_door_nums",
        ]
        existing_detail = [c for c in detail_cols if c in df_report.columns]
        df_report[existing_detail].to_excel(writer, sheet_name="Door Numbers", index=False)

        # HW sets detail  
        hw_detail_cols = [
            "run_id", "project_id", "file", "extracted_hw_sets", "extracted_hw_set_ids",
            "gt_candidate_hw_sets", "gt_hw_set_ids",
        ]
        existing_hw = [c for c in hw_detail_cols if c in df_report.columns]
        df_report[existing_hw].to_excel(writer, sheet_name="HW Sets", index=False)

        # Schema fill rates
        fill_cols = [c for c in df_report.columns if c.endswith("_fill%")]
        if fill_cols:
            df_report[["run_id", "project_id", "file"] + fill_cols].to_excel(
                writer, sheet_name="Schema Fill Rates", index=False
            )

    # ═══════════════════════════════════════════════════════════════
    #  PRINT FINAL SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("  DEEP E2E TEST COMPLETE")
    print("=" * 80)

    total_pdfs = len(df_report)
    total_doors = int(df_report["extracted_doors"].sum())
    total_hw_sets = int(df_report["extracted_hw_sets"].sum())
    total_hw_items = int(df_report["extracted_hw_components"].sum())
    total_time = df_report["elapsed_sec"].sum()

    status_counts = df_report["status"].value_counts()

    print(f"\n  Total PDFs:        {total_pdfs}")
    print(f"  Total Doors:       {total_doors}")
    print(f"  Total HW Sets:     {total_hw_sets}")
    print(f"  Total HW Items:    {total_hw_items}")
    print(f"  Total Time:        {total_time/60:.1f} min")
    print(f"\n  Status breakdown:")
    for s, c in status_counts.items():
        print(f"    {s}: {c}")

    has_doors = (df_report["extracted_doors"] > 0).sum()
    has_hw = (df_report["extracted_hw_sets"] > 0).sum()
    print(f"\n  PDFs with doors:   {has_doors}/{total_pdfs} ({has_doors/total_pdfs*100:.0f}%)")
    print(f"  PDFs with HW sets: {has_hw}/{total_pdfs} ({has_hw/total_pdfs*100:.0f}%)")

    # Average schema scores (only for PDFs that had data)
    with_doors = df_report[df_report["extracted_doors"] > 0]
    with_hw = df_report[df_report["extracted_hw_sets"] > 0]
    if not with_doors.empty:
        avg_ds = with_doors["door_schema_score"].mean()
        print(f"  Avg Door Schema:   {avg_ds:.1f}%")
    if not with_hw.empty:
        avg_hs = with_hw["hw_schema_score"].mean()
        print(f"  Avg HW Schema:     {avg_hs:.1f}%")

    # Problem PDFs
    problems = df_report[df_report["status"].isin(["ZERO_EXTRACT", "ERROR", "MISSING_HW"])]
    if not problems.empty:
        print(f"\n  ⚠️  Problem PDFs ({len(problems)}):")
        for _, r in problems.iterrows():
            print(f"    [{r['status']}] {r['project_id']} / {r['file']}: {r['issues']}")

    print(f"\n  Reports saved to: {OUT_DIR.resolve()}")
    print(f"    - {csv_path.name}")
    print(f"    - {xlsx_path.name}")
    print("=" * 80)


if __name__ == "__main__":
    main()
