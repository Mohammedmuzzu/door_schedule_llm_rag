"""Render PDF pages and detected schedule crops for visual QA."""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
sys.path.append(str(APP_DIR))


def _parse_box(value: str | None):
    if not value:
        return None
    parts = [int(float(part.strip())) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--extra-box must be x0,y0,x1,y1")
    return tuple(parts)


def render(pdf_path: Path, output_dir: Path, page_index: int, zoom: float, extra_box):
    from page_extractor import extract_structured_page

    output_dir.mkdir(parents=True, exist_ok=True)
    _text, page_type, _is_cont, _base64_img, crops = extract_structured_page(
        str(pdf_path),
        page_index,
        include_crops=True,
    )

    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    full_path = output_dir / f"page_{page_index + 1}_full.png"
    pix.save(str(full_path))

    img = Image.open(full_path)
    annotated = img.copy()
    draw = ImageDraw.Draw(annotated)

    if extra_box:
        draw.rectangle(extra_box, outline="red", width=5)
        img.crop(extra_box).save(output_dir / f"page_{page_index + 1}_extra_box.png")

    crop_summaries = []
    for idx, crop in enumerate(crops, 1):
        bbox = crop.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        box = tuple(int(round(float(v) * zoom)) for v in bbox)
        crop_type = str(crop.get("crop_type") or "crop")
        draw.rectangle(box, outline="lime", width=4)
        crop_path = output_dir / f"page_{page_index + 1}_crop_{idx}_{crop_type}.png"
        crop_b64 = crop.get("base64_image")
        if crop_b64:
            try:
                crop_img = Image.open(io.BytesIO(base64.b64decode(crop_b64))).convert("RGB")
                crop_img.save(crop_path)
            except Exception:
                img.crop(box).save(crop_path)
        else:
            img.crop(box).save(crop_path)
        crop_summaries.append(
            {
                "idx": idx,
                "path": str(crop_path),
                "crop_type": crop_type,
                "source": crop.get("source"),
                "confidence": crop.get("confidence"),
                "bbox": bbox,
                "rotation_degrees": crop.get("rotation_degrees"),
            }
        )

    annotated_path = output_dir / f"page_{page_index + 1}_annotated.png"
    annotated.save(annotated_path)
    summary = {
        "pdf": str(pdf_path),
        "page": page_index + 1,
        "page_type": page_type,
        "full": str(full_path),
        "annotated": str(annotated_path),
        "crops": crop_summaries,
    }
    (output_dir / f"page_{page_index + 1}_visual_qa.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--page", type=int, default=1, help="1-based page number")
    parser.add_argument("--zoom", type=float, default=2.0)
    parser.add_argument("--extra-box", default=None, help="Optional pixel crop x0,y0,x1,y1")
    args = parser.parse_args()

    summary = render(
        Path(args.pdf),
        Path(args.output_dir),
        max(0, args.page - 1),
        args.zoom,
        _parse_box(args.extra_box),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
