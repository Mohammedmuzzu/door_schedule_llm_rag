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
import json
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

from config import (
    PDF_FOLDER,
    OUTPUT_DIR,
    MAX_PAGE_CHARS,
    HYBRID_DIRECT_PDF,
    HYBRID_DIRECT_PDF_MODE,
)
import agent as _agent_module  # access LAST_VERIFY_REPORT after each page
from agent import extract_page_with_llm, ExtractionContext
from page_extractor import extract_structured_page, get_page_count, PageType
from page_evidence import collect as collect_evidence, confidence_score
from llm_extract import llm_config, is_probable_hardware_component, extract_pdf_direct_openai
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


def _is_likely_quote_or_proposal_pdf(filename: str) -> bool:
    name = str(filename or "").strip().lower()
    return (
        "proposal" in name
        or bool(re.match(r"p\d{2}[_-]", name))
        or bool(re.match(r"p\d{2,}[_-]", name))
    )


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


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "always"}


def _resolve_hybrid_direct_pdf_mode(
    enabled: Optional[bool],
    mode: Optional[str],
) -> str:
    if mode:
        clean = str(mode).strip().lower()
    elif enabled is True:
        clean = "rescue"
    elif enabled is False:
        clean = "off"
    else:
        raw = str(HYBRID_DIRECT_PDF or "0").strip().lower()
        clean = "always" if raw in {"1", "true", "yes", "on", "always"} else raw
        if clean not in {"always", "rescue"}:
            clean = (HYBRID_DIRECT_PDF_MODE or "off").strip().lower()
    return clean if clean in {"off", "rescue", "always"} else "off"


def _should_run_direct_pdf_witness(mode: str, pdf_doors: list[dict], pdf_hardware: list[dict]) -> bool:
    if mode == "always":
        return True
    if mode != "rescue":
        return False
    if not pdf_doors and not pdf_hardware:
        return True
    if pdf_doors:
        missing_dims = sum(
            1 for row in pdf_doors
            if _is_blank(row.get("door_width")) or _is_blank(row.get("door_height"))
        )
        if missing_dims / max(len(pdf_doors), 1) > 0.5:
            return True
    if pdf_hardware:
        unique_sets = {_clean_join_id(row.get("hardware_set_id")) for row in pdf_hardware}
        unique_sets.discard("")
        if len(pdf_hardware) < 3 and len(unique_sets) <= 1:
            return True
    return False


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    return str(value).strip().upper() in {"", "N/A", "NA", "NONE", "NULL", "?", "-", "--", "---", "----"}


def _clean_join_id(value) -> str:
    if _is_blank(value):
        return ""
    s = str(value).strip().upper()
    if s.endswith(".0"):
        s = s[:-2]
    return re.sub(r"^(?:HW|HDWR|HARDWARE|SET|GROUP)[\s.#:-]*", "", s).strip()


def _backfill_orphan_hw_sets_by_door_number(
    df_doors: pd.DataFrame,
    df_components: pd.DataFrame,
    project_id: object | None = None,
) -> int:
    """Assign blank door hardware_set when a component set ID exactly matches the door mark."""
    if df_doors.empty or df_components.empty:
        return 0
    if "door_number" not in df_doors.columns or "hardware_set" not in df_doors.columns:
        return 0
    if "hardware_set_id" not in df_components.columns:
        return 0

    door_mask = pd.Series(True, index=df_doors.index)
    comp_mask = pd.Series(True, index=df_components.index)
    if project_id is not None and "project_id" in df_doors.columns:
        door_mask &= df_doors["project_id"] == project_id
    if project_id is not None and "project_id" in df_components.columns:
        comp_mask &= df_components["project_id"] == project_id

    hw_lookup: dict[str, str] = {}
    for raw in df_components.loc[comp_mask, "hardware_set_id"].dropna().tolist():
        clean = _clean_join_id(raw)
        if clean and clean not in hw_lookup:
            hw_lookup[clean] = str(raw).strip()
    if not hw_lookup:
        return 0

    orphan_mask = door_mask & (
        df_doors["hardware_set"].isna()
        | (df_doors["hardware_set"].astype(str).str.strip() == "")
    )
    filled = 0
    for idx in df_doors.loc[orphan_mask].index:
        key = _clean_join_id(df_doors.at[idx, "door_number"])
        if key in hw_lookup:
            df_doors.at[idx, "hardware_set"] = hw_lookup[key]
            filled += 1
    return filled


def _append_semicolon(value: object, token: str) -> str:
    parts = [p for p in str(value or "").split(";") if p]
    if token not in parts:
        parts.append(token)
    return ";".join(parts)


def _direct_pdf_source_page(row: dict):
    extra = row.get("extra_fields")
    if isinstance(extra, dict):
        for key in ("source_page", "page"):
            value = extra.pop(key, None)
            if not _is_blank(value):
                return value
    return None


def _door_key(row: dict) -> str:
    return str(row.get("door_number") or "").strip().upper()


def _hardware_key(row: dict) -> tuple[str, str]:
    hw_id = _clean_join_id(row.get("hardware_set_id"))
    catalog = str(row.get("catalog_number") or "").strip().upper()
    desc = re.sub(r"\s+", " ", str(row.get("description") or "").strip().upper())
    return hw_id, catalog or desc


def _door_physical_score(row: dict) -> int:
    return sum(
        1 for field in (
            "door_width", "door_height", "door_thickness", "door_material",
            "door_type", "frame_material", "frame_type", "fire_rating",
        )
        if not _is_blank(row.get(field))
    )


_HYBRID_METADATA_FIELDS = {
    "project_id", "source_file", "page", "page_type", "source_method",
    "source_confidence", "source_location", "verification_flags",
    "evidence_expected_door_rows", "evidence_expected_hw_sets",
    "hardware_set_clean", "hardware_set_join_status", "hybrid_decision",
}


def _merge_missing_fields(target: dict, witness: dict) -> int:
    filled = 0
    for key, value in witness.items():
        if key in _HYBRID_METADATA_FIELDS or key == "extra_fields" or _is_blank(value):
            continue
        if _is_blank(target.get(key)):
            target[key] = value
            filled += 1
    extra = witness.get("extra_fields")
    if isinstance(extra, dict) and extra:
        target_extra = target.setdefault("extra_fields", {})
        if isinstance(target_extra, dict):
            for key, value in extra.items():
                if key not in target_extra and not _is_blank(value):
                    target_extra[key] = value
    return filled


_HYBRID_COMPARE_FIELDS = (
    "room_name", "door_type", "door_width", "door_height", "door_thickness",
    "door_material", "door_finish", "frame_type", "frame_material",
    "frame_finish", "hardware_set", "fire_rating", "hardware_set_id",
    "hardware_set_name", "qty", "qty_raw", "unit", "description",
    "catalog_number", "finish_code", "manufacturer_code",
)


def _compare_value(value: object) -> str:
    if _is_blank(value):
        return ""
    return re.sub(r"[^A-Z0-9]+", "", str(value).upper())


def _record_direct_pdf_conflicts(target: dict, witness: dict) -> int:
    conflicts = []
    for field in _HYBRID_COMPARE_FIELDS:
        if _is_blank(target.get(field)) or _is_blank(witness.get(field)):
            continue
        if _compare_value(target.get(field)) == _compare_value(witness.get(field)):
            continue
        conflicts.append(f"{field}: text={target.get(field)!r} direct_pdf={witness.get(field)!r}")
    if not conflicts:
        return 0
    existing = [part for part in str(target.get("hybrid_conflicts") or "").split("; ") if part]
    for conflict in conflicts:
        if conflict not in existing:
            existing.append(conflict)
    target["hybrid_conflicts"] = "; ".join(existing)
    target["verification_flags"] = _append_semicolon(target.get("verification_flags"), "direct_pdf_conflict")
    target["hybrid_decision"] = _append_semicolon(target.get("hybrid_decision"), "direct_pdf_conflict")
    return len(conflicts)


def _tag_direct_door(row: dict, pdf_name: str, project_id: str, decision: str) -> dict:
    row = dict(row)
    source_page = _direct_pdf_source_page(row)
    row["project_id"] = project_id
    row["source_file"] = pdf_name
    row["page"] = source_page
    row["page_type"] = "DIRECT_PDF"
    row["source_method"] = "openai_direct_pdf"
    row["source_confidence"] = 0.72
    row["source_location"] = f"{pdf_name}#direct-pdf"
    row["evidence_expected_door_rows"] = None
    row["verification_flags"] = decision
    row["hybrid_decision"] = decision
    return row


def _tag_direct_hardware(row: dict, pdf_name: str, project_id: str, decision: str) -> dict:
    row = dict(row)
    source_page = _direct_pdf_source_page(row)
    row["project_id"] = project_id
    row["source_file"] = pdf_name
    row["page"] = source_page
    row["page_type"] = "DIRECT_PDF"
    row["source_method"] = "openai_direct_pdf"
    row["source_confidence"] = 0.72
    row["source_location"] = f"{pdf_name}#direct-pdf"
    row["evidence_expected_hw_sets"] = None
    row["verification_flags"] = decision
    row["hybrid_decision"] = decision
    return row


def _merge_direct_pdf_witness(
    all_doors: list[dict],
    all_components: list[dict],
    door_start_idx: int,
    hardware_start_idx: int,
    direct_doors: list[dict],
    direct_hardware: list[dict],
    *,
    pdf_name: str,
    project_id: str,
) -> dict:
    metrics = {
        "door_confirmed": 0,
        "door_added": 0,
        "door_fields_filled": 0,
        "hardware_confirmed": 0,
        "hardware_added": 0,
        "hardware_fields_filled": 0,
        "door_conflicts": 0,
        "hardware_conflicts": 0,
    }

    door_index = {
        _door_key(row): row
        for row in all_doors[door_start_idx:]
        if _door_key(row)
    }
    for witness in direct_doors:
        key = _door_key(witness)
        if not key:
            continue
        if key in door_index:
            target = door_index[key]
            metrics["door_conflicts"] += _record_direct_pdf_conflicts(target, witness)
            filled = _merge_missing_fields(target, witness)
            target["source_method"] = _append_semicolon(target.get("source_method"), "openai_direct_pdf")
            target["verification_flags"] = _append_semicolon(target.get("verification_flags"), "direct_pdf_confirmed")
            target["hybrid_decision"] = _append_semicolon(target.get("hybrid_decision"), "direct_pdf_confirmed")
            metrics["door_confirmed"] += 1
            metrics["door_fields_filled"] += filled
            continue

        if _door_physical_score(witness) >= 2:
            tagged = _tag_direct_door(witness, pdf_name, project_id, "direct_pdf_added")
            all_doors.append(tagged)
            door_index[key] = tagged
            metrics["door_added"] += 1

    hardware_index = {
        _hardware_key(row): row
        for row in all_components[hardware_start_idx:]
        if _hardware_key(row) != ("", "")
    }
    for witness in direct_hardware:
        key = _hardware_key(witness)
        if key == ("", "") or not is_probable_hardware_component(witness):
            continue
        if key in hardware_index:
            target = hardware_index[key]
            metrics["hardware_conflicts"] += _record_direct_pdf_conflicts(target, witness)
            filled = _merge_missing_fields(target, witness)
            target["source_method"] = _append_semicolon(target.get("source_method"), "openai_direct_pdf")
            target["verification_flags"] = _append_semicolon(target.get("verification_flags"), "direct_pdf_confirmed")
            target["hybrid_decision"] = _append_semicolon(target.get("hybrid_decision"), "direct_pdf_confirmed")
            metrics["hardware_confirmed"] += 1
            metrics["hardware_fields_filled"] += filled
            continue

        tagged = _tag_direct_hardware(witness, pdf_name, project_id, "direct_pdf_added")
        all_components.append(tagged)
        hardware_index[key] = tagged
        metrics["hardware_added"] += 1

    return metrics


def _write_direct_pdf_witness(
    output_dir: str,
    pdf_path: Path,
    doors: list[dict],
    hardware: list[dict],
    meta: dict,
    merge_metrics: dict,
) -> None:
    try:
        out_dir = Path(output_dir) / "hybrid_direct_pdf"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_path.stem).strip("._-") or "pdf"
        payload = {
            "pdf_path": str(pdf_path),
            "meta": meta,
            "merge_metrics": merge_metrics,
            "doors": doors,
            "hardware": hardware,
        }
        (out_dir / f"{safe_name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug("Failed to write direct-PDF witness output: %s", e)


def run_pipeline(
    pdf_folder: str = None,
    output_dir: str = None,
    max_pdfs: int = None,
    use_rag: bool = True,
    pdf_files: List[Path] = None,
    hybrid_direct_pdf: Optional[bool] = None,
    hybrid_direct_pdf_mode: Optional[str] = None,
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
    hybrid_mode = _resolve_hybrid_direct_pdf_mode(hybrid_direct_pdf, hybrid_direct_pdf_mode)
    if hybrid_mode != "off":
        logger.info("Hybrid direct-PDF witness enabled: mode=%s", hybrid_mode)

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
        pdf_door_start = len(all_doors)
        pdf_hardware_start = len(all_components)
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

            if doors and _is_likely_quote_or_proposal_pdf(fname):
                logger.info(
                    "Filtered %d door rows from likely proposal/quote PDF %s; preserving hardware rows.",
                    len(doors),
                    fname,
                )
                doors = []

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

        pdf_doors = all_doors[pdf_door_start:]
        pdf_hardware = all_components[pdf_hardware_start:]
        if _should_run_direct_pdf_witness(hybrid_mode, pdf_doors, pdf_hardware):
            direct_started = time.time()
            logger.info("Running direct-PDF OpenAI witness for %s", fname)
            direct_doors, direct_hardware, direct_meta = extract_pdf_direct_openai(pdf_path)
            merge_metrics = _merge_direct_pdf_witness(
                all_doors,
                all_components,
                pdf_door_start,
                pdf_hardware_start,
                direct_doors,
                direct_hardware,
                pdf_name=fname,
                project_id=project_id,
            )
            _write_direct_pdf_witness(
                output_dir,
                pdf_path,
                direct_doors,
                direct_hardware,
                direct_meta,
                merge_metrics,
            )
            logger.info(
                "Direct-PDF witness for %s: raw=%dd/%dhw, added=%dd/%dhw, "
                "confirmed=%dd/%dhw, filled=%d/%d fields, conflicts=%d/%d, elapsed=%.1fs%s",
                fname,
                len(direct_doors),
                len(direct_hardware),
                merge_metrics["door_added"],
                merge_metrics["hardware_added"],
                merge_metrics["door_confirmed"],
                merge_metrics["hardware_confirmed"],
                merge_metrics["door_fields_filled"],
                merge_metrics["hardware_fields_filled"],
                merge_metrics["door_conflicts"],
                merge_metrics["hardware_conflicts"],
                time.time() - direct_started,
                f", error={direct_meta.get('error')}" if direct_meta.get("error") else "",
            )
            if run_logger is not None:
                try:
                    run_logger.event(
                        "direct_pdf_witness",
                        doors=len(direct_doors),
                        hardware=len(direct_hardware),
                        meta=direct_meta,
                        merge_metrics=merge_metrics,
                    )
                except Exception as e:
                    logger.debug("run_logger direct_pdf_witness event failed: %s", e)

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

                matched_by_door = _backfill_orphan_hw_sets_by_door_number(df_doors, df_components, project_id=pid)
                if matched_by_door:
                    logger.info(
                        "Cross-ref: assigned %d orphan doors in %s to hardware sets with matching door numbers.",
                        matched_by_door,
                        pid,
                    )
                
                hw_set_ids = proj_hw["hardware_set_id"].dropna().unique()
                current_orphan_mask = (
                    (df_doors["project_id"] == pid)
                    & (
                        df_doors["hardware_set"].isna()
                        | (df_doors["hardware_set"].astype(str).str.strip() == "")
                    )
                )
                
                # Strategy 1: If the project has exactly 1 hardware set,
                # assign all orphan doors to it.
                if len(hw_set_ids) == 1 and current_orphan_mask.any():
                    mask = current_orphan_mask
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
        dimension_cols = [c for c in ["door_width", "door_height", "frame_width", "frame_height"] if c in df_doors.columns]
        strong_phys_cols = [
            c for c in ["door_thickness", "door_material", "door_finish", "frame_material", "frame_finish", "fire_rating"]
            if c in df_doors.columns
        ]
        existing = dimension_cols + strong_phys_cols
        if existing:
            before_ghosts = len(df_doors)
            has_dimensions = (
                df_doors[dimension_cols].notna().any(axis=1)
                if dimension_cols else pd.Series(False, index=df_doors.index)
            )
            has_strong_physical = (
                df_doors[strong_phys_cols].notna().any(axis=1)
                if strong_phys_cols else pd.Series(False, index=df_doors.index)
            )
            valid_mask = has_dimensions | has_strong_physical | (df_doors["door_number"].astype(str).str.strip() == "")
            if "source_file" in df_doors.columns:
                source_upper = df_doors["source_file"].fillna("").astype(str).str.upper()
                hardware_only_source = source_upper.str.contains("HARDWARE") & ~source_upper.str.contains("DOOR")
                valid_mask &= ~(hardware_only_source & ~has_dimensions)
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
        "source_location", "verification_flags", "hybrid_decision", "hybrid_conflicts", "evidence_expected_door_rows",
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
        "source_location", "verification_flags", "hybrid_decision", "hybrid_conflicts", "evidence_expected_hw_sets", "hardware_set_id",
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
