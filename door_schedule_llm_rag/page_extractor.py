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
import base64
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
_raw_paddle_ocr = None  # Raw paddleocr engine for direct text extraction
try:
    from img2table.document import PDF as Img2TablePDF
    _IMG2TABLE_OK = True
    try:
        from img2table.ocr import PaddleOCR
        _img_ocr = PaddleOCR(lang="en")
    except Exception as e:
        logger.warning("OCR disabled because PaddleOCR failed to initialize: %s", e)
    try:
        from paddleocr import PaddleOCR as RawPaddleOCR
        _raw_paddle_ocr = RawPaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    except Exception as e:
        logger.warning("Raw PaddleOCR unavailable for direct fallback: %s", e)
except ImportError:
    logger.info("img2table not available")

# ─── Page Type Classification ────────────────────────────────────
class PageType:
    DOOR_SCHEDULE = "door_schedule"
    HARDWARE_SET = "hardware_set"
    MIXED = "mixed"
    OTHER = "other"


# ─── Page Classification (Hybrid LLM Architecture) ───────────────

def classify_page(text: str) -> str:
    """
    Classify a page using a Fast Gatekeeper + LLM Arbiter hybrid logic.
    Returns: door_schedule, hardware_set, mixed, or other.
    """
    upper = text.upper()
    
    # 1. Fast Gatekeeper (Heuristic)
    # If the page has absolutely no architectural schedule terminology, skip it Instantly (0s).
    # This prevents sending 800 pages of plumbing/electrical diagrams to the LLM.
    if not any(kw in upper for kw in ("DOOR", "HARDWARE", "HDWR", "HDWE", "HW", "FRAME", "OPENING", "SCHED")):
        return PageType.OTHER

    # 2. The Smart LLM Arbiter
    # If it passed the gatekeeper, we let the LLM definitively classify the raw text.
    # This completely eliminates Regex false-positives and handles split-headers natively!
    system_prompt = (
        "You are an expert architectural document classifier evaluating raw extracted PDF text. "
        "Analyze the text and determine if it contains a tabular 'Door Schedule', a 'Hardware Schedule' glossary/matrix, 'Both' (Mixed), or 'Neither'. "
        "\n\nCRITICAL CLASSIFICATION RULES:\n"
        "1. DOOR SCHEDULE = A table/matrix listing individual door numbers (e.g. 101, 101A, D2) with columns like Mark, Size, Width, Height, Frame, Rating, Hardware Set No, Remarks. "
        "A Door Schedule that has a column named 'Hardware Set', 'HDWR SET', or 'Hardware Group' is STILL purely 'DOOR' — that column is just a foreign-key reference, NOT actual hardware component data.\n"
        "2. HARDWARE SCHEDULE = A section listing physical hardware COMPONENTS (Hinges, Closers, Locks, Deadbolts, Door Stops) with explicit Qty, Unit (EA/PAIR), Catalog Number, Finish Code, and Manufacturer fields. "
        "Hardware schedules are organized by Set/Group headers (e.g. 'SET 1.0', 'HARDWARE GROUP NO. 103').\n"
        "3. MIXED = The page contains BOTH a Door Schedule table AND a Hardware Component listing on the SAME page. This is rare — only use MIXED if you can identify BOTH door number rows AND component-level hardware rows (with Qty, Description, Catalog) on the same page.\n"
        "4. OTHER = Floor plans, elevation drawings, detail drawings, window schedules only, index pages, cover sheets, or pages that merely mention 'door' in passing text without any actual schedule matrix.\n"
        "5. IMPORTANT: Even if a page is cluttered with elevation drawings, legends, or notes — if there IS a tabular matrix tracking unique door numbers with dimensional data, classify it as 'DOOR' (not OTHER).\n"
        "6. IMPORTANT: Window schedules, finish schedules, and equipment schedules are NOT door schedules. Only classify as DOOR if the table explicitly tracks door marks/numbers.\n"
        "\nYour output must be EXACTLY ONE WORD from this list: [DOOR, HARDWARE, MIXED, OTHER]"
    )
    
    try:
        # Give the LLM a generous chunk so it sees both door AND hardware sections.
        # For mixed pages, the hardware section is often at the bottom, so include the tail too.
        if len(text) > 7000:
            # Head + tail to catch hardware sections at the bottom of the page
            classifier_text = text[:4000] + "\n\n[...content trimmed...]\n\n" + text[-3000:]
        else:
            classifier_text = text[:7000]
        llm_response = _llm_chat(system_prompt, classifier_text, force_json=False).strip().upper()
        
        # Parse the definitive response securely
        if "MIXED" in llm_response or "BOTH" in llm_response:
            return PageType.MIXED
        if "DOOR" in llm_response:
            page_type = PageType.DOOR_SCHEDULE
        elif "HARDWARE" in llm_response or "HDWR" in llm_response:
            page_type = PageType.HARDWARE_SET
        else:
            page_type = PageType.OTHER
        
        # ── Deterministic Upgrade: DOOR → MIXED ──
        # The LLM only sees a truncated text snippet. Check the FULL text for 
        # hardware component signatures that the LLM might have missed.
        # This catches mixed-content PDFs where hardware is in the middle of the document.
        if page_type == PageType.DOOR_SCHEDULE:
            has_hw_components = len(re.findall(r"(?:BUTT HINGE|SURFACE CLOSER|FLOOR STOP|WALL STOP|LOCKSET|DEADBOLT|KICK PLATE|THRESHOLD|DOOR STOP)", upper)) >= 2
            has_hw_sets = len(re.findall(r"(?:SET|GROUP|HW|HDWE|HARDWARE)\s*(?:NO\.?|#)?\s*[\w\d]+", upper)) >= 2
            if has_hw_components or has_hw_sets:
                logger.info("Deterministic upgrade: DOOR → MIXED (found hardware sets or components in full text)")
                page_type = PageType.MIXED
        
        return page_type
        
    except Exception as e:
        logger.error("LLM Arbiter classification failed: %s", e)
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
    if n_cols > 40:
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
            implicit_rows=False,
            borderless_tables=False,
        )

        parts = []
        if tables and page_idx in tables:
            page_tables = tables[page_idx]
            if page_tables:
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
        
        # ── NATIVE OPTICAL TEXT FALLBACK ──
        # If OpenCV failed to find any rigid borders (e.g. sparse hardware sets),
        # extract pure unstructured text directly using raw PaddleOCR bounding boxes
        # sorted by Y-axis (top-to-bottom) then X-axis (left-to-right).
        if not parts and use_ocr and _raw_paddle_ocr is not None:
            logger.info("img2table found 0 structured tables. Deploying pure PaddleOCR text extraction...")
            try:
                import pymupdf
                import numpy as np
                import cv2
                
                doc = pymupdf.open(str(pdf_path))
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                res = _raw_paddle_ocr.ocr(img, cls=True)
                if res and isinstance(res, list) and res[0]:
                    flattened = []
                    for bbox in res[0]:
                        coords = bbox[0]
                        txt, conf = bbox[1]
                        if conf < 0.3:  # Filter low-confidence garbage
                            continue
                        y_center = (coords[0][1] + coords[2][1]) / 2
                        x_center = (coords[0][0] + coords[1][0]) / 2
                        flattened.append((y_center, x_center, txt))
                    
                    if flattened:
                        # Sort by Y (row grouping with 15px tolerance), then X (left-to-right)
                        flattened.sort(key=lambda item: (round(item[0] / 15), item[1]))
                        
                        current_y_group = -1
                        lines = []
                        current_line = []
                        for y, x, txt in flattened:
                            y_group = round(y / 15)
                            if y_group != current_y_group and current_line:
                                lines.append("    ".join(current_line))
                                current_line = []
                                current_y_group = y_group
                            elif current_y_group == -1:
                                current_y_group = y_group
                            current_line.append(txt)
                            
                        if current_line:
                            lines.append("    ".join(current_line))
                            
                        fallback_text = "\n".join(lines)
                        parts.append(f"=== PURE OPTICAL TEXT SEQUENCE ===\n{fallback_text}")
                        logger.info("PaddleOCR fallback produced %d lines, %d chars", len(lines), len(fallback_text))
                        
            except Exception as e:
                logger.error("Optical text sequence fallback failed: %s", e)

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


# ═══════════════════════════════════════════════════════════════════
#  TEXT PRE-PROCESSING: Decode Unicode Private Use Area (PUA) fonts
# ═══════════════════════════════════════════════════════════════════
# Some CAD software (AutoCAD, Revit) maps standard ASCII into the
# Unicode Private Use Area (U+F000-F0FF). This makes the text
# invisible to LLMs — e.g., "DOOR" is stored as \uF044\uF04F\uF04F\uF052.
# The fix is simple: subtract 0xF000 to recover the original ASCII.

def _decode_pua_text(text: str) -> str:
    """Decode Unicode Private Use Area (PUA) encoded text from CAD PDFs.
    
    Detects if >10% of characters fall in the U+F000-F0FF range,
    and if so, maps them back to standard ASCII (U+0000-00FF).
    """
    if not text:
        return text
    
    total = len(text)
    pua_count = sum(1 for ch in text if 0xF000 <= ord(ch) <= 0xF0FF)
    
    # Only apply if >10% of chars are PUA-encoded (avoids false positives)
    if total == 0 or (pua_count / total) < 0.10:
        return text
    
    logger.info("PUA font encoding detected (%d/%d chars). Decoding...", pua_count, total)
    
    result = []
    for ch in text:
        cp = ord(ch)
        if 0xF000 <= cp <= 0xF0FF:
            result.append(chr(cp - 0xF000))
        else:
            result.append(ch)
    return ''.join(result)


def _destutter_text(text: str) -> str:
    """Fix doubled/stuttered text from CAD bold-simulation rendering.
    
    Some CAD tools simulate bold text by printing each character twice
    with a slight offset, resulting in 'MMAARRKK' instead of 'MARK'.
    This detects consecutive character-pair runs and collapses them.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    fixed_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Only attempt destutter on lines that are mostly alphabetic
        # and where the length is even (every char doubled)
        if (len(stripped) >= 4 
            and len(stripped) % 2 == 0
            and sum(1 for c in stripped if c.isalpha()) > len(stripped) * 0.6):
            
            # Check if ALL adjacent character pairs match: AA BB CC ...
            pairs_match = all(
                stripped[i] == stripped[i + 1]
                for i in range(0, len(stripped) - 1, 2)
            )
            
            if pairs_match:
                destuttered = stripped[::2]  # Take every other char
                # Preserve leading whitespace
                leading = len(line) - len(line.lstrip())
                fixed_lines.append(line[:leading] + destuttered)
                continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


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
    Always reserves budget for plain text to ensure hardware sections on mixed pages aren't lost.
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
    # Reserve budget for plain text — critical for mixed pages where hardware 
    # is cleanly readable in plain text but garbled in table extraction.
    plain_text_reserve = min(4000, max_chars // 4) if plumber_text and len(plumber_text) > 200 else 0
    table_budget = max_chars - plain_text_reserve

    # Priority 1: Best structured tables (capped to leave room for plain text)
    table_sources = [
        ("pymupdf4llm", pymupdf_md),
        ("pdfplumber_tables", plumber_tables),
        ("img2table", img2table_md),
    ]
    # Sort by score descending
    table_sources.sort(key=lambda x: scores.get(x[0], 0), reverse=True)

    for name, content in table_sources:
        if content and len(content) > 50 and table_budget > 0:
            chunk = content[:table_budget]
            parts.append(f"[Source: {name}]\n{chunk}")
            table_budget -= len(chunk) + 50

    # Priority 2: ALWAYS include plain text (critical for hardware on mixed pages)
    if plumber_text and len(plumber_text) > 100:
        budget_for_text = max(plain_text_reserve, 500)
        # Hardware sets usually live at the BOTTOM of mixed pages. If we must truncate, secure the tail.
        if len(plumber_text) > budget_for_text:
            chunk = plumber_text[-budget_for_text:]
        else:
            chunk = plumber_text
        parts.append(f"[Source: plain_text]\n{chunk}")

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
) -> Tuple[str, str, bool, Optional[str]]:
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
    base64_img = None

    # ── Step 0: Render Page Image for Vision RAG ──
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")
        base64_img = base64.b64encode(img_bytes).decode("utf-8")
        doc.close()
    except Exception as e:
        logger.warning(f"Failed to render Vision RAG image for page {page_idx+1}: {e}")

    # ── Step 1: Try native text extraction (fast, no OCR) ──
    # First get plain text length to determine complexity
    plumber_tables, plumber_text = _extract_pdfplumber(pdf_path, page_idx)
    raw_text_len = len(plumber_text or "")
    
    pymupdf_md = ""
    # Avoid GNN markdown table rendering on massive dense schedules (A0 size prints).
    # pymupdf4llm's neural engine massively hallucinates staggered columns in complex drawings.
    if raw_text_len < 4000:
        pymupdf_md = _extract_pymupdf4llm(pdf_path, page_idx)
        if pymupdf_md:
            backends_used.append("pymupdf4llm")
            
    if plumber_tables:
        backends_used.append("pdfplumber_tables")
    if plumber_text:
        backends_used.append("pdfplumber_text")

    # ── Step 2: Decide if we need OCR/Image Table Parsing ──
    combined_native = (pymupdf_md or "") + (plumber_text or "") + (plumber_tables or "")
    native_text_len = len(combined_native)
    
    # Heuristic: Detect Optical Illusion Font Encoding Corruption
    def _is_text_gibberish(text: str) -> bool:
        if not text or len(text) < 100:
            return False
        if text.count("cid:") > 20 or text.count("(cid:") > 20:
            return True
        import string
        valid_chars = sum(1 for c in text if c in string.ascii_letters + string.digits)
        density = valid_chars / len(text)
        vowels = sum(1 for c in text.lower() if c in 'aeiou')
        vowel_density = vowels / max(1, valid_chars)
        if density < 0.35 or vowel_density < 0.05:
            return True
        return False

    is_corrupt = _is_text_gibberish(combined_native)
    if is_corrupt:
        logger.warning("Page %d: Optical Illusion Font Corruption detected (Gibberish). Forcing OCR bypass.", page_idx + 1)

    # ── NEW: "Title Block Only" Detection ──
    # Some A0 PDFs have the actual schedule rendered as flattened vector art,
    # but the title block stamp at the edge IS machine-readable (300-1500 chars).
    # The old threshold (100 chars) incorrectly classified these as "machine generated",
    # preventing the OCR fallback from ever running.
    # Fix: If native text is short AND lacks any door-number patterns, it's just a title block.
    def _is_title_block_only(text: str, raw_text: str) -> bool:
        """Detect if the extracted text is just a title block border stamp with no schedule data.
        
        Uses raw_text (plumber_text) as the primary signal because pdfplumber tables
        often extract title block borders as fake tables, inflating char counts.
        """
        # Check raw text content (the actual paragraph text, not table extraction)
        raw_len = len(raw_text or "")
        if raw_len > 2000:
            return False  # Substantial raw text content exists
        
        # Even if combined text is large, if raw text is tiny it's probably just border garbage
        check_text = raw_text if raw_len > 50 else text
        if len(check_text) > 3000:
            return False
            
        # Check for door number patterns (101, 101A, D2, etc.)
        door_nums = re.findall(r'\b\d{3,4}[A-Za-z]?\b', check_text)
        # Filter out years
        real_doors = [n for n in door_nums if not (1900 <= int(re.match(r'\d+', n).group()) <= 2099)]
        if len(real_doors) >= 2:
            return False  # Has door numbers, not just a title block
        # Check for table structure keywords
        table_kw = sum(1 for kw in ("WIDTH", "HEIGHT", "FRAME", "HINGE", "CLOSER", "LOCK", "SCHEDULE") if kw in check_text.upper())
        if table_kw >= 2:
            return False  # Has structural table keywords
        return True  # Looks like just a title block

    is_title_block = _is_title_block_only(combined_native, plumber_text) and not is_corrupt
    if is_title_block:
        logger.info("Page %d: Title-block-only text detected (%d chars, no schedule data). Will try OCR.", page_idx + 1, native_text_len)

    is_machine_generated = native_text_len > 100 and not is_corrupt and not is_title_block

    img2table_md = ""
    if is_machine_generated:
        # PDF is natively machine-generated. 
        # Bypass img2table entirely to prevent visual table detectors from ruining the text formatting.
        logger.info("Page %d: Machine-generated PDF detected (%d chars). Relying purely on vector extraction.",
                    page_idx + 1, native_text_len)
        
        # OPENAI VISION BUG-FIX:
        # OpenAI automatically downscales large images to 768x2000px.
        # On massive A0 architectural prints with 50+ rows (like Project 9), 
        # this downscaling crushes text into 2-pixel blurs.
        # When gpt-4o tries to map the text prompt against a blurred image, it fails and returns []
        # Since we have full machine text, we drop the image entirely to force pure semantic extraction!
        # Note: native_text_len sums 3 separate text backends, so 20,000 roughly equals ~7000 chars of actual density.
        if native_text_len > 20000:
            logger.info("Page %d: Text volume is massively dense (>20000 backend chars). Dropping image payload to prevent Vision blurs.", page_idx + 1)
            base64_img = None
    else:
        # PDF appears flattened/scanned OR title-block-only → run img2table WITH OCR
        logger.info("Page %d: No native text found (or title-block-only). Using optical img2table fallback.",
                    page_idx + 1)
        img2table_md = _extract_img2table(pdf_path, page_idx, use_ocr=True)

    if img2table_md:
        backends_used.append("img2table")

    if not backends_used:
        return "", PageType.OTHER, False, base64_img

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
        return "", PageType.OTHER, False, base64_img

    # ── Step 3b: CID font corruption fallback ──
    # pdfplumber can't decode CID-mapped fonts and produces "(cid:XX)" garbage.
    # When this happens, raw fitz.get_text() usually decodes correctly.
    cid_ratio = content.count("(cid:") / max(len(content), 1)
    if cid_ratio > 0.05:  # >5% of content is CID references
        logger.warning("Page %d: CID-encoded text detected (%.0f%%). Falling back to raw fitz extraction.",
                        page_idx + 1, cid_ratio * 100)
        try:
            doc = pymupdf.open(str(pdf_path))
            fitz_text = doc[page_idx].get_text()
            doc.close()
            if fitz_text and len(fitz_text.strip()) > 30:
                content = fitz_text[:max_chars]
                if "pdfplumber_text" in backends_used and "fitz_fallback" not in backends_used:
                    backends_used.append("fitz_fallback")
                logger.info("Page %d: fitz fallback recovered %d chars of clean text.", page_idx + 1, len(content))
        except Exception as e:
            logger.debug("fitz CID fallback failed: %s", e)

    # ── Step 4: Fix CAD text corruption BEFORE classification ──
    # CRITICAL: These must run BEFORE classify_page() so reversed/PUA text
    # doesn't confuse the LLM classifier into returning OTHER.
    content = _decode_pua_text(content)       # Decrypt PUA-encoded fonts
    content = _destutter_text(content)         # Collapse doubled bold characters
    content = _fix_reversed_text(content)      # Fix mirrored/reversed headers

    # Classify page
    page_type = classify_page(content)

    # ── Deterministic Classification Backstop ──
    # If the LLM classified as OTHER, but the text clearly has door schedule content,
    # force override to MIXED. This catches cases where the text structure confuses
    # the LLM classifier (e.g., malformed pdfplumber table grids).
    if page_type == PageType.OTHER:
        upper = content.upper()
        has_schedule_kw = any(kw in upper for kw in (
            "DOOR SCHEDULE", "DOOR NO", "DOOR NUMBER", "DOOR MARK", 
            "HARDWARE SET", "HW SET", "HDWR SET", "FRAME TYPE",
            "FIRE RATING", "DOOR TYPE",
        ))
        door_nums = re.findall(r'\b\d{3,4}[A-Za-z]?\b', content)
        real_doors = [n for n in door_nums if not (1900 <= int(re.match(r'\d+', n).group()) <= 2099)]
        has_dimensions = bool(re.search(r"\d+['\u2019]\s*-?\s*\d+\"", content))  # 3'-0" pattern
        has_hw_components = any(kw in upper for kw in ("HINGE", "CLOSER", "LOCKSET", "DEADBOLT", "THRESHOLD", "DOOR STOP", "KICK PLATE"))
        
        # Aggressive backstop: multiple signals override the LLM
        if (has_schedule_kw and (len(real_doors) >= 2 or has_dimensions)) or \
           (len(real_doors) >= 5 and has_dimensions) or \
           (len(real_doors) >= 3 and has_hw_components):
            logger.warning("Page %d: LLM misclassified as OTHER but text has %d door-like numbers, dimensions=%s, hw=%s. Forcing MIXED.", 
                          page_idx + 1, len(real_doors), has_dimensions, has_hw_components)
            page_type = PageType.MIXED

    is_continuation = detect_continuation(content, prev_page_type)

    return content, page_type, is_continuation, base64_img


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
