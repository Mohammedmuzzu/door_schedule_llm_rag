import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = REPO_ROOT / "data" / "pdfs"
OUT_DIR = REPO_ROOT / ".codex_work" / "fastbid_corpus_benchmark"
BACKEND_DIR = REPO_ROOT / "apps" / "fastbid24-door-analyzer" / "backend"

sys.path.insert(0, str(BACKEND_DIR))

from extraction import extract_pdf_secure  # noqa: E402


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def summarize(pdf: Path, data: dict, elapsed: int) -> dict:
    analysis = data.get("analysis") or {}
    qa = data.get("qa") or {}
    sets = analysis.get("hardware_set_review") or []
    doors = analysis.get("door_analysis") or []
    mapping = analysis.get("door_hardware_mapping") or []
    steps = qa.get("pipeline_steps") or []
    rescue_step = next((step for step in steps if step.get("label") == "Completeness check"), {})
    return {
        "file": pdf.name,
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
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    summary_path = OUT_DIR / "summary.json"
    status_path = OUT_DIR / "status.json"
    rows: list[dict] = []
    if summary_path.exists():
        try:
            rows = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            rows = []
    done = {row.get("file") for row in rows if row.get("status") == "ok"}

    for index, pdf in enumerate(pdfs, start=1):
        if pdf.name in done:
            continue
        write_json(status_path, {"state": "running", "index": index, "total": len(pdfs), "file": pdf.name, "started_at": time.time()})
        started = time.time()
        try:
            data = extract_pdf_secure(pdf.read_bytes(), pdf.name, "Supply & Installation", run_rfis=False)
            elapsed = int(time.time() - started)
            result_path = OUT_DIR / f"{safe_name(pdf.stem)}.json"
            write_json(result_path, data)
            row = summarize(pdf, data, elapsed)
        except Exception as exc:
            elapsed = int(time.time() - started)
            row = {"file": pdf.name, "status": "error", "elapsed_seconds_wall": elapsed, "error": str(exc)}
        rows = [old for old in rows if old.get("file") != pdf.name]
        rows.append(row)
        write_json(summary_path, rows)
        write_json(status_path, {"state": "completed_file", "index": index, "total": len(pdfs), "file": pdf.name, "row": row, "updated_at": time.time()})
        print(json.dumps(row), flush=True)

    write_json(status_path, {"state": "done", "total": len(pdfs), "completed": len(rows), "updated_at": time.time()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
