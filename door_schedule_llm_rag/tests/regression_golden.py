"""
Focused golden regression runner for max-accuracy extraction.

This is intentionally smaller than the full corpus run. It runs representative
PDFs through the same safe worker path and asserts minimum extraction floors.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = APP_DIR.parent
DEFAULT_BASELINE = APP_DIR / "tests" / "golden_max_accuracy_baseline.json"


def _safe_id(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in value)[:80]


def run_case(case: dict, output_root: Path, timeout: int) -> dict:
    pdf_path = Path(case["pdf_path"])
    output_dir = output_root / "runs" / _safe_id(case["id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(APP_DIR / "scripts" / "full_corpus_runner.py"),
        "--worker-pdf",
        str(pdf_path),
        "--worker-output",
        str(output_dir),
        "--output-root",
        str(output_root),
    ]
    env = os.environ.copy()
    env.setdefault("FULL_CORPUS_PDF_TIMEOUT", str(timeout))
    completed = subprocess.run(
        command,
        cwd=str(REPO_DIR),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout + 60,
    )
    (output_dir / "regression_worker.log").write_text(completed.stdout or "", encoding="utf-8")
    result_path = output_dir / "worker_result.json"
    if completed.returncode != 0 or not result_path.exists():
        return {
            "id": case["id"],
            "status": "error",
            "doors": 0,
            "hardware": 0,
            "error": f"worker exit {completed.returncode}",
        }
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["id"] = case["id"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--output-root", default=str(APP_DIR / "qa_out" / f"golden_regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    cases = baseline["cases"][: args.limit] if args.limit else baseline["cases"]
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    rows = []
    failures = []
    for case in cases:
        print(f"RUN {case['id']}: {case['pdf_path']}", flush=True)
        try:
            result = run_case(case, output_root, args.timeout)
        except Exception as exc:
            result = {"id": case["id"], "status": "error", "doors": 0, "hardware": 0, "error": str(exc)}

        result["min_doors"] = case.get("min_doors", 0)
        result["min_hardware"] = case.get("min_hardware", 0)
        result["purpose"] = case.get("purpose", "")
        ok = (
            result.get("status") == "ok"
            and int(result.get("doors", 0)) >= int(case.get("min_doors", 0))
            and int(result.get("hardware", 0)) >= int(case.get("min_hardware", 0))
        )
        result["passed"] = ok
        rows.append(result)
        print(
            f"  -> {'PASS' if ok else 'FAIL'} doors={result.get('doors')} hardware={result.get('hardware')} "
            f"crops={result.get('crop_count', 0)} crop_added={result.get('crop_door_added', 0)}/{result.get('crop_hw_added', 0)}",
            flush=True,
        )
        if not ok:
            failures.append(result)

    summary = {
        "total": len(rows),
        "passed": len(rows) - len(failures),
        "failed": len(failures),
        "rows": rows,
    }
    (output_root / "golden_regression_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"total": summary["total"], "passed": summary["passed"], "failed": summary["failed"]}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
