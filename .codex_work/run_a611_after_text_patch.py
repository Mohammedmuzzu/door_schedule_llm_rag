import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "apps" / "fastbid24-door-analyzer" / "backend"
PDF = REPO_ROOT / "data" / "pdfs" / "A611 - Door Schedule.pdf"
OUT_DIR = REPO_ROOT / ".codex_work" / "fastbid_a611_after_text_patch"

sys.path.insert(0, str(BACKEND_DIR))

from extraction import extract_pdf_secure  # noqa: E402


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "status.json").write_text(json.dumps({"state": "running", "file": PDF.name}, indent=2), encoding="utf-8")
    started = time.time()
    data = extract_pdf_secure(PDF.read_bytes(), PDF.name, "Supply & Installation", run_rfis=False)
    elapsed = int(time.time() - started)
    analysis = data.get("analysis") or {}
    qa = data.get("qa") or {}
    sets = analysis.get("hardware_set_review") or []
    mapping = analysis.get("door_hardware_mapping") or []
    row = {
        "file": PDF.name,
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
        "steps": qa.get("pipeline_steps") or [],
    }
    (OUT_DIR / "A611.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
    (OUT_DIR / "status.json").write_text(json.dumps({"state": "done", "row": row}, indent=2), encoding="utf-8")
    print(json.dumps(row), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
