"""
Full pipeline: discover PDFs, run LLM+RAG extraction per page, aggregate, export Excel.

Key improvements:
1. Correct PDF folder discovery (recursive into subdirectories)
2. Page classification → targeted extraction (door OR hardware, not both blindly)
3. Multi-page continuity tracking
4. PRD-compliant aggregation (NO quantity doubling for pairs)
5. Deterministic pair detection
6. Proper deduplication
"""
import os
import re
import sys
import logging
from pathlib import Path
from typing import List, Tuple, Optional

import time
import pandas as pd

# Ensure UTF-8 for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import PDF_FOLDER, OUTPUT_DIR, MAX_PAGE_CHARS
from agent import extract_page_with_llm, ExtractionContext
from page_extractor import extract_structured_page, get_page_count, PageType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True,
)
logger = logging.getLogger("pipeline")


def log_anomaly_to_skills(pdf_name: str, page_idx: int, anomaly_type: str, raw_text: str):
    """
    Dynamically logs zero-extraction anomalies into the Master Skills documentation block 
    so the system is self-documenting regarding new architectural edge cases.
    """
    skills_path = Path("c:/Users/muzaf/my_lab/sushmita_proj/skills/MASTER_PDF_ANALYSIS_SKILLS.md")
    if not skills_path.exists():
        logger.warning("Agent Skills md missing! Unable to log anomaly.")
        return
        
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    snippet = raw_text[:800] + "...\n[TRUNCATED]" if len(raw_text) > 800 else raw_text
    
    try:
        with open(skills_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n### ⚠️ Auto-Logged Extraction Anomaly: {pdf_name} (Page {page_idx + 1})\n")
            f.write(f"- **Timestamp:** {now}\n")
            f.write(f"- **Issue:** Zero `{anomaly_type}` rows extracted despite explicit structural classification.\n")
            f.write("- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.\n")
            f.write("- **Raw Output Hook:**\n```text\n")
            f.write(f"{snippet}\n```\n")
            f.write("---\n")
    except Exception as e:
        logger.error("Failed to append to skills md: %s", e)


def discover_pdfs(folder: str) -> List[Tuple[Path, str]]:
    """
    Discover all PDFs in the folder (top-level and subdirectories).
    Returns list of (pdf_path, project_id).
    """
    folder = Path(folder)
    if not folder.exists():
        logger.error("PDF folder not found: %s", folder)
        return []

    pdfs = []

    # Top-level PDFs
    for f in sorted(folder.glob("*.pdf")):
        pid = _extract_project_id(f.stem)
        pdfs.append((f, pid))

    # Subdirectory PDFs
    for d in sorted(folder.iterdir()):
        if d.is_dir():
            pid = _extract_project_id(d.name)
            for pdf in sorted(d.rglob("*.pdf")):
                pdfs.append((pdf, pid))

    logger.info("Discovered %d PDFs in %s", len(pdfs), folder)
    return pdfs


def _extract_project_id(name: str) -> str:
    """Extract a clean project ID from a filename or directory name."""
    m = re.search(r"[Pp]roject\s*[-_]?\s*(\d+)", name)
    if m:
        return f"project_{m.group(1)}"
    # Try to extract just a number
    m2 = re.search(r"(\d+)", name)
    if m2:
        clean = re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s_-]+", "_", name.lower()))
        return clean or f"project_{m2.group(1)}"
    return re.sub(r"[^a-z0-9_]", "", re.sub(r"[\s_-]+", "_", name.lower())) or "unknown"


def classify_pdf_file(pdf_path: Path) -> str:
    """
    Quick classification of a PDF file based on filename.
    Returns 'door', 'hardware', or 'both'.
    """
    name = pdf_path.stem.upper()
    has_door = any(kw in name for kw in ("DOOR", "SCHEDULE", "OPENING"))
    has_hw = any(kw in name for kw in ("HARDWARE", "DIVISION", "DIV 8", "DIV8"))

    if has_door and has_hw:
        return "both"
    elif has_hw:
        return "hardware"
    return "both"  # Default: process as both (let page classifier decide)


def run_pipeline(
    pdf_folder: str = None,
    output_dir: str = None,
    max_pdfs: int = None,
    use_rag: bool = True,
    pdf_files: List[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run LLM+RAG extraction on targeted PDFs.
    Returns (df_doors, df_components).
    """
    pdf_folder = pdf_folder or PDF_FOLDER
    output_dir = output_dir or OUTPUT_DIR
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if pdf_files:
        pdfs = []
        for p in pdf_files:
            if not isinstance(p, Path):
                p = Path(p)
            pdfs.append((p, p.parent.name or "standalone"))
    else:
        pdfs = discover_pdfs(pdf_folder)
        if max_pdfs is not None:
            pdfs = pdfs[:max_pdfs]

    if not pdfs:
        logger.warning("No PDFs found in %s", pdf_folder)
        return pd.DataFrame(), pd.DataFrame()

    all_doors = []
    all_components = []
    project_stats = {}

    for pdf_path, project_id in pdfs:
        if not pdf_path.exists():
            continue

        fname = pdf_path.name
        logger.info("=" * 60)
        logger.info("Processing: %s [%s]", fname, project_id)

        n_pages = get_page_count(pdf_path)
        if n_pages == 0:
            logger.warning("Cannot read %s", fname)
            continue

        pdf_start_time = time.time()
        # Per-PDF extraction context for multi-page continuity
        ctx = ExtractionContext()
        prev_page_type = None

        for page_idx in range(n_pages):
            # Extract structured page content with classification
            t0 = time.time()
            text, page_type, is_continuation = extract_structured_page(
                pdf_path, page_idx,
                max_chars=MAX_PAGE_CHARS,
                prev_page_type=prev_page_type,
            )
            logger.info("Page %d Text/Structure extraction took %.1fs", page_idx + 1, time.time() - t0)

            if not text or len(text.strip()) < 30:
                continue

            # Skip pages that are clearly not relevant
            if page_type == PageType.OTHER and not is_continuation:
                logger.debug("Skipping page %d (classified as OTHER)", page_idx + 1)
                continue

            # Extract doors and/or hardware
            t1 = time.time()
            doors, hardware = extract_page_with_llm(
                text,
                page_type=page_type,
                page_idx=page_idx,
                use_rag=use_rag,
                retry_with_hint=True,
                is_continuation=is_continuation,
                context=ctx,
            )
            logger.info("Page %d LLM Extraction (%s) took %.1fs", page_idx + 1, page_type, time.time() - t1)

            # Automatic Anomaly Logging Hook
            if page_type == PageType.DOOR_SCHEDULE and not doors:
                logger.warning("Anomaly: Classified DOOR_SCHEDULE but 0 doors extracted for %s! Auto-logging.", fname)
                log_anomaly_to_skills(fname, page_idx, "DOOR", text)
                
            if page_type == PageType.HARDWARE_SET and not hardware:
                logger.warning("Anomaly: Classified HARDWARE_SET but 0 hardware items extracted for %s! Auto-logging.", fname)
                log_anomaly_to_skills(fname, page_idx, "HARDWARE", text)

            # Tag and collect doors
            for d in doors:
                d["project_id"] = project_id
                d["source_file"] = fname
                d["page"] = page_idx + 1
                all_doors.append(d)

            # Tag and collect hardware
            for h in hardware:
                h["project_id"] = project_id
                h["source_file"] = fname
                h["page"] = page_idx + 1
                all_components.append(h)

            prev_page_type = page_type
            
        logger.info("Finished processing %s in %.1fs", fname, time.time() - pdf_start_time)

        # Update project stats
        key = project_id
        if key not in project_stats:
            project_stats[key] = {"doors": 0, "components": 0, "files": []}
        project_stats[key]["files"] = list(set(project_stats[key]["files"] + [fname]))
        project_stats[key]["doors"] = sum(
            1 for d in all_doors if d.get("project_id") == key
        )
        project_stats[key]["components"] = sum(
            1 for c in all_components if c.get("project_id") == key
        )

    # ═══════════════════════════════════════════════════════════════
    #  POST-PROCESSING
    # ═══════════════════════════════════════════════════════════════

    # Build DataFrames
    df_doors = pd.DataFrame(all_doors)
    df_components = pd.DataFrame(all_components)

    # Deduplicate doors by (project_id, door_number) — keep first occurrence
    if not df_doors.empty and "project_id" in df_doors.columns and "door_number" in df_doors.columns:
        before = len(df_doors)
        df_doors = df_doors.drop_duplicates(
            subset=["project_id", "door_number"], keep="first"
        ).reset_index(drop=True)
        dupes = before - len(df_doors)
        if dupes:
            logger.info("Removed %d duplicate door rows", dupes)

    # ── Columns for output ──
    door_cols = [
        "project_id", "source_file", "page", "door_number", "level_area",
        "room_name", "door_type", "frame_type", "frame_width", "frame_height",
        "door_width", "door_height", "hardware_set", "fire_rating",
        "head_jamb_sill_detail", "keyed_notes", "remarks",
        "door_slab_material", "vision_panel", "glazing_type", "finish",
        "is_pair", "door_leaves",
    ]
    df_doors_out = _reorder_columns(df_doors, door_cols)

    comp_cols = [
        "project_id", "source_file", "page", "hardware_set_id",
        "hardware_set_name", "qty", "unit", "description",
        "catalog_number", "finish_code", "manufacturer_code", "notes",
    ]
    df_comp_out = _reorder_columns(df_components, comp_cols)

    # ═══════════════════════════════════════════════════════════════
    #  AGGREGATION (PRD Milestone 1)
    # ═══════════════════════════════════════════════════════════════
    milestone1 = pd.DataFrame()
    door_agg = pd.DataFrame()

    if not df_doors_out.empty and "hardware_set" in df_doors_out.columns:
        df_doors_out["hardware_set_clean"] = (
            df_doors_out["hardware_set"].fillna("").astype(str).str.strip()
        )

        # Only aggregate doors with valid hardware sets
        valid = df_doors_out[df_doors_out["hardware_set_clean"] != ""]

        if not valid.empty:
            door_agg = valid.groupby(["project_id", "hardware_set_clean"]).agg(
                total_doors=("door_number", "count"),
                unit_doors=("is_pair", lambda x: (~x.astype(bool)).sum()),
                pair_doors=("is_pair", lambda x: x.astype(bool).sum()),
                door_leaves=("door_leaves", "sum"),
            ).reset_index()
            door_agg = door_agg.rename(columns={"hardware_set_clean": "hardware_set_id"})

    if not df_comp_out.empty and "hardware_set_id" in df_comp_out.columns and not door_agg.empty:
        # Merge hardware components with door aggregation
        comp_for_merge = df_comp_out[[
            c for c in [
                "project_id", "hardware_set_id", "hardware_set_name",
                "qty", "unit", "description", "catalog_number",
                "finish_code", "manufacturer_code",
            ] if c in df_comp_out.columns
        ]].copy()

        milestone1 = door_agg.merge(
            comp_for_merge,
            on=["project_id", "hardware_set_id"],
            how="left",
        )

        # PRD CRITICAL: qty is AS-STATED in Division 8 (already pair-adjusted)
        # total_qty = qty_per_set × total_doors (NOT door_leaves!)
        milestone1["qty_per_set"] = milestone1["qty"].fillna(0).astype(int)
        milestone1["total_qty_project"] = (
            milestone1["qty_per_set"] * milestone1["total_doors"]
        )

        # Drop helper column
        if "hardware_set_clean" in df_doors_out.columns:
            df_doors_out = df_doors_out.drop(columns=["hardware_set_clean"])

    # ═══════════════════════════════════════════════════════════════
    #  WRITE OUTPUT
    # ═══════════════════════════════════════════════════════════════
    excel_path = Path(output_dir) / "extraction_results_llm.xlsx"

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        if not df_doors_out.empty:
            df_doors_out.to_excel(writer, sheet_name="Door Schedule", index=False)
        if not df_comp_out.empty:
            df_comp_out.to_excel(writer, sheet_name="Hardware Components", index=False)
        if not milestone1.empty:
            milestone1.to_excel(writer, sheet_name="Milestone1 Aggregate", index=False)
        if not door_agg.empty:
            door_agg.to_excel(writer, sheet_name="Door Aggregation", index=False)

        # Project summary
        summary = pd.DataFrame([
            {
                "project_id": pid,
                "files_processed": "; ".join(s.get("files", [])),
                "doors_extracted": s.get("doors", 0),
                "hw_components_extracted": s.get("components", 0),
            }
            for pid, s in sorted(project_stats.items())
        ])
        summary.to_excel(writer, sheet_name="Project Summary", index=False)

    logger.info("Wrote %s", excel_path)

    # Also write CSVs
    if not df_doors_out.empty:
        df_doors_out.to_csv(Path(output_dir) / "door_schedule_llm.csv", index=False)
    if not df_comp_out.empty:
        df_comp_out.to_csv(Path(output_dir) / "hardware_components_llm.csv", index=False)
    if not milestone1.empty:
        milestone1.to_csv(Path(output_dir) / "milestone1_aggregate.csv", index=False)

    logger.info(
        "Pipeline complete: %d doors, %d hardware components, %d projects",
        len(df_doors_out), len(df_comp_out), len(project_stats),
    )

    return df_doors_out, df_comp_out


def _reorder_columns(df: pd.DataFrame, desired_cols: list) -> pd.DataFrame:
    """Reorder DataFrame columns, keeping only those that exist."""
    if df.empty:
        return pd.DataFrame()
    existing = [c for c in desired_cols if c in df.columns]
    extra = [c for c in df.columns if c not in desired_cols]
    return df[existing + extra].copy()
