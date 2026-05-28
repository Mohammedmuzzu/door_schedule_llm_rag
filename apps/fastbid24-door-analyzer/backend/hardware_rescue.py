import base64
import io
import re
from typing import Any


SCHEDULE_KEYWORDS = (
    "DOOR HARDWARE",
    "HARDWARE SET",
    "HARDWARE SCHEDULE",
    "HDWR SET",
    "HW SET",
    "DOOR AND HARDWARE",
)

HARDWARE_ANCHORS = frozenset({"DOOR HARDWARE", "HARDWARE SET", "HARDWARE SCHEDULE", "HDWR SET", "HW SET"})


def detect_hardware_crops(file_bytes: bytes, *, max_candidates: int = 8, dpi: int = 260) -> list[dict[str, Any]]:
    """
    Render high-resolution crops around hardware schedules.

    The staged full-PDF pass can miss tiny dense hardware tables after the PDF is
    downscaled by the model. This mirrors the legacy crop-rescue behavior while
    keeping the user-facing pipeline simple.
    """
    try:
        import fitz
    except Exception as exc:
        raise RuntimeError("PyMuPDF is required for hardware completeness checks.") from exc

    crop_metas: list[dict[str, Any]] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        page_count_total = max(len(doc), 1)
        for page_idx, page in enumerate(doc):
            page_rect = page.rect
            page_text = page.get_text("text") or ""
            rects = _text_anchor_rects(page, page_rect)
            if _needs_tiles(page_text, rects):
                rects.extend(_tile_rects(page_rect, visual_only=not page_text.strip()))

            for source, score, bbox, crop_type, rotation in _dedupe_rects(rects, page_rect):
                if crop_type not in {"hardware", "mixed"} and "hardware" not in source.lower():
                    continue
                rect = fitz.Rect(*bbox)
                text = _clip_text(page, rect)
                crop_metas.append(
                    {
                        "page_index": page_idx,
                        "page": page_idx + 1,
                        "crop_type": crop_type or "hardware",
                        "confidence": round(float(score), 3),
                        "source": source,
                        "bbox": tuple(round(float(v), 2) for v in bbox),
                        "text": text,
                        "priority": _crop_priority(source, text),
                        "rotation": int(rotation or 0),
                    }
                )

        crop_metas.sort(key=lambda crop: (crop.get("priority") or 0, crop.get("confidence") or 0), reverse=True)
        if any((crop.get("priority") or 0) >= 7 for crop in crop_metas):
            crop_metas = [crop for crop in crop_metas if (crop.get("priority") or 0) >= 7]
        crop_metas = crop_metas[:max_candidates]

        candidates: list[dict[str, Any]] = []
        for meta in crop_metas:
            page = doc[int(meta["page_index"])]
            rect = fitz.Rect(*meta["bbox"])
            render_dpi = _bounded_dpi(rect, min(360, int(dpi * 1.35)) if meta.get("rotation") else dpi)
            img_bytes = _render_crop_bytes(page, rect, dpi=render_dpi, rotation_degrees=int(meta.get("rotation") or 0))
            candidates.append(
                {
                    "page": meta["page"],
                    "crop_type": meta["crop_type"],
                    "confidence": meta["confidence"],
                    "source": meta["source"],
                    "bbox": meta["bbox"],
                    "text": meta["text"],
                    "base64_image": base64.b64encode(img_bytes).decode("ascii"),
                }
            )
    return candidates[:max_candidates]


def extract_pdf_text(file_bytes: bytes, *, max_chars: int = 45000) -> str:
    try:
        import fitz
    except Exception:
        return ""
    try:
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            chunks: list[str] = []
            total = 0
            for page in doc:
                chunk = page.get_text("text") or ""
                if not chunk:
                    continue
                remaining = max_chars - total
                if remaining <= 0:
                    break
                chunks.append(chunk[:remaining])
                total += len(chunks[-1])
        return "\n".join(chunks).strip()[:max_chars]
    except Exception:
        return ""


def _clip_text(page: Any, rect: Any, max_chars: int = 6000) -> str:
    try:
        return (page.get_text("text", clip=rect) or "")[:max_chars]
    except Exception:
        return ""


def _render_crop_bytes(page: Any, rect: Any, *, dpi: int, rotation_degrees: int = 0) -> bytes:
    pix = page.get_pixmap(dpi=dpi, clip=rect, alpha=False)
    if not rotation_degrees:
        return pix.tobytes("jpeg", jpg_quality=88)

    from PIL import Image

    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    img = img.rotate(rotation_degrees, expand=True)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def _bounded_dpi(rect: Any, desired_dpi: int, *, max_pixels: int = 6_000_000) -> int:
    area = max(float(rect.width) * float(rect.height), 1.0)
    pixels_at_desired = area * (desired_dpi / 72.0) ** 2
    if pixels_at_desired <= max_pixels:
        return desired_dpi
    scaled = int((max_pixels / area) ** 0.5 * 72.0)
    return max(120, min(desired_dpi, scaled))


def _keyword_crop_type(keyword: str) -> str:
    upper = keyword.upper()
    if upper == "DOOR AND HARDWARE":
        return "mixed"
    return "hardware" if upper in HARDWARE_ANCHORS or "HARDWARE" in upper else "mixed"


def _crop_priority(source: str, text: str) -> int:
    source_upper = source.upper()
    text_upper = text.upper()
    has_set_header = bool(re.search(r"\b(?:SET|HW\s*SET|HARDWARE\s*SET)\s*#?\s*[A-Z]?\d+[A-Z]?\b", text_upper))
    has_item_terms = bool(re.search(r"\b(EXIT\s+DEVICE|CONTINUOUS\s+HINGE|HINGE|CLOSER|LOCKSET|LATCHSET|CYLINDER|THRESHOLD|WEATHERSTRIP|GASKET|SWEEP|PUSH\s+PLATE|PULL)\b", text_upper))
    looks_like_door_schedule = bool(re.search(r"\bDOOR\s+NUMBER\b|\bTYPE\s+WIDTH\b|\bWINDOW\s+NOTES\b|\bWINDOW\s+TYPES\b", text_upper))
    if has_set_header and has_item_terms:
        return 9
    if has_set_header:
        return 8
    if has_item_terms and "HARDWARE" in text_upper:
        return 7
    if looks_like_door_schedule and not has_set_header:
        return 0
    if "DOOR HARDWARE" in source_upper:
        return 5
    if any(token in source_upper for token in ("HARDWARE SET", "HARDWARE SCHEDULE", "HDWR SET", "HW SET")):
        return 4
    if "HARDWARE SET DESCRIPTIONS" in text_upper or "DOOR HARDWARE" in text_upper:
        return 3
    if any(token in text_upper for token in ("HARDWARE SET", "HARDWARE SCHEDULE", "HW SET")):
        return 2
    return 1


def _expand_rect(rect: Any, page_rect: Any, x_pad: float = 0.08, y_pad: float = 0.10) -> Any:
    width = rect.width
    height = rect.height
    expanded = rect + (
        -max(24, width * x_pad),
        -max(24, height * y_pad),
        max(120, width * 2.5),
        max(180, height * 10.0),
    )
    return expanded & page_rect


def _expand_hardware_title_rect(rect: Any, page_rect: Any) -> Any:
    width = page_rect.width
    height = page_rect.height
    if rect.x0 > width * 0.45 or rect.y0 > height * 0.45:
        expanded = rect + (
            -max(260, width * 0.72),
            -max(260, height * 0.34),
            max(120, width * 0.04),
            max(80, height * 0.04),
        )
        return expanded & page_rect
    return _expand_rect(rect, page_rect, x_pad=0.12, y_pad=0.12)


def _hardware_section_tiles(expanded: Any, anchor_rect: Any, page_rect: Any, columns: int = 4) -> list[tuple]:
    width = page_rect.width
    height = page_rect.height
    if not (anchor_rect.x0 > width * 0.45 or anchor_rect.y0 > height * 0.45):
        return []

    y0 = max(page_rect.y0, expanded.y0 + 70)
    y1 = min(page_rect.y1, expanded.y1)
    if y1 <= y0:
        y0, y1 = expanded.y0, expanded.y1

    x0 = expanded.x0
    x1 = expanded.x1
    crop_width = x1 - x0
    if crop_width <= 0:
        return []

    tile_width = crop_width / columns
    overlap = min(90.0, tile_width * 0.18)
    rects = []
    for idx in range(columns):
        tx0 = max(page_rect.x0, x0 + idx * tile_width - (overlap if idx else 0))
        tx1 = min(page_rect.x1, x0 + (idx + 1) * tile_width + (overlap if idx < columns - 1 else 0))
        rects.append((f"text:DOOR HARDWARE column {idx + 1}/{columns}", 0.985 - idx * 0.002, (tx0, y0, tx1, y1), "hardware", 0))

    rects.extend(
        [
            (
                "text:DOOR HARDWARE middle-upper sets",
                0.9845,
                (
                    max(page_rect.x0, x0 + crop_width * 0.32),
                    max(page_rect.y0, y0 + 15),
                    min(page_rect.x1, x0 + crop_width * 0.50),
                    min(page_rect.y1, y0 + (y1 - y0) * 0.46),
                ),
                "hardware",
                0,
            ),
            (
                "text:DOOR HARDWARE upper-right sets",
                0.9825,
                (
                    max(page_rect.x0, x0 + crop_width * 0.55),
                    expanded.y0,
                    min(page_rect.x1, x1),
                    y0 + (y1 - y0) * 0.55,
                ),
                "hardware",
                0,
            ),
            (
                "text:DOOR HARDWARE lower-right sets",
                0.982,
                (
                    max(page_rect.x0, x0 + crop_width * 0.55),
                    y0 + (y1 - y0) * 0.48,
                    min(page_rect.x1, x1),
                    y1,
                ),
                "hardware",
                0,
            ),
        ]
    )
    return rects


def _text_anchor_rects(page: Any, page_rect: Any) -> list[tuple]:
    rects: list[tuple] = []
    for keyword in SCHEDULE_KEYWORDS:
        try:
            found_rects = page.search_for(keyword)
        except Exception:
            continue
        for found in found_rects:
            crop_type = _keyword_crop_type(keyword)
            expanded = _expand_hardware_title_rect(found, page_rect) if keyword.upper() in HARDWARE_ANCHORS else _expand_rect(found, page_rect)
            if expanded.get_area() / max(page_rect.get_area(), 1) >= 0.70:
                continue
            lower_section = keyword.upper() == "DOOR HARDWARE" and (found.x0 > page_rect.width * 0.45 or found.y0 > page_rect.height * 0.45)
            score = 0.974 if lower_section else 0.86
            rects.append((f"text:{keyword}", score, tuple(expanded), crop_type, 0))
            if lower_section:
                rects.extend(_hardware_section_tiles(expanded, found, page_rect))
    return rects


def _needs_tiles(page_text: str, rects: list[tuple]) -> bool:
    if len(rects) < 2:
        return True
    upper = page_text.upper()
    return bool(any(token in upper for token in ("DOOR HARDWARE", "HARDWARE SET", "HARDWARE SCHEDULE")) and len(rects) < 4)


def _tile_rects(page_rect: Any, *, visual_only: bool = False) -> list[tuple]:
    width = page_rect.width
    height = page_rect.height
    tiles = [
        ("tile_main_sheet_area", 0.40, (0, 0, width * 0.88, height), "hardware", 0),
        ("tile_left_band", 0.39, (0, 0, width * 0.62, height), "hardware", 0),
        ("tile_top_left", 0.38, (0, 0, width * 0.55, height * 0.45), "mixed", 0),
        ("tile_top_right", 0.38, (width * 0.45, 0, width, height * 0.45), "mixed", 0),
        ("tile_right_schedule_band", 0.37, (width * 0.88, 0, width, height * 0.36), "mixed", 0),
        ("tile_bottom_left", 0.36, (0, height * 0.45, width * 0.55, height), "mixed", 0),
        ("tile_bottom_right", 0.35, (width * 0.45, height * 0.45, width, height), "hardware", 0),
        ("tile_center", 0.30, (width * 0.20, height * 0.20, width * 0.80, height * 0.80), "mixed", 0),
    ]
    if not visual_only:
        return tiles
    return [
        ("tile_visual_bottom_hardware_band", 0.64, (width * 0.24, height * 0.70, width * 0.72, height * 0.98), "hardware", 0),
        ("tile_rotated_hardware_schedule_ccw", 0.61, (width * 0.54, height * 0.50, width * 0.97, height * 0.74), "hardware", 90),
        ("tile_rotated_hardware_schedule_cw", 0.605, (width * 0.54, height * 0.50, width * 0.97, height * 0.74), "hardware", 270),
        *tiles,
    ]


def _dedupe_rects(rects: list[tuple], page_rect: Any) -> list[tuple]:
    cleaned: list[tuple] = []
    for source, score, bbox, crop_type, rotation in rects:
        x0, y0, x1, y1 = bbox
        x0 = max(0.0, min(float(x0), page_rect.width))
        y0 = max(0.0, min(float(y0), page_rect.height))
        x1 = max(0.0, min(float(x1), page_rect.width))
        y1 = max(0.0, min(float(y1), page_rect.height))
        if x1 <= x0 or y1 <= y0:
            continue
        if (x1 - x0) * (y1 - y0) < page_rect.get_area() * 0.005:
            continue
        bbox = (x0, y0, x1, y1)
        if any(int(rotation or 0) == int(existing[4] or 0) and _iou(bbox, existing[2]) > 0.75 for existing in cleaned):
            continue
        cleaned.append((source, score, bbox, crop_type, int(rotation or 0)))

    cleaned.sort(key=lambda item: item[1], reverse=True)
    return cleaned


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return inter / max(area_a + area_b - inter, 1.0)
