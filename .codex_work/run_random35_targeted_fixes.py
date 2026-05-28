import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "apps" / "fastbid24-door-analyzer" / "backend"
OUT_DIR = REPO_ROOT / ".codex_work" / "fastbid_random35_targeted_fixes"
PDFS = [
    REPO_ROOT / "data/pdfs/Project - 70/Door Schedule 1.pdf",
    REPO_ROOT / "data/pdfs/Project - 2/A701-DOOR-SCHEDULE,-ELEVATIONS-&-DETAILS-Rev.0.pdf",
    REPO_ROOT / "data/pdfs/Project - 49/Door & Hardware Schedule.pdf",
    REPO_ROOT / "data/pdfs/Project - 44/Door & Hardware schedule.pdf",
    REPO_ROOT / "data/pdfs/New Project-10/Door Hardware.pdf",
    REPO_ROOT / "data/pdfs/Project - 23/Door Schedule.pdf",
    REPO_ROOT / "data/pdfs/New Project-3/Doors and Hardware.pdf",
]

sys.path.insert(0, str(BACKEND_DIR))

from extraction import extract_pdf_secure  # noqa: E402


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


def summarize(pdf: Path, data: dict, elapsed: int) -> dict:
    analysis = data.get("analysis") or {}
    qa = data.get("qa") or {}
    doors = analysis.get("door_analysis") or []
    sets = analysis.get("hardware_set_review") or []
    mapping = analysis.get("door_hardware_mapping") or []
    steps = qa.get("pipeline_steps") or []
    return {
        "file": pdf.name,
        "relative_path": str(pdf.relative_to(REPO_ROOT)),
        "status": "ok",
        "elapsed_seconds_wall": elapsed,
        "doors": len(doors),
        "sets": len(sets),
        "items": sum(len(s.get("items") or []) for s in sets),
        "sets_with_items": sum(1 for s in sets if s.get("items")),
        "empty_sets": [s.get("hardware_set") for s in sets if not s.get("items")],
        "mapping_rows": len(mapping),
        "failed_mapping_rows": sum(1 for row in mapping if row.get("status") == "FAILED_EXTRACTION_REVIEW_REQUIRED"),
        "no_hw_set_rows": sum(1 for row in mapping if row.get("status") == "NO_HW_SET"),
        "ok_mapping_rows": sum(1 for row in mapping if row.get("status") == "OK"),
        "qa_issues": len(qa.get("mapping_qa_issues") or []),
        "steps": steps,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, pdf in enumerate(PDFS, start=1):
        write_json(OUT_DIR / "status.json", {"state": "running", "index": index, "total": len(PDFS), "file": str(pdf.relative_to(REPO_ROOT))})
        started = time.time()
        try:
            data = extract_pdf_secure(pdf.read_bytes(), pdf.name, "Supply & Installation", run_rfis=False)
            elapsed = int(time.time() - started)
            write_json(OUT_DIR / f"{index:02d}_{safe_name(str(pdf.relative_to(REPO_ROOT)))}.json", data)
            row = summarize(pdf, data, elapsed)
        except Exception as exc:
            row = {
                "file": pdf.name,
                "relative_path": str(pdf.relative_to(REPO_ROOT)),
                "status": "error",
                "elapsed_seconds_wall": int(time.time() - started),
                "error": str(exc),
            }
        rows.append(row)
        write_json(OUT_DIR / "summary.json", rows)
        print(json.dumps(row), flush=True)
    write_json(OUT_DIR / "status.json", {"state": "done", "total": len(PDFS), "completed": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
