"""
mineru_backend.py
─────────────────
Optional MinerU adapter.

MinerU (https://github.com/opendatalab/MinerU, Apache-2.0-equivalent license) is
a document-parsing toolkit that combines layout detection, formula recognition,
table recognition, and OCR. It performs very well on architectural /
engineering PDFs where native text extraction is weak but the pages are still
machine-readable.

This module is written to be **completely optional**:
  * If `mineru` is not installed, `run_mineru_on_page` returns "" silently.
  * If `mineru` is installed but errors during inference, the adapter logs a
    warning and returns "".
  * The rest of the pipeline never needs to know whether MinerU ran.

Installation (only when the user opts in):
    pip install "mineru[pipeline]>=2.0.0"

The adapter uses the lightweight `pipeline` backend (CPU-friendly) rather
than the VLM backend, because we already have a Vision LLM escalation path
inside the agent.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("mineru_backend")


_MINERU_AVAILABLE: Optional[bool] = None


def is_available() -> bool:
    """Check whether MinerU is importable. Result is cached."""
    global _MINERU_AVAILABLE
    if _MINERU_AVAILABLE is not None:
        return _MINERU_AVAILABLE
    if os.getenv("MINERU_DISABLED", "").strip() in ("1", "true", "yes"):
        _MINERU_AVAILABLE = False
        return False
    try:
        # MinerU exposes `pipeline_analyze` and `doc_analyze` from its
        # pipeline backend. We use the high-level `analyze_pdf` helper when
        # available; otherwise fall back to the lower-level API.
        import mineru  # noqa: F401
        _MINERU_AVAILABLE = True
    except Exception as e:
        logger.debug("MinerU not importable (fine, optional): %s", e)
        _MINERU_AVAILABLE = False
    return _MINERU_AVAILABLE


def run_mineru_on_page(pdf_path: Path, page_idx: int, timeout_s: int = 120) -> str:
    """
    Run MinerU's pipeline backend on a single page of a PDF and return a
    markdown string. Returns "" if MinerU is unavailable or fails.

    Strategy: extract the single page to a temp PDF first, then let MinerU
    parse it. This keeps inference scoped and avoids running the full heavy
    model on the entire (often multi-hundred-page) document.
    """
    if not is_available():
        return ""

    try:
        import pymupdf  # already a hard dep of the project
    except Exception as e:
        logger.warning("pymupdf unavailable; MinerU adapter disabled: %s", e)
        return ""

    try:
        with tempfile.TemporaryDirectory() as td:
            single_page_pdf = Path(td) / "page.pdf"
            with pymupdf.open(str(pdf_path)) as src:
                if page_idx >= len(src):
                    return ""
                out = pymupdf.open()
                out.insert_pdf(src, from_page=page_idx, to_page=page_idx)
                out.save(str(single_page_pdf))
                out.close()

            markdown = _call_mineru_pipeline(single_page_pdf, Path(td) / "out", timeout_s)
            return markdown or ""
    except Exception as e:
        logger.warning("MinerU inference failed: %s", e)
        return ""


# ─── Backend calls ─────────────────────────────────────────────────
def _call_mineru_pipeline(single_page_pdf: Path, out_dir: Path, timeout_s: int) -> str:
    """
    Call MinerU's pipeline backend. Prefers the stable CLI-equivalent
    function; falls back to reading the emitted markdown file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # MinerU's internal API has shifted across versions. Probe defensively.
    try:
        from mineru.backend.pipeline.pipeline_analyze import (  # type: ignore
            doc_analyze as pipeline_doc_analyze,
        )
    except Exception:
        pipeline_doc_analyze = None  # type: ignore[assignment]

    try:
        from mineru.cli.common import do_parse  # type: ignore
    except Exception:
        do_parse = None  # type: ignore[assignment]

    if do_parse is not None:
        try:
            do_parse(
                output_dir=str(out_dir),
                pdf_file_names=[single_page_pdf.stem],
                pdf_bytes_list=[single_page_pdf.read_bytes()],
                p_lang_list=["en"],
                backend="pipeline",
                parse_method="auto",
                formula_enable=False,
                table_enable=True,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
            )
        except Exception as e:
            logger.warning("MinerU do_parse failed: %s", e)
            return ""
    elif pipeline_doc_analyze is not None:
        # Older API — skip unless someone wires it up; stays safe.
        logger.info("Older MinerU API detected; skipping for stability.")
        return ""
    else:
        return ""

    # do_parse writes: <out_dir>/<stem>/auto/<stem>.md
    candidates = list(out_dir.rglob("*.md"))
    if not candidates:
        return ""
    md = candidates[0].read_text(encoding="utf-8", errors="replace").strip()
    if not md:
        return ""
    return f"=== MINERU MARKDOWN ===\n{md}"
