import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "apps" / "fastbid24-door-analyzer" / "backend"
OUT_DIR = REPO_ROOT / ".codex_work" / "fastbid_targeted_after_patch"
PDFS = [
    REPO_ROOT / "data" / "pdfs" / "A611 - Door Schedule.pdf",
    REPO_ROOT / "data" / "pdfs" / "Door Schedule & Hardware Sets.pdf",
]

sys.path.insert(0, str(BACKEND_DIR))

from extraction import extract_pdf_secure  # noqa: E402


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def summarize(pdf: Path, data: dict, elapsed: int) -> dict:
    analysis = data.get("analysis") or {}
    qa = data.get("qa") or {}
    sets = analysis.get("hardware_set_review") or []
    mapping = analysis.get("door_hardware_mapping") or []
    steps = qa.get("pipeline_steps") or []
    rescue_step = next((step for step in steps if step.get("label") == "Completeness check"), {})
    return {
        "file": pdf.name,
        "elapsed_seconds_wall": elapsed,
        "doors": len(analysis.get("door_analysis") or []),
        "sets": len(sets),
        "items": sum(len(s.get("items") or []) for s in sets),
        "sets_with_items": sum(1 for s in sets if s.get("items")),
        "empty_sets": [s.get("hardware_set") for s in sets if not s.get("items")],
        "mapping_rows": len(mapping),
        "failed_mapping_rows": sum(1 for row in mapping if row.get("status") == "FAILED_EXTRACTION_REVIEW_REQUIRED"),
        "no_hw_set_rows": sum(1 for row in mapping if row.get("status") == "NO_HW_SET"),
        "qa_issues": len(qa.get("mapping_qa_issues") or []),
        "rescue_attempted": not bool(rescue_step.get("skipped", True)),
        "rescue_items_added": rescue_step.get("output_count") or 0,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, pdf in enumerate(PDFS, start=1):
        write_json(OUT_DIR / "status.json", {"state": "running", "index": idx, "total": len(PDFS), "file": pdf.name})
        started = time.time()
        data = extract_pdf_secure(pdf.read_bytes(), pdf.name, "Supply & Installation", run_rfis=False)
        elapsed = int(time.time() - started)
        write_json(OUT_DIR / f"{safe_name(pdf.stem)}.json", data)
        row = summarize(pdf, data, elapsed)
        rows.append(row)
        write_json(OUT_DIR / "summary.json", rows)
        print(json.dumps(row), flush=True)
    write_json(OUT_DIR / "status.json", {"state": "done", "total": len(PDFS), "completed": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
