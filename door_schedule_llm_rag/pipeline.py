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
import agent as _agent_module  # access LAST_VERIFY_REPORT after each page
from agent import extract_page_with_llm, ExtractionContext
from page_extractor import extract_structured_page, get_page_count, PageType
from page_evidence import collect as collect_evidence, confidence_score
from llm_extract import llm_config, is_probable_hardware_component
from db_utils import save_estimations_to_db

try:
    from cloud_storage import upload_file_to_s3
except Exception:
    upload_file_to_s3 = None

# RAG + run-store (soft imports so a missing optional dep never kills the pipeline)
try:
    from rag_store import (
        ensure_seeded as _rag_ensure_seeded,
        record_door_example,
        record_hardware_example,
        record_anomaly,
        status as _rag_status,
        is_available as _rag_available,
    )
except Exception as _rag_e:  # pragma: no cover
    logging.getLogger("pipeline").warning("rag_store unavailable: %s", _rag_e)

    def _rag_ensure_seeded(force: bool = False):
        return {}

    def record_door_example(*_args, **_kwargs):
        return False

    def record_hardware_example(*_args, **_kwargs):
        return False

    def record_anomaly(*_args, **_kwargs):
        return False

    def _rag_status():
        return {"available": 0}

    def _rag_available():
        return False

try:
    from run_store import RunLogger
except Exception:  # pragma: no cover
    RunLogger = None  # type: ignore[assignment]

try:
    from mineru_backend import is_available as _mineru_available
except Exception:  # pragma: no cover
    def _mineru_available() -> bool:  # type: ignore[misc]
        return False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True,
)
logger = logging.getLogger("pipeline")

LAST_CROP_METRICS = {
    "crop_count": 0,
    "crop_rescue_attempt_pages": 0,
    "crop_rescue_pages": 0,
    "crop_door_added": 0,
    "crop_hw_added": 0,
}


def log_anomaly_to_skills(pdf_name: str, page_idx: int, anomaly_type: str, raw_text: str):
    """
    Dynamically logs zero-extraction anomalies into the Master Skills documentation block 
    so the system is self-documenting regarding new architectural edge cases.
    """
    skills_path = Path(__file__).resolve().parent / "docs" / "EDGE_CASE_LOG.md"
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


def _source_methods_from_text(text: str) -> str:
    methods = []
    for match in re.findall(r"\[Source:\s*([^\]]+)\]", text or ""):
        method = match.strip()
        if method and method not in methods:
            methods.append(method)
    if "VISION LLM EXTRACTION" in (text or "") and "vision_llm" not in methods:
        methods.append("vision_llm")
    if not methods:
        methods.append("unknown")
    return ";".join(methods)


def _verification_flags(verify_report: Optional[dict], anomaly_reason: Optional[str]) -> str:
    flags = []
    if anomaly_reason:
        flags.append(anomaly_reason)
    if verify_report:
        for key, label in (
            ("door_rescue", "door_rescue"),
            ("hw_rescue", "hardware_rescue"),
            ("crop_rescue", "crop_rescue"),
            ("crop_rescue_attempted", "crop_rescue_attempted"),
        ):
            if verify_report.get(key):
                flags.append(label)
    return ";".join(dict.fromkeys(flags))


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
    global LAST_CROP_METRICS
    LAST_CROP_METRICS = {
        "crop_count": 0,
        "crop_rescue_attempt_pages": 0,
        "crop_rescue_pages": 0,
        "crop_door_added": 0,
        "crop_hw_added": 0,
    }

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

    # ── Boot-time: make sure RAG is seeded so the agent and verification
    # layer actually have context on the first page. This is the fix for the
    # previous silent "RAG returns []" bug.
    try:
        status = _rag_ensure_seeded()
        if status.get("available"):
            logger.info(
                "RAG ready: instructions[door=%d, hw=%d], examples[door=%d, hw=%d], anomalies=%d",
                status.get("instructions_door", 0),
                status.get("instructions_hardware", 0),
                status.get("examples_door", 0),
                status.get("examples_hardware", 0),
                status.get("anomalies", 0),
            )
        else:
            logger.warning(
                "RAG is NOT available — pipeline will run without retrieval context. "
                "This is OK but reduces long-term self-improvement."
            )
    except Exception as e:
        logger.warning("RAG seeding skipped: %s", e)

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

        # Per-PDF durable run log. Each PDF gets its own JSONL file so
        # Streamlit can stream it back or users can grep historical runs.
        run_logger = None
        if RunLogger is not None:
            try:
                active_model = (
                    llm_config.openai_model if llm_config.provider == "openai"
                    else llm_config.groq_model if llm_config.provider == "groq"
                    else llm_config.ollama_model
                )
                run_logger = RunLogger(
                    pdf_name=fname,
                    provider=llm_config.provider,
                    model=active_model,
                    use_rag=bool(use_rag),
                    mineru_available=_mineru_available(),
                )
                run_logger.start()
            except Exception as e:
                logger.debug("RunLogger init failed: %s", e)
                run_logger = None

        for page_idx in range(n_pages):
            # Extract structured page content with classification
            t0 = time.time()
            text, page_type, is_continuation, base64_img, crop_candidates = extract_structured_page(
                pdf_path, page_idx,
                max_chars=MAX_PAGE_CHARS,
                prev_page_type=prev_page_type,
                include_crops=True,
            )
            logger.info("Page %d Text/Structure extraction took %.1fs", page_idx + 1, time.time() - t0)
            LAST_CROP_METRICS["crop_count"] += len(crop_candidates or [])

            if not text or len(text.strip()) < 30:
                continue

            # Skip pages that are clearly not relevant
            if page_type == PageType.OTHER and not is_continuation and not crop_candidates:
                logger.debug("Skipping page %d (classified as OTHER)", page_idx + 1)
                continue
            if page_type == PageType.OTHER and crop_candidates:
                logger.warning(
                    "Page %d classified OTHER but has %d crop candidates; processing as MIXED.",
                    page_idx + 1,
                    len(crop_candidates),
                )
                page_type = PageType.MIXED

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
                base64_image=base64_img,
                crop_candidates=crop_candidates,
            )
            logger.info("Page %d LLM Extraction (%s) took %.1fs", page_idx + 1, page_type, time.time() - t1)

            # ── Evidence snapshot for durable logging + learning ──
            evidence = collect_evidence(text)
            page_confidence = round(confidence_score(evidence), 3)
            source_methods = _source_methods_from_text(text)
            verify_report = getattr(_agent_module, "LAST_VERIFY_REPORT", None)
            if verify_report and verify_report.get("crop_rescue"):
                LAST_CROP_METRICS["crop_rescue_pages"] += 1
                LAST_CROP_METRICS["crop_door_added"] += int(verify_report.get("crop_door_added") or 0)
                LAST_CROP_METRICS["crop_hw_added"] += int(verify_report.get("crop_hw_added") or 0)
            if verify_report and verify_report.get("crop_rescue_attempted"):
                LAST_CROP_METRICS["crop_rescue_attempt_pages"] += 1

            # ── Automatic Anomaly Logging Hook ──
            anomaly_reason: Optional[str] = None
            if page_type == PageType.DOOR_SCHEDULE and not doors:
                anomaly_reason = "DOOR_ZERO_EXTRACT"
                logger.warning("Anomaly: Classified DOOR_SCHEDULE but 0 doors extracted for %s! Auto-logging.", fname)
                log_anomaly_to_skills(fname, page_idx, "DOOR", text)
            if page_type == PageType.HARDWARE_SET and not hardware:
                anomaly_reason = "HW_ZERO_EXTRACT"
                logger.warning("Anomaly: Classified HARDWARE_SET but 0 hardware items extracted for %s! Auto-logging.", fname)
                log_anomaly_to_skills(fname, page_idx, "HARDWARE", text)

            # Persist anomaly into RAG so similar future pages retrieve it as context.
            if anomaly_reason:
                try:
                    record_anomaly(
                        page_text=text,
                        reason=anomaly_reason,
                        source_file=fname,
                        page=page_idx + 1,
                        evidence=evidence.as_dict(),
                        verify_report=verify_report,
                    )
                except Exception as e:
                    logger.debug("record_anomaly failed: %s", e)

            # ── Learn from successful extractions ──
            # Each time we get a meaningful result, save a compact few-shot
            # example. Future pages with similar signals will retrieve it
            # via the RAG query in `agent.extract_page_with_llm`.
            try:
                if doors:
                    record_door_example(
                        page_text=text,
                        doors=doors,
                        source_file=fname,
                        page=page_idx + 1,
                    )
                if hardware:
                    record_hardware_example(
                        page_text=text,
                        hardware=hardware,
                        source_file=fname,
                        page=page_idx + 1,
                    )
            except Exception as e:
                logger.debug("record_example failed: %s", e)

            # ── Per-page durable event ──
            if run_logger is not None:
                try:
                    run_logger.event(
                        "page_extracted",
                        page=page_idx + 1,
                        page_type=page_type,
                        doors=len(doors),
                        hardware=len(hardware),
                        evidence=evidence.as_dict(),
                        verify_report=verify_report,
                        crop_count=len(crop_candidates or []),
                        anomaly=anomaly_reason,
                    )
                except Exception as e:
                    logger.debug("run_logger.event failed: %s", e)

            # Tag and collect doors
            for d in doors:
                d["project_id"] = project_id
                d["source_file"] = fname
                d["page"] = page_idx + 1
                d["page_type"] = page_type
                d["source_method"] = source_methods
                d["source_confidence"] = page_confidence
                d["source_location"] = f"{fname}#page={page_idx + 1}"
                d["evidence_expected_door_rows"] = evidence.expected_door_rows()
                d["verification_flags"] = _verification_flags(verify_report, anomaly_reason)
                all_doors.append(d)

            # Tag and collect hardware
            for h in hardware:
                h["project_id"] = project_id
                h["source_file"] = fname
                h["page"] = page_idx + 1
                h["page_type"] = page_type
                h["source_method"] = source_methods
                h["source_confidence"] = page_confidence
                h["source_location"] = f"{fname}#page={page_idx + 1}"
                h["evidence_expected_hw_sets"] = evidence.expected_hw_sets()
                h["verification_flags"] = _verification_flags(verify_report, anomaly_reason)
                all_components.append(h)

            prev_page_type = page_type

        logger.info("Finished processing %s in %.1fs", fname, time.time() - pdf_start_time)

        # ── Close durable run log ──
        if run_logger is not None:
            try:
                run_logger.finish(
                    doors=sum(1 for d in all_doors if d.get("source_file") == fname),
                    hardware=sum(1 for h in all_components if h.get("source_file") == fname),
                    status="OK",
                )
            except Exception as e:
                logger.debug("run_logger.finish failed: %s", e)

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

    # Flatten extra_fields to native columns before making DataFrames
    def _flatten(data_list):
        for d in data_list:
            if "extra_fields" in d and isinstance(d["extra_fields"], dict):
                for k, v in d["extra_fields"].items():
                    if k not in d:
                        d[k] = v
                del d["extra_fields"]
        return pd.DataFrame(data_list)

    df_doors = _flatten(all_doors)
    df_components = _flatten(all_components)

    if not df_components.empty and "description" in df_components.columns:
        before_hw_noise = len(df_components)
        df_components = df_components[
            df_components.apply(lambda row: is_probable_hardware_component(row.to_dict()), axis=1)
        ].reset_index(drop=True)
        filtered_hw_noise = before_hw_noise - len(df_components)
        if filtered_hw_noise:
            logger.info(
                "Filtered %d hardware rows that looked like headers, title blocks, notes, or door-schedule noise.",
                filtered_hw_noise,
            )

    def _clean_join_id(value) -> str:
        if pd.isna(value):
            return ""
        s = str(value).strip().upper()
        if s in ("", "N/A", "NA", "NONE", "NULL", "?", "-", "—"):
            return ""
        if s.endswith(".0"):
            s = s[:-2]
        return re.sub(r"^(?:HW|HDWR|HARDWARE|SET|GROUP)[\s.#:-]*", "", s).strip()

    # Validate door hardware_set values against extracted hardware-set IDs.
    # Preserve the source value for QA/provenance, but mark whether it can join
    # to component rows. Earlier code erased unmatched values; that hid real
    # source data and made bad joins harder to review.
    valid_hw_ids = set()
    if not df_components.empty and "hardware_set_id" in df_components.columns:
        valid_hw_ids = {
            _clean_join_id(v)
            for v in df_components["hardware_set_id"].dropna().tolist()
            if _clean_join_id(v)
        }
    if valid_hw_ids and not df_doors.empty and "hardware_set" in df_doors.columns:
        df_doors["hardware_set_clean"] = df_doors["hardware_set"].apply(_clean_join_id)
        df_doors["hardware_set_join_status"] = df_doors["hardware_set_clean"].apply(
            lambda v: "matched" if v and v in valid_hw_ids else "unmatched" if v else "missing"
        )
        invalid = int((df_doors["hardware_set_join_status"] == "unmatched").sum())
        if invalid > 0:
            logger.info(
                "Marked %d door hardware_set values as unmatched against extracted hardware set IDs.",
                invalid,
            )
    elif not df_doors.empty and "hardware_set" in df_doors.columns:
        df_doors["hardware_set_clean"] = df_doors["hardware_set"].apply(_clean_join_id)
        df_doors["hardware_set_join_status"] = df_doors["hardware_set_clean"].apply(
            lambda v: "not_checked_no_hardware_components" if v else "missing"
        )

    # ── Cross-reference: back-fill missing hardware_set on doors ──
    # If a project has hardware components but door rows are missing the
    # hardware_set column, try to infer it from the hardware side.
    if not df_doors.empty and not df_components.empty and "hardware_set" in df_doors.columns:
        orphan_mask = df_doors["hardware_set"].isna() | (df_doors["hardware_set"].astype(str).str.strip() == "")
        if orphan_mask.any():
            logger.info("Cross-reference: %d doors missing hardware_set, attempting back-fill.", orphan_mask.sum())
            
            for pid in df_doors.loc[orphan_mask, "project_id"].unique():
                proj_hw = df_components[df_components["project_id"] == pid]
                if proj_hw.empty:
                    continue
                
                hw_set_ids = proj_hw["hardware_set_id"].dropna().unique()
                
                # Strategy 1: If the project has exactly 1 hardware set,
                # assign all orphan doors to it.
                if len(hw_set_ids) == 1:
                    mask = orphan_mask & (df_doors["project_id"] == pid)
                    df_doors.loc[mask, "hardware_set"] = str(hw_set_ids[0])
                    logger.info("Cross-ref: assigned %d orphan doors in %s to sole HW set '%s'.",
                                mask.sum(), pid, hw_set_ids[0])
                    continue
                
                # Avoid fuzzy room/name matching here. It produced confident but
                # incorrect hardware joins on tests where hardware_set_name
                # contains room-like words or numbers unrelated to door marks.
            
            filled = orphan_mask.sum() - (df_doors["hardware_set"].isna() | (df_doors["hardware_set"].astype(str).str.strip() == "")).sum()
            if filled > 0:
                logger.info("Cross-reference back-filled %d hardware_set values.", filled)
                valid_hw_ids = {
                    _clean_join_id(v)
                    for v in df_components["hardware_set_id"].dropna().tolist()
                    if _clean_join_id(v)
                }
                df_doors["hardware_set_clean"] = df_doors["hardware_set"].apply(_clean_join_id)
                df_doors["hardware_set_join_status"] = df_doors["hardware_set_clean"].apply(
                    lambda v: "matched" if v and v in valid_hw_ids else "unmatched" if v else "missing"
                )

    # ── Ghost Door Filter: Remove doors with NO physical attributes ──
    # Hardware pages often list door numbers under hardware sets. The LLM might extract these 
    # as door rows, but they lack all physical dimensions/materials.
    if not df_doors.empty:
        phys_cols = ["door_width", "door_height", "door_thickness", "door_material", "door_type", "frame_material", "fire_rating"]
        existing = [c for c in phys_cols if c in df_doors.columns]
        if existing:
            before_ghosts = len(df_doors)
            valid_mask = df_doors[existing].notna().any(axis=1) | (df_doors["door_number"].astype(str).str.strip() == "")
            df_doors = df_doors[valid_mask].reset_index(drop=True)
            ghosts = before_ghosts - len(df_doors)
            if ghosts > 0:
                logger.info("Filtered %d 'ghost doors' (likely scraped from hardware lists)", ghosts)

    # Deduplicate doors by (project_id, door_number) — keep row with most fields populated
    if not df_doors.empty and "project_id" in df_doors.columns and "door_number" in df_doors.columns:
        before = len(df_doors)
        # Score each row by how many non-null fields it has
        df_doors["_completeness"] = df_doors.notna().sum(axis=1)
        df_doors = df_doors.sort_values("_completeness", ascending=False)
        df_doors = df_doors.drop_duplicates(
            subset=["project_id", "door_number"], keep="first"
        ).reset_index(drop=True)
        df_doors = df_doors.drop(columns=["_completeness"])
        dupes = before - len(df_doors)
        if dupes:
            logger.info("Removed %d duplicate door rows (kept most complete)", dupes)

    # ── Columns for output ──
    door_cols = [
        "project_id", "source_file", "page", "page_type", "source_method", "source_confidence",
        "source_location", "verification_flags", "evidence_expected_door_rows",
        "door_number", "elevation", "level_area",
        "room_name", "door_type", "door_thickness", "door_material", "door_finish", "frame_type", "frame_material", "frame_finish", "frame_width", "frame_height",
        "door_width", "door_height", "hardware_set", "hardware_set_clean", "hardware_set_join_status", "fire_rating",
        "head_jamb_sill_detail", "keyed_notes", "remarks",
        "door_slab_material", "vision_panel", "glazing_type", "finish",
        "is_pair", "door_leaves",
    ]
    df_doors_out = _reorder_columns(df_doors, door_cols)

    comp_cols = [
        "project_id", "source_file", "page", "page_type", "source_method", "source_confidence",
        "source_location", "verification_flags", "evidence_expected_hw_sets", "hardware_set_id",
        "hardware_set_name", "qty", "qty_raw", "unit", "description",
        "catalog_number", "finish_code", "manufacturer_code", "notes",
    ]
    df_comp_out = _reorder_columns(df_components, comp_cols)

    # ═══════════════════════════════════════════════════════════════
    #  AGGREGATION (PRD Milestone 1)
    # ═══════════════════════════════════════════════════════════════
    milestone1 = pd.DataFrame()
    door_agg = pd.DataFrame()

    if not df_doors_out.empty and "hardware_set" in df_doors_out.columns:
        def _clean_hw(val):
            if pd.isna(val) or val == "":
                return ""
            return _clean_join_id(val)

        df_doors_out["hardware_set_clean"] = df_doors_out["hardware_set"].apply(_clean_hw)

        # Only aggregate doors with joinable hardware sets when component IDs exist.
        valid = df_doors_out[df_doors_out["hardware_set_clean"] != ""]
        if "hardware_set_join_status" in valid.columns and not df_comp_out.empty:
            valid = valid[valid["hardware_set_join_status"] == "matched"]

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
        
        # Clean the right-hand join key identically
        comp_for_merge["hardware_set_id"] = comp_for_merge["hardware_set_id"].apply(_clean_hw)

        milestone1 = door_agg.merge(
            comp_for_merge,
            on=["project_id", "hardware_set_id"],
            how="left",
        )

        # PRD CRITICAL: qty is AS-STATED in Division 8 (already pair-adjusted)
        # total_qty = qty_per_set × total_doors (NOT door_leaves!)
        milestone1["qty_per_set"] = pd.to_numeric(milestone1["qty"], errors="coerce").fillna(0).astype(int)
        milestone1["total_qty_project"] = (
            milestone1["qty_per_set"] * milestone1["total_doors"]
        )

        # Save to database
        try:
            save_estimations_to_db(milestone1, df_doors_out)
            logger.info("Saved Milestone 1 data to centralized database.")
        except Exception as e:
            logger.error("Failed to save to database: %s", e)

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

    # ── Upload to S3 if configured ──
    if upload_file_to_s3:
        excel_name = excel_path.name
        upload_file_to_s3(str(excel_path), f"exports/{excel_name}")
        
        if not df_doors_out.empty:
            upload_file_to_s3(str(Path(output_dir) / "door_schedule_llm.csv"), "exports/door_schedule_llm.csv")
        if not df_comp_out.empty:
            upload_file_to_s3(str(Path(output_dir) / "hardware_components_llm.csv"), "exports/hardware_components_llm.csv")
        if not milestone1.empty:
            upload_file_to_s3(str(Path(output_dir) / "milestone1_aggregate.csv"), "exports/milestone1_aggregate.csv")
        logger.info("Uploaded output files to S3.")

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
