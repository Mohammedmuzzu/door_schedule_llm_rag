"""
High-resolution schedule crop detection for vision rescue.

The normal pipeline sends a full-page image to GPT-4o, but large architectural
sheets downscale tiny schedules into unreadable blur. This module finds likely
schedule regions and renders only those regions at higher DPI.
"""

from __future__ import annotations

import base64
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger("vision_crops")

# Search phrases for PyMuPDF — keep specific multi-word anchors first.
SCHEDULE_KEYWORDS = (
    "DOOR SCHEDULE", "DOOR NO", "DOOR NUMBER", "DOOR MARK", "FRAME TYPE",
    "FIRE RATING", "HARDWARE SET", "HARDWARE SCHEDULE", "HDWR SET", "HW SET",
    "OPENING SCHEDULE", "DOOR AND FRAME", "DOOR AND HARDWARE",
)

# Keyword → crop_type for rescue routing (door / hardware / mixed).
_HW_ANCHORS = frozenset(
    {"HARDWARE SET", "HARDWARE SCHEDULE", "HDWR SET", "HW SET"},
)
_MIXED_HINTS = frozenset({"DOOR AND HARDWARE"})


@dataclass
class CropCandidate:
    crop_type: str
    confidence: float
    source: str
    bbox: Tuple[float, float, float, float]
    page_size: Tuple[float, float]
    base64_image: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_schedule_crops(
    pdf_path: Path,
    page_idx: int,
    page_text: str = "",
    page_type: str = "",
    *,
    max_candidates: int = 5,
    dpi: int = 240,
) -> List[dict]:
    """
    Return high-resolution schedule crop candidates for a page.

    Detection is intentionally layered:
    1. text anchors from the PDF text layer;
    2. visual grid/table contours when OpenCV is installed;
    3. fixed layout tiles as a last resort for visual-only sheets.
    """
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        if page_idx >= len(doc):
            doc.close()
            return []
        page = doc[page_idx]
        page_rect = page.rect
        page_size = (float(page_rect.width), float(page_rect.height))

        rects: list[tuple] = []
        rects.extend(_text_anchor_rects(page, page_rect))
        rects.extend(_visual_table_rects(page, page_rect))
        if _needs_tiles(page_text, page_type, rects):
            rects.extend(_tile_rects(page_rect))

        merged = _dedupe_rects(rects, page_rect)
        page_default_type = _infer_crop_type(page_text, page_type)
        candidates: List[CropCandidate] = []
        for entry in merged[:max_candidates]:
            source, score, bbox = entry[0], entry[1], entry[2]
            anchor_type = entry[3] if len(entry) > 3 else None
            crop_kind = anchor_type or page_default_type
            rect = fitz.Rect(*bbox)
            try:
                pix = page.get_pixmap(dpi=dpi, clip=rect, alpha=False)
                img_bytes = pix.tobytes("jpeg", jpg_quality=88)
            except TypeError:
                pix = page.get_pixmap(dpi=dpi, clip=rect, alpha=False)
                img_bytes = pix.tobytes("jpeg")

            candidates.append(
                CropCandidate(
                    crop_type=crop_kind,
                    confidence=round(float(score), 3),
                    source=source,
                    bbox=tuple(round(float(v), 2) for v in bbox),
                    page_size=page_size,
                    base64_image=base64.b64encode(img_bytes).decode("utf-8"),
                )
            )

        doc.close()
        if candidates:
            logger.info(
                "Page %d: detected %d schedule crop candidates (%s).",
                page_idx + 1,
                len(candidates),
                ", ".join(f"{c.source}:{c.confidence}" for c in candidates),
            )
        return [candidate.to_dict() for candidate in candidates]
    except Exception as exc:
        logger.debug("Schedule crop detection failed on %s page %d: %s", pdf_path, page_idx + 1, exc)
        return []


def crop_summary(crops: Iterable[dict]) -> list[dict]:
    """Return a log-safe summary without large base64 payloads."""
    out = []
    for crop in crops or []:
        out.append({
            "type": crop.get("crop_type"),
            "confidence": crop.get("confidence"),
            "source": crop.get("source"),
            "bbox": crop.get("bbox"),
            "page_size": crop.get("page_size"),
        })
    return out


def _keyword_crop_type(keyword: str) -> str:
    k = keyword.upper().strip()
    if k in _MIXED_HINTS:
        return "mixed"
    if k in _HW_ANCHORS or "HARDWARE" in k:
        return "hardware"
    return "door"


def _infer_crop_type(page_text: str, page_type: str) -> str:
    upper = f"{page_type}\n{page_text}".upper()
    has_door = any(
        token in upper
        for token in (
            "DOOR SCHEDULE", "DOOR NO", "DOOR NUMBER", "DOOR MARK",
            "FRAME TYPE", "OPENING SCHEDULE", "DOOR AND FRAME", "DOOR AND HARDWARE",
        )
    )
    has_hw = any(
        token in upper
        for token in ("HARDWARE SET", "HARDWARE SCHEDULE", "HDWR", "HW SET", "GROUP NO", "SET NO")
    )
    if has_door and has_hw:
        return "mixed"
    if has_hw:
        return "hardware"
    if has_door:
        return "door"
    return "mixed"


def _expand_rect(rect, page_rect, x_pad: float = 0.08, y_pad: float = 0.10):
    width = rect.width
    height = rect.height
    expanded = rect + (
        -max(24, width * x_pad),
        -max(24, height * y_pad),
        max(120, width * 2.5),
        max(180, height * 10.0),
    )
    return expanded & page_rect


def _text_anchor_rects(page, page_rect) -> list[tuple]:
    rects = []
    for keyword in SCHEDULE_KEYWORDS:
        try:
            for found in page.search_for(keyword):
                expanded = _expand_rect(found, page_rect)
                area_ratio = expanded.get_area() / max(page_rect.get_area(), 1)
                if area_ratio < 0.70:
                    score = 0.95 if "SCHEDULE" in keyword else 0.82
                    ctype = _keyword_crop_type(keyword)
                    rects.append((f"text:{keyword}", score, tuple(expanded), ctype))
        except Exception:
            continue
    return rects


def _visual_table_rects(page, page_rect) -> list[tuple]:
    try:
        import cv2
        import numpy as np
    except Exception:
        return []

    try:
        pix = page.get_pixmap(dpi=120, alpha=False)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)[1]

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(18, pix.width // 60), 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(18, pix.height // 60)))
        lines = cv2.add(cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel), cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel))
        contours, _ = cv2.findContours(lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rects = []
        scale_x = page_rect.width / max(pix.width, 1)
        scale_y = page_rect.height / max(pix.height, 1)
        page_area_px = pix.width * pix.height
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < pix.width * 0.12 or h < pix.height * 0.05:
                continue
            area_ratio = (w * h) / max(page_area_px, 1)
            if not (0.01 <= area_ratio <= 0.55):
                continue
            # Schedule tables are usually wider than tall, but hardware lists can be vertical.
            density = cv2.countNonZero(lines[y:y + h, x:x + w]) / max(w * h, 1)
            score = min(0.88, 0.48 + density * 18 + min(area_ratio, 0.12))
            pdf_rect = (
                x * scale_x,
                y * scale_y,
                (x + w) * scale_x,
                (y + h) * scale_y,
            )
            rects.append(("visual_grid", score, pdf_rect, None))
        return rects
    except Exception as exc:
        logger.debug("Visual table detection failed: %s", exc)
        return []


def _needs_tiles(page_text: str, page_type: str, rects: list) -> bool:
    if len(rects) >= 2:
        return False
    upper = f"{page_type}\n{page_text}".upper()
    if any(keyword in upper for keyword in ("DOOR SCHEDULE", "HARDWARE SET", "HARDWARE SCHEDULE")):
        return True
    if len(re.findall(r"\b\d{2,4}[A-Za-z]?\b", page_text or "")) >= 5:
        return True
    return not rects


def _tile_rects(page_rect) -> list[tuple]:
    w = page_rect.width
    h = page_rect.height
    tiles = [
        ("tile_top_left", 0.38, (0, 0, w * 0.55, h * 0.45)),
        ("tile_top_right", 0.36, (w * 0.45, 0, w, h * 0.45)),
        ("tile_bottom_left", 0.32, (0, h * 0.45, w * 0.55, h)),
        ("tile_bottom_right", 0.30, (w * 0.45, h * 0.45, w, h)),
        ("tile_left_band", 0.28, (0, 0, w * 0.62, h)),
        ("tile_center", 0.26, (w * 0.20, h * 0.20, w * 0.80, h * 0.80)),
    ]
    return [(name, score, bbox, None) for name, score, bbox in tiles]


def _merge_crop_types(a: Optional[str], b: Optional[str]) -> Optional[str]:
    types = {x for x in (a, b) if x}
    if not types:
        return None
    if types == {"door"}:
        return "door"
    if types == {"hardware"}:
        return "hardware"
    return "mixed"


def _dedupe_rects(rects, page_rect) -> list[tuple]:
    cleaned: list[tuple] = []
    for item in rects:
        source = item[0]
        score = item[1]
        bbox = item[2]
        ctype = item[3] if len(item) > 3 else None
        x0, y0, x1, y1 = bbox
        x0 = max(0.0, min(float(x0), page_rect.width))
        y0 = max(0.0, min(float(y0), page_rect.height))
        x1 = max(0.0, min(float(x1), page_rect.width))
        y1 = max(0.0, min(float(y1), page_rect.height))
        if x1 <= x0 or y1 <= y0:
            continue
        area = (x1 - x0) * (y1 - y0)
        if area < page_rect.get_area() * 0.005:
            continue
        candidate_bbox = (x0, y0, x1, y1)
        merged = False
        for i, ex in enumerate(cleaned):
            ex_source, ex_score, ex_bbox, ex_ctype = ex[0], ex[1], ex[2], ex[3] if len(ex) > 3 else None
            if _iou(candidate_bbox, ex_bbox) > 0.75:
                new_score = max(float(score), float(ex_score))
                new_type = _merge_crop_types(ctype, ex_ctype)
                cleaned[i] = (f"{ex_source}+{source}", new_score, ex_bbox, new_type)
                merged = True
                break
        if not merged:
            cleaned.append((source, score, candidate_bbox, ctype))

    cleaned.sort(key=lambda item: item[1], reverse=True)
    return cleaned


def _iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return inter / max(area_a + area_b - inter, 1.0)
