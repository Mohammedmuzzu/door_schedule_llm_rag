import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "apps" / "fastbid24-door-analyzer" / "backend"
SAMPLE_FILE = REPO_ROOT / ".codex_work" / "random35_candidates.json"
OUT_DIR = REPO_ROOT / ".codex_work" / "fastbid_random35_benchmark"

sys.path.insert(0, str(BACKEND_DIR))

from extraction import extract_pdf_secure  # noqa: E402


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)


def classify_file(path: Path) -> str:
    low = str(path).lower()
    has_door = "door" in low or "a6" in low or "a7" in low or "a8" in low or "a400" in low
    has_hw = "hardware" in low or "division 08" in low
    if has_door and has_hw:
        return "door_hardware"
    if has_hw:
        return "hardware_only"
    if has_door:
        return "door_only"
    return "unknown"


def summarize(pdf: Path, data: dict, elapsed: int) -> dict:
    analysis = data.get("analysis") or {}
    qa = data.get("qa") or {}
    doors = analysis.get("door_analysis") or []
    sets = analysis.get("hardware_set_review") or []
    mapping = analysis.get("door_hardware_mapping") or []
    steps = qa.get("pipeline_steps") or []
    rescue_step = next((step for step in steps if step.get("label") == "Completeness check"), {})
    return {
        "file": pdf.name,
        "relative_path": str(pdf.relative_to(REPO_ROOT)),
        "class": classify_file(pdf),
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
        "truncated": bool(qa.get("truncated")),
        "extraction_complete": bool(qa.get("extraction_complete")),
        "rescue_attempted": not bool(rescue_step.get("skipped", True)),
        "rescue_items_added": rescue_step.get("output_count") or 0,
        "pipeline_elapsed_seconds": qa.get("elapsed_seconds"),
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample_payload = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    pdfs = []
    for item in sample_payload["sample"]:
        path = Path(item["path"])
        pdfs.append(path if path.is_absolute() else REPO_ROOT / path)
    summary_path = OUT_DIR / "summary.json"
    rows: list[dict] = []
    if summary_path.exists():
        try:
            rows = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            rows = []
    done = {row.get("relative_path") for row in rows if row.get("status") == "ok"}

    for index, pdf in enumerate(pdfs, start=1):
        rel = str(pdf.relative_to(REPO_ROOT))
        if rel in done:
            continue
        write_json(OUT_DIR / "status.json", {"state": "running", "index": index, "total": len(pdfs), "file": rel, "started_at": time.time()})
        started = time.time()
        try:
            data = extract_pdf_secure(pdf.read_bytes(), pdf.name, "Supply & Installation", run_rfis=False)
            elapsed = int(time.time() - started)
            result_name = f"{index:02d}_{safe_name(str(pdf.relative_to(REPO_ROOT)))}.json"
            write_json(OUT_DIR / result_name, data)
            row = summarize(pdf, data, elapsed)
        except Exception as exc:
            elapsed = int(time.time() - started)
            row = {
                "file": pdf.name,
                "relative_path": rel,
                "class": classify_file(pdf),
                "status": "error",
                "elapsed_seconds_wall": elapsed,
                "error": str(exc),
            }
        rows = [old for old in rows if old.get("relative_path") != rel]
        rows.append(row)
        write_json(summary_path, rows)
        write_json(OUT_DIR / "status.json", {"state": "completed_file", "index": index, "total": len(pdfs), "file": rel, "row": row, "updated_at": time.time()})
        print(json.dumps(row), flush=True)

    write_json(OUT_DIR / "status.json", {"state": "done", "total": len(pdfs), "completed": len(rows), "updated_at": time.time()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
