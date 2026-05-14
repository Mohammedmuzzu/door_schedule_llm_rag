"""
Safe full-corpus QA runner for door schedule PDFs.

This script is intentionally separate from the app and older batch scripts:
- processes one PDF per output folder so runs are resumable;
- disables S3 uploads for local QA;
- uses a local SQLite database unless DATABASE_URL is explicitly provided;
- writes per-PDF metrics for visual triage and dashboard generation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
REPO_DIR = APP_DIR.parent
sys.path.append(str(APP_DIR))


def _configure_safe_env(output_root: Path) -> None:
    os.environ.setdefault("DEPLOYMENT_ENV", "production")
    os.environ.setdefault("LLM_PROVIDER", "openai")
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    os.environ.setdefault("MAX_PAGE_CHARS", "35000")
    os.environ.setdefault("RAG_DATA_DIR", str(output_root / "rag_data"))
    os.environ["S3_BUCKET_NAME"] = ""
    os.environ["AWS_ACCESS_KEY_ID"] = ""
    os.environ["AWS_SECRET_ACCESS_KEY"] = ""
    os.environ["S3_ENDPOINT_URL"] = ""
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{(output_root / 'qa_full_corpus.db').as_posix()}")


def _safe_slug(value: str, limit: int = 80) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return (value or "pdf")[:limit]


def _run_id(pdf_path: Path, root: Path) -> str:
    try:
        rel = pdf_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = pdf_path.resolve().as_posix()
    digest = hashlib.sha1(rel.lower().encode("utf-8")).hexdigest()[:10]
    return f"{digest}_{_safe_slug(pdf_path.stem)}"


def _iter_pdfs(root: Path) -> Iterable[Path]:
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


def _page_count(pdf_path: Path) -> int:
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def build_inventory(target_dir: Path, output_root: Path) -> list[dict]:
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for idx, pdf in enumerate(_iter_pdfs(target_dir), 1):
        try:
            rel = pdf.resolve().relative_to(target_dir.resolve()).as_posix()
        except ValueError:
            rel = pdf.name
        rows.append(
            {
                "index": idx,
                "run_id": _run_id(pdf, target_dir),
                "pdf_path": str(pdf),
                "relative_path": rel,
                "file_name": pdf.name,
                "parent": pdf.parent.name,
                "bytes": pdf.stat().st_size,
                "pages": _page_count(pdf),
            }
        )

    inventory_path = output_root / "inventory.csv"
    with inventory_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    (output_root / "inventory.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Inventory written: {inventory_path} ({len(rows)} PDFs)", flush=True)
    return rows


def _load_done(report_path: Path) -> set[str]:
    if not report_path.exists():
        return set()
    done: set[str] = set()
    with report_path.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status") == "ok":
                done.add(row.get("run_id", ""))
    return done


def _append_report(report_path: Path, row: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    exists = report_path.exists()
    with report_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _worker_result_path(output_dir: Path) -> Path:
    return output_dir / "worker_result.json"


def _collect_crop_metrics(output_root: Path, pdf_name: str) -> dict:
    metrics = {
        "crop_count": 0,
        "crop_rescue_attempt_pages": 0,
        "crop_rescue_pages": 0,
        "crop_door_added": 0,
        "crop_hw_added": 0,
    }
    runs_dir = output_root / "rag_data" / "runs"
    if not runs_dir.exists():
        return metrics
    try:
        files = sorted(runs_dir.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[:50]:
            events = []
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        events.append(json.loads(line))
            if not events or events[0].get("pdf_name") != pdf_name:
                continue
            for event in events:
                if event.get("event") != "page_extracted":
                    continue
                metrics["crop_count"] += int(event.get("crop_count") or 0)
                report = event.get("verify_report") or {}
                if report.get("crop_rescue_attempted"):
                    metrics["crop_rescue_attempt_pages"] += 1
                if report.get("crop_rescue"):
                    metrics["crop_rescue_pages"] += 1
                metrics["crop_door_added"] += int(report.get("crop_door_added") or 0)
                metrics["crop_hw_added"] += int(report.get("crop_hw_added") or 0)
            return metrics
    except Exception:
        return metrics
    return metrics


def run_one_pdf_worker(pdf_path: Path, output_dir: Path, output_root: Path) -> None:
    _configure_safe_env(output_root)

    from llm_extract import llm_config
    import pipeline
    from db import init_db

    pipeline.upload_file_to_s3 = None
    llm_config.set("openai", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    init_db()

    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    doors, hardware = pipeline.run_pipeline(
        pdf_folder=str(pdf_path.parent),
        output_dir=str(output_dir),
        use_rag=True,
        pdf_files=[pdf_path],
    )
    crop_metrics = getattr(pipeline, "LAST_CROP_METRICS", None) or _collect_crop_metrics(output_root, pdf_path.name)
    result = _summarize_result(output_dir.name, pdf_path, output_dir, started, doors, hardware, "ok", crop_metrics=crop_metrics)
    _worker_result_path(output_dir).write_text(json.dumps(result, indent=2), encoding="utf-8")


def _summarize_result(run_id: str, pdf_path: Path, output_dir: Path, started: float, doors, hardware, status: str, error: str = "", crop_metrics: dict | None = None) -> dict:
    door_count = int(len(doors)) if doors is not None else 0
    hw_count = int(len(hardware)) if hardware is not None else 0
    duplicate_doors = 0
    missing_door_number = 0
    missing_width = 0
    missing_height = 0
    missing_hw_set = 0
    if doors is not None and not doors.empty:
        if {"project_id", "door_number"}.issubset(doors.columns):
            duplicate_doors = int(doors.duplicated(subset=["project_id", "door_number"]).sum())
        if "door_number" in doors.columns:
            missing_door_number = int(doors["door_number"].isna().sum())
        if "door_width" in doors.columns:
            missing_width = int(doors["door_width"].isna().sum())
        if "door_height" in doors.columns:
            missing_height = int(doors["door_height"].isna().sum())
        if "hardware_set" in doors.columns:
            missing_hw_set = int(doors["hardware_set"].isna().sum())

    crop_metrics = crop_metrics or {}
    return {
        "run_id": run_id,
        "status": status,
        "pdf_path": str(pdf_path),
        "pdf_name": pdf_path.name,
        "output_dir": str(output_dir),
        "pages": _page_count(pdf_path),
        "doors": door_count,
        "hardware": hw_count,
        "duplicate_doors": duplicate_doors,
        "missing_door_number": missing_door_number,
        "missing_width": missing_width,
        "missing_height": missing_height,
        "missing_hw_set": missing_hw_set,
        "crop_count": int(crop_metrics.get("crop_count", 0)),
        "crop_rescue_attempt_pages": int(crop_metrics.get("crop_rescue_attempt_pages", 0)),
        "crop_rescue_pages": int(crop_metrics.get("crop_rescue_pages", 0)),
        "crop_door_added": int(crop_metrics.get("crop_door_added", 0)),
        "crop_hw_added": int(crop_metrics.get("crop_hw_added", 0)),
        "elapsed_s": round(time.time() - started, 1),
        "error": error[:1000],
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }


def run_corpus(target_dir: Path, output_root: Path, limit: int | None = None, resume: bool = True) -> Path:
    _configure_safe_env(output_root)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY must be present in the process environment.")

    inventory = build_inventory(target_dir, output_root)
    if limit is not None:
        inventory = inventory[:limit]

    report_path = output_root / "deep_e2e_report.csv"
    done = _load_done(report_path) if resume else set()
    print(f"Starting corpus run: {len(inventory)} PDFs, resume={resume}, already_done={len(done)}", flush=True)

    for pos, item in enumerate(inventory, 1):
        run_id = item["run_id"]
        pdf_path = Path(item["pdf_path"])
        output_dir = output_root / "runs" / run_id
        if resume and run_id in done and (output_dir / "extraction_results_llm.xlsx").exists():
            print(f"[{pos}/{len(inventory)}] SKIP {run_id}", flush=True)
            continue

        output_dir.mkdir(parents=True, exist_ok=True)
        started = time.time()
        print(f"[{pos}/{len(inventory)}] START {pdf_path}", flush=True)
        result_path = _worker_result_path(output_dir)
        try:
            if result_path.exists():
                result_path.unlink()
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker-pdf",
                str(pdf_path),
                "--worker-output",
                str(output_dir),
                "--output-root",
                str(output_root),
            ]
            completed = subprocess.run(
                command,
                cwd=str(REPO_DIR),
                env=os.environ.copy(),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=int(os.environ.get("FULL_CORPUS_PDF_TIMEOUT", "1200")),
            )
            (output_dir / "worker.log").write_text(completed.stdout or "", encoding="utf-8")
            if completed.returncode != 0:
                raise RuntimeError(f"worker exit {completed.returncode}")
            if not result_path.exists():
                raise RuntimeError("worker did not write result JSON")
            row = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            error_path = output_dir / "error.txt"
            error_text = "".join(traceback.format_exception(exc))
            error_path.write_text(error_text, encoding="utf-8")
            row = _summarize_result(run_id, pdf_path, output_dir, started, None, None, "error", str(exc))
            print(f"[{pos}/{len(inventory)}] ERROR {run_id}: {exc}", flush=True)
        else:
            row["run_id"] = run_id
            print(
                f"[{pos}/{len(inventory)}] OK {run_id}: doors={row['doors']} hardware={row['hardware']} elapsed={row['elapsed_s']}s",
                flush=True,
            )

        _append_report(report_path, row)

    print(f"Corpus report written: {report_path}", flush=True)
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", default=None)
    parser.add_argument("--output-root", default=str(APP_DIR / "qa_out" / f"full_corpus_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--worker-pdf", default=None)
    parser.add_argument("--worker-output", default=None)
    args = parser.parse_args()

    if args.worker_pdf:
        if not args.worker_output:
            raise ValueError("--worker-output is required with --worker-pdf")
        run_one_pdf_worker(Path(args.worker_pdf), Path(args.worker_output), Path(args.output_root))
        return 0

    output_root = Path(args.output_root)
    if not args.target_dir:
        raise ValueError("--target-dir is required")
    target_dir = Path(args.target_dir)
    if not target_dir.exists():
        raise FileNotFoundError(target_dir)

    if args.inventory_only:
        build_inventory(target_dir, output_root)
        return 0

    run_corpus(target_dir, output_root, limit=args.limit, resume=not args.no_resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
