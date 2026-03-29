"""
Multi-backend page extraction from PDFs.

Architecture:
  Backend 1: PyMuPDF4LLM — layout-aware markdown extraction (tables, text, headers)
  Backend 2: pdfplumber  — structured table extraction with multiple strategies
  Backend 3: img2table   — image-based table detection (handles drawings, scanned PDFs)
  
The best output from all backends is merged and scored to give the LLM
maximum context with minimum noise.
"""
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# Late import or safe import since no circular dependency exists
from llm_extract import _llm_chat

logger = logging.getLogger("page_extractor")


# ─── Optional Backend Imports ────────────────────────────────────
_PDFPLUMBER_OK = False
try:
    import pdfplumber
    _PDFPLUMBER_OK = True
except ImportError:
    logger.info("pdfplumber not available")

_PYMUPDF4LLM_OK = False
try:
    import pymupdf.layout  # must be imported BEFORE pymupdf4llm
    import pymupdf4llm
    import pymupdf
    _PYMUPDF4LLM_OK = True
except ImportError:
    try:
        import pymupdf4llm
        import pymupdf
        _PYMUPDF4LLM_OK = True
    except ImportError:
        logger.info("pymupdf4llm not available")

_IMG2TABLE_OK = False
_img_ocr = None
try:
    from img2table.document import PDF as Img2TablePDF
    _IMG2TABLE_OK = True
    try:
        from img2table.ocr import PaddleOCR
        _img_ocr = PaddleOCR(lang="en")
    except Exception as e:
        logger.warning("OCR disabled because PaddleOCR failed to initialize: %s", e)
except ImportError:
    logger.info("img2table not available")

# ─── Page Type Classification ────────────────────────────────────
class PageType:
    DOOR_SCHEDULE = "door_schedule"
    HARDWARE_SET = "hardware_set"
    MIXED = "mixed"
    OTHER = "other"


_DOOR_KW = {
    "DOOR SCHEDULE", "DOOR AND HARDWARE SCHEDULE", "DOOR AND WINDOW SCHEDULE",
    "OPENING SCHEDULE", "DOOR SCHED", "DOOR NO.", "DOOR NUMBER", "DOOR MARK",
    "DOOR AND FRAME SCHEDULE", "DOOR & FRAME SCHEDULE"
}
_HW_KW = {
    "HARDWARE GROUP", "HARDWARE SET NO", "DIVISION 8", "HARDWARE SET #",
    "GROUP NO", "HDWR GRP", "SET NO.", "HARDWARE SCHEDULE",
}
_DOOR_TABLE_HEADERS = re.compile(
    r"(?:door\s*(?:number|no|mark|tag|#)|"
    r"frame\s*type|frame\s*material|fire\s*rat|room\s*name|opening\s*no)",
    re.IGNORECASE,
)
_HW_SET_HEADER = re.compile(
    r"(?:hardware\s*(?:set|group)\s*(?:no\.?|#|number|–|-|[A-Z])?|"
    r"group\s*(?:no\.?|#)?\s*[\d]+|"
    r"set\s*(?:no\.?|#)?\s*[\d]+\s*[-–—]\s*)",
    re.IGNORECASE,
)


def classify_page(text: str) -> str:
    """Classify a page as door_schedule, hardware_set, mixed, or other."""
    upper = text.upper()
    has_door = any(kw in upper for kw in _DOOR_KW) or bool(_DOOR_TABLE_HEADERS.search(text))
    has_hw = any(kw in upper for kw in _HW_KW) or bool(_HW_SET_HEADER.search(text))

    # Door number patterns (101, 101A, D2) inside tables (heuristic: a lot of them)
    door_nums = re.findall(r"\b(?:10[0-9]|1[1-9][0-9]|[2-9][0-9]{2})[A-Za-z]?\b", text)
    if len(door_nums) >= 5:
        has_door = True

    # Hardware quantity patterns (2 EA, 1 PAIR)
    hw_qty = re.findall(r"\b\d+\s*(?:EA|PAIR|SET|EACH)\b", upper)
    if len(hw_qty) >= 2:
        has_hw = True
        
    # If the page specifically explicitly says "HARDWARE SCHEDULE" only
    if "HARDWARE SCHEDULE" in upper and not any(kw in upper for kw in _DOOR_KW):
        has_door = False
        has_hw = True

    if has_door and has_hw:
        return PageType.MIXED
    elif has_door:
        return PageType.DOOR_SCHEDULE
    elif has_hw:
        return PageType.HARDWARE_SET
        
    # Phase 4 Upgrade: Dynamic LLM Fallback for classification if text is decent length
    if len(text) > 200:
        system_prompt = "You are a document classifier. Is the following text from a 'door_schedule', 'hardware_set', 'mixed', or 'other' document? Reply with ONLY ONE of those four words."
        try:
            llm_class = _llm_chat(system_prompt, text[:2000], force_json=False).strip().lower()
            if "mixed" in llm_class: return PageType.MIXED
            if "door" in llm_class: return PageType.DOOR_SCHEDULE
            if "hardware" in llm_class: return PageType.HARDWARE_SET
        except Exception as e:
            logger.debug("LLM dynamic classification failed: %s", e)
            
    return PageType.OTHER


# ═══════════════════════════════════════════════════════════════════
#  BACKEND 1: PyMuPDF4LLM  (layout-aware markdown)
# ═══════════════════════════════════════════════════════════════════
def _extract_pymupdf4llm(pdf_path: Path, page_idx: int) -> str:
    """
    Extract page using PyMuPDF4LLM with layout analysis.
    Returns markdown with tables detected by the neural-net layout model.
    Uses a 30s timeout because the GNN layout model can hang on complex drawings.
    """
    if not _PYMUPDF4LLM_OK:
        return ""
    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        def _do_extract():
            return pymupdf4llm.to_markdown(
                str(pdf_path),
                pages=[page_idx],
                show_progress=False,
                use_ocr=False,
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_extract)
            try:
                md = future.result(timeout=30)  # 30 second hard limit
            except FuturesTimeout:
                logger.warning("pymupdf4llm timed out after 30s on page %d — skipping", page_idx + 1)
                return ""

        if not md:
            return ""
        # Clean up HTML/markdown artifacts
        md = md.replace("<br>", "\n")
        md = re.sub(r"\*\*==>\s*picture\s*\[.*?\]\s*intentionally omitted\s*<==\*\*", "", md)
        md = re.sub(r"\*\*----- (?:Start|End) of picture text -----\*\*", "", md)
        md = md.replace("**", "")  # Remove bold markers
        # Collapse multiple blank lines
        md = re.sub(r"\n{3,}", "\n\n", md)
        return md.strip()
    except Exception as e:
        logger.debug("pymupdf4llm failed p%d: %s", page_idx, e)
        return ""


# ═══════════════════════════════════════════════════════════════════
#  BACKEND 2: pdfplumber (structured table extraction)
# ═══════════════════════════════════════════════════════════════════
def _table_to_markdown(table: list, max_cell_len: int = 80) -> str:
    """Convert a 2D table list to markdown."""
    if not table or not table[0]:
        return ""
    rows = []
    for row in table:
        cells = [str(c or "").strip().replace("\n", " ")[:max_cell_len] for c in row]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _clean_table(table: list) -> list:
    """Remove empty rows and columns."""
    if not table:
        return []
    cleaned = [row for row in table if any(str(c or "").strip() for c in row)]
    if not cleaned:
        return []
    n_cols = max(len(r) for r in cleaned)
    non_empty_cols = set()
    for row in cleaned:
        for i, cell in enumerate(row):
            if str(cell or "").strip():
                non_empty_cols.add(i)
    if not non_empty_cols:
        return []
    return [[row[i] if i < len(row) else "" for i in sorted(non_empty_cols)] for row in cleaned]


def _merge_split_rows(table: list) -> list:
    """Merge continuation rows (mostly empty) with the previous row."""
    if len(table) < 2:
        return table
    merged = [list(table[0])]
    for row in table[1:]:
        non_empty = sum(1 for c in row if str(c or "").strip())
        if non_empty <= 1 and len(row) > 2 and merged:
            prev = merged[-1]
            for i, cell in enumerate(row):
                t = str(cell or "").strip()
                if t and i < len(prev):
                    pt = str(prev[i] or "").strip()
                    prev[i] = (pt + " " + t).strip() if pt else t
        else:
            merged.append(list(row))
    return merged


def _is_quality_table(table: list) -> bool:
    """Filter out drawing grids and garbled tables."""
    if not table or len(table) < 2:
        return False
    n_cols = max(len(r) for r in table)
    if n_cols > 20:
        return False
    total = sum(len(r) for r in table)
    filled = sum(1 for r in table for c in r if str(c or "").strip())
    if total > 0 and filled / total < 0.15:
        return False
    if filled > 0:
        avg_len = sum(len(str(c or "").strip()) for r in table for c in r if str(c or "").strip()) / filled
        if avg_len < 1.5:
            return False
    # Check for CID garbled text
    total_chars = sum(len(str(c or "").strip()) for r in table for c in r)
    cid_count = sum(len(re.findall(r"\(cid:\d+\)", str(c or ""))) for r in table for c in r)
    if total_chars > 0 and (cid_count * 5) / total_chars > 0.3:
        return False
    return True


def _extract_pdfplumber(pdf_path: Path, page_idx: int) -> Tuple[str, str]:
    """
    Extract via pdfplumber with multiple strategies.
    Returns (tables_markdown, plain_text).
    """
    if not _PDFPLUMBER_OK:
        return "", ""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_idx >= len(pdf.pages):
                return "", ""
            page = pdf.pages[page_idx]
            plain_text = (page.extract_text() or "").strip()

            strategies = [
                {},
                {"vertical_strategy": "text", "horizontal_strategy": "text", "snap_tolerance": 5},
                {"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 8, "join_tolerance": 5},
            ]

            best_parts = []
            best_score = 0

            for settings in strategies:
                try:
                    tables = page.extract_tables(settings) if settings else page.extract_tables()
                    if not tables:
                        continue
                    score = 0
                    parts = []
                    for t in tables:
                        ct = _clean_table(t)
                        if ct and len(ct) >= 2:
                            ct = _merge_split_rows(ct)
                            if not _is_quality_table(ct):
                                continue
                            n_r, n_c = len(ct), max(len(r) for r in ct)
                            md = _table_to_markdown(ct)
                            if md:
                                parts.append(f"=== TABLE ({n_r}×{n_c}) ===\n{md}")
                                score += sum(1 for r in ct for c in r if str(c or "").strip())
                    if score > best_score:
                        best_score = score
                        best_parts = parts
                except Exception:
                    pass

            tables_md = "\n\n".join(best_parts)
            return tables_md, plain_text

    except Exception as e:
        logger.debug("pdfplumber failed p%d: %s", page_idx, e)
        return "", ""


# ═══════════════════════════════════════════════════════════════════
#  BACKEND 3: img2table (image-based table detection)
# ═══════════════════════════════════════════════════════════════════
def _extract_img2table(pdf_path: Path, page_idx: int, use_ocr: bool = False) -> str:
    """
    Image-based table extraction using OpenCV.
    
    Args:
        use_ocr: If True, use PaddleOCR to read text from images.
                 If False, only detect table structure (no text reading).
                 OCR should only be used when native text extraction failed,
                 indicating a flattened/scanned PDF.
    """
    if not _IMG2TABLE_OK:
        return ""
    try:
        pdf_doc = Img2TablePDF(str(pdf_path), pages=[page_idx])
        
        ocr_engine = _img_ocr if use_ocr else None
        tables = pdf_doc.extract_tables(
            ocr=ocr_engine,
            implicit_rows=True,
            borderless_tables=True,
        )

        if not tables or page_idx not in tables:
            return ""

        page_tables = tables[page_idx]
        if not page_tables:
            return ""

        parts = []
        for t_idx, extracted_table in enumerate(page_tables):
            try:
                # img2table returns ExtractedTable objects
                df = extracted_table.df
                if df is not None and not df.empty and len(df) >= 2:
                    n_r, n_c = df.shape
                    if 1 < n_c <= 20:  # Quality filter: MUST be > 1 column
                        md = df.to_markdown(index=False)
                        parts.append(f"=== IMG2TABLE ({n_r}x{n_c}) ===\n{md}")
            except Exception:
                pass

        return "\n\n".join(parts)
    except Exception as e:
        logger.debug("img2table failed p%d: %s", page_idx, e)
        return ""


# ═══════════════════════════════════════════════════════════════════
#  MULTI-BACKEND MERGER & SCORING
# ═══════════════════════════════════════════════════════════════════
def _score_content(text: str) -> float:
    """
    Score extracted content quality for door/hardware extraction.
    Higher = more relevant structured data.
    """
    if not text:
        return 0.0
    score = 0.0

    # Door number patterns
    score += len(re.findall(r"\b\d{3,4}[A-Za-z]?\b", text)) * 3.0

    # Dimension patterns (3'-0", 7'-0")
    score += len(re.findall(r"\d+'-\d+\"", text)) * 2.0

    # Hardware keywords
    score += len(re.findall(r"\b(?:HINGE|CLOSER|LOCK|STOP|THRESHOLD|SEAL)\b", text, re.IGNORECASE)) * 5.0

    # Table markers
    score += text.count("===") * 1.0

    # Markdown table pipes (structured data)
    score += text.count("|") * 0.1

    # Penalty for CID font garbage
    cid_count = len(re.findall(r"\(cid:\d+\)", text))
    score -= cid_count * 10.0

    # Penalty for garbled text (reversed text, too many special chars)
    garbled = len(re.findall(r"[^\x20-\x7E\n\r\t]", text))
    score -= garbled * 0.5

    # Penalty for very short content
    if len(text) < 100:
        score *= 0.5

    return max(0.0, score)


# ═══════════════════════════════════════════════════════════════════
#  TEXT PRE-PROCESSING: Fix reversed/mirrored headers from CAD PDFs
# ═══════════════════════════════════════════════════════════════════
# Architectural CAD software often renders vertical text that gets extracted
# as reversed words (e.g. "EPYT ROOD" instead of "DOOR TYPE").
# This map fixes the most common reversed patterns so smaller LLMs can parse them.
_REVERSED_FIXES = {
    "EPYT ROOD": "DOOR TYPE",
    "TES ERAWDRAH": "HARDWARE SET",
    "ERAWDRAH": "HARDWARE",
    "SSENKCIHT ROOD": "DOOR THICKNESS",
    "SSENKCIHT": "THICKNESS",
    "WOLLOH LATEM": "HOLLOW METAL",
    "MUNIMULA": "ALUMINUM",
    "SSALG": "GLASS",
    "LATEM": "METAL",
    "STNEMMOC": "COMMENTS",
    "SELUDEHCS": "SCHEDULES",
    "TNORFEROTS": "STOREFRONT",
    "SEPYT ROOD": "DOOR TYPES",
    "SEPYT": "TYPES",
    "ECNEREFER": "REFERENCE",
    "ELUDEHCS": "SCHEDULE",
    "ROTCAF-U": "U-FACTOR",
    "CGHS": "SHGC",
    "ETIL ROODTUO": "OUTDOOR LITE",
    "ETIL ROODNI": "INDOOR LITE",
    "ECAPS RIA": "AIR SPACE",
    "ROIRETXE": "EXTERIOR",
    "ROIRETNI": "INTERIOR",
    "ECAFRUS": "SURFACE",
    "KCALB": "BLACK",
    "NOITATNEIRO": "ORIENTATION",
    "REENWAK": "WAKEENER",
    "RETNEC": "CENTER",
    "DEZALG": "GLAZED",
    "LEDOM": "MODEL",
    "noitpircseD": "Description",
    "etaD": "Date",
    "TNEILC": "CLIENT",
    "SETADPU": "UPDATES",
    "XENOCA": "ACONEX",
}


def _fix_reversed_text(text: str) -> str:
    """Fix reversed/mirrored text from CAD PDF rendering."""
    for reversed_str, correct_str in _REVERSED_FIXES.items():
        text = text.replace(reversed_str, correct_str)
    return text


def _merge_backends(
    pymupdf_md: str,
    plumber_tables: str,
    plumber_text: str,
    img2table_md: str,
    max_chars: int = 14000,
) -> str:
    """
    Merge outputs from all backends into a single context string.
    Strategy: Use the highest-quality structured content, supplement with text.
    """
    # Score each backend
    scores = {
        "pymupdf4llm": _score_content(pymupdf_md),
        "pdfplumber_tables": _score_content(plumber_tables),
        "pdfplumber_text": _score_content(plumber_text),
        "img2table": _score_content(img2table_md) * 0.5,  # Base penalty for optical hallucinations
    }

    # If native vector extraction found high-quality tables, discard img2table entirely to avoid noise
    if max(scores["pymupdf4llm"], scores["pdfplumber_tables"]) > 30:
        scores["img2table"] = 0.0

    logger.debug("Backend scores: %s", {k: f"{v:.1f}" for k, v in scores.items()})

    parts = []
    budget = max_chars

    # Priority 1: Best structured tables
    table_sources = [
        ("pymupdf4llm", pymupdf_md),
        ("pdfplumber_tables", plumber_tables),
        ("img2table", img2table_md),
    ]
    # Sort by score descending
    table_sources.sort(key=lambda x: scores.get(x[0], 0), reverse=True)

    for name, content in table_sources:
        if content and len(content) > 50 and budget > 0:
            chunk = content[:budget]
            parts.append(f"[Source: {name}]\n{chunk}")
            budget -= len(chunk) + 50
            # If best source has very good score, don't add duplicates
            if scores.get(name, 0) > 50:
                break

    # Priority 2: Include plain text if we have budget and it adds value
    if plumber_text and budget > 500:
        # Only add plain text if it has content not already in tables
        text_score = scores.get("pdfplumber_text", 0)
        if text_score > 10 or not parts:
            chunk = plumber_text[:budget]
            parts.append(f"[Source: plain_text]\n{chunk}")
            budget -= len(chunk)

    return "\n\n".join(parts).strip()[:max_chars]


# ═══════════════════════════════════════════════════════════════════
#  CONTINUITY DETECTION
# ═══════════════════════════════════════════════════════════════════
def detect_continuation(text: str, prev_page_type: Optional[str] = None) -> bool:
    """Detect if page is a continuation of a multi-page table."""
    upper = text.upper().strip()
    if any(m in upper[:200] for m in ("(CONTINUED)", "(CONT'D)", "(CONT)", "CONTINUED FROM")):
        return True
    if prev_page_type:
        lines = [l.strip() for l in text.split("\n") if l.strip()][:5]
        if lines:
            first = lines[0]
            if re.match(r"^\d{2,4}[A-Za-z]?\s", first):
                return True
            if re.match(r"^\d+\s+(EA|PAIR|SET)\s", first, re.IGNORECASE):
                return True
    return False


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def extract_structured_page(
    pdf_path: Path,
    page_idx: int,
    max_chars: int = 14000,
    prev_page_type: Optional[str] = None,
) -> Tuple[str, str, bool]:
    """
    Extract page content using ALL available backends, merge best results.

    Strategy:
      1. Try native text extraction first (PyMuPDF4LLM + pdfplumber)
      2. If native extraction returns meaningful text → PDF is machine-generated,
         skip OCR entirely (fast path)
      3. If native extraction fails → PDF is likely flattened/scanned,
         fall back to img2table + PaddleOCR (slow path)

    Returns:
        (content_text, page_type, is_continuation)
    """
    pdf_path = Path(pdf_path)
    backends_used = []

    # ── Step 1: Try native text extraction (fast, no OCR) ──
    pymupdf_md = _extract_pymupdf4llm(pdf_path, page_idx)
    if pymupdf_md:
        backends_used.append("pymupdf4llm")

    plumber_tables, plumber_text = _extract_pdfplumber(pdf_path, page_idx)
    if plumber_tables:
        backends_used.append("pdfplumber_tables")
    if plumber_text:
        backends_used.append("pdfplumber_text")

    # ── Step 2: Decide if we need OCR/Image Table Parsing ──
    native_text_len = len(pymupdf_md or "") + len(plumber_text or "") + len(plumber_tables or "")
    is_machine_generated = native_text_len > 100  # Meaningful text found

    img2table_md = ""
    if is_machine_generated:
        # PDF is natively machine-generated. 
        # Bypass img2table entirely to prevent visual table detectors from ruining the text formatting.
        logger.info("Page %d: Machine-generated PDF detected (%d chars). Relying purely on vector extraction.",
                    page_idx + 1, native_text_len)
    else:
        # PDF appears flattened/scanned → run img2table WITH OCR
        logger.info("Page %d: No native text found. Using optical img2table fallback.",
                    page_idx + 1)
        img2table_md = _extract_img2table(pdf_path, page_idx, use_ocr=True)

    if img2table_md:
        backends_used.append("img2table")

    if not backends_used:
        return "", PageType.OTHER, False

    logger.info("Page %d backends: %s", page_idx + 1, ", ".join(backends_used))

    # ── Step 3: Merge all backends ──
    content = _merge_backends(
        pymupdf_md, plumber_tables, plumber_text, img2table_md,
        max_chars=max_chars,
    )

    if not content or len(content.strip()) < 30:
        # Last resort: use any text available
        content = plumber_text[:max_chars] if plumber_text else pymupdf_md[:max_chars]

    if not content or len(content.strip()) < 30:
        return "", PageType.OTHER, False

    # ── Step 4: Fix reversed text from CAD PDFs ──
    content = _fix_reversed_text(content)

    # Classify page
    page_type = classify_page(content)
    is_continuation = detect_continuation(content, prev_page_type)

    return content, page_type, is_continuation


def get_page_count(pdf_path: Path) -> int:
    """Get total page count for a PDF."""
    if _PYMUPDF4LLM_OK:
        try:
            doc = pymupdf.open(str(pdf_path))
            count = len(doc)
            doc.close()
            return count
        except Exception:
            pass
    if _PDFPLUMBER_OK:
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                return len(pdf.pages)
        except Exception:
            pass
    return 0
