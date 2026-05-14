"""
Golden regression gate for full-corpus QA runs.

Capture tiered baselines (ok / medium / high severity) from deep_e2e_report.csv,
then compare a newer report to enforce:

- OK-severity PDFs: door and hardware counts must not drop vs baseline.
- Optional strict high-risk run_ids: total extracted rows must not decrease.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent


def _load_dashboard():
    path = SCRIPT_DIR / "full_corpus_dashboard.py"
    spec = importlib.util.spec_from_file_location("full_corpus_dashboard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load full_corpus_dashboard")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _score_rows(df: pd.DataFrame) -> pd.DataFrame:
    dash = _load_dashboard()
    severities = []
    issues_list = []
    for _, row in df.iterrows():
        sev, issues = dash._score_row(row)
        severities.append(sev)
        issues_list.append(";".join(issues))
    out = df.copy()
    out["severity"] = severities
    out["issues"] = issues_list
    return out


def cmd_capture(args: argparse.Namespace) -> int:
    run_root = Path(args.run_root)
    report_path = run_root / "deep_e2e_report.csv"
    if not report_path.exists():
        print(f"Missing {report_path}; run full_corpus_runner first.", file=sys.stderr)
        return 2
    report = pd.read_csv(report_path).fillna("")
    if "completed_at" in report.columns:
        report = report.sort_values("completed_at")
    report = report.drop_duplicates(subset=["run_id"], keep="last").reset_index(drop=True)
    scored = _score_rows(report)

    rows: dict[str, dict[str, Any]] = {}
    for _, row in scored.iterrows():
        rid = str(row["run_id"])
        rows[rid] = {
            "run_id": rid,
            "pdf_name": str(row.get("pdf_name", "")),
            "severity": str(row["severity"]),
            "status": str(row.get("status", "")),
            "doors": int(row.get("doors", 0) or 0),
            "hardware": int(row.get("hardware", 0) or 0),
            "issues": str(row.get("issues", "")),
        }

    tiers: dict[str, list[str]] = {}
    for rid, data in rows.items():
        sev = str(data["severity"])
        tiers.setdefault(sev, []).append(rid)

    baseline = {
        "created_from": str(run_root.resolve()),
        "row_count": len(rows),
        "tiers": tiers,
        "rows": rows,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"Wrote baseline with {len(rows)} PDFs → {out_path}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"Missing baseline {baseline_path}", file=sys.stderr)
        return 2

    current_path = Path(args.current)
    if not current_path.exists():
        print(f"Missing current report {current_path}", file=sys.stderr)
        return 2

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_rows: dict[str, dict] = baseline.get("rows") or {}

    cur = pd.read_csv(current_path).fillna("")
    if "run_id" not in cur.columns:
        print("Current CSV missing run_id", file=sys.stderr)
        return 2
    if "completed_at" in cur.columns:
        cur = cur.sort_values("completed_at")
    cur = cur.drop_duplicates(subset=["run_id"], keep="last").reset_index(drop=True)
    cur_map = {str(r["run_id"]): r for _, r in cur.iterrows()}

    failures: list[str] = []
    warnings = []

    for rid, b in baseline_rows.items():
        if rid not in cur_map:
            failures.append(f"{rid} ({b.get('pdf_name')}): missing in current run")
            continue
        row = cur_map[rid]
        c_doors = int(row.get("doors", 0) or 0)
        c_hw = int(row.get("hardware", 0) or 0)
        b_doors = int(b.get("doors", 0) or 0)
        b_hw = int(b.get("hardware", 0) or 0)

        if str(row.get("status")) != "ok" and str(b.get("status")) == "ok":
            failures.append(f"{rid}: status regressed to {row.get('status')}")

        if b.get("severity") == "ok":
            if c_doors < b_doors:
                failures.append(f"{rid}: doors {c_doors} < baseline {b_doors}")
            if c_hw < b_hw:
                failures.append(f"{rid}: hardware {c_hw} < baseline {b_hw}")

        if args.strict_high and rid in args.strict_high and b.get("severity") == "high":
            if (c_doors + c_hw) < (b_doors + b_hw):
                failures.append(
                    f"{rid} (high strict): total rows {c_doors + c_hw} < baseline {b_doors + b_hw}"
                )
            elif (c_doors + c_hw) > (b_doors + b_hw):
                warnings.append(f"{rid}: high-risk improved +{(c_doors + c_hw) - (b_doors + b_hw)} rows")

    if warnings:
        print("Improvements:")
        for w in warnings:
            print(f"  {w}")
    if failures:
        print("REGRESSION FAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    print("Golden regression check passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden regression for corpus CSVs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture", help="Build baseline JSON from a completed run_root")
    p_cap.add_argument("--run-root", required=True)
    p_cap.add_argument(
        "--output",
        default=str(APP_DIR / "qa_out" / "golden_baseline.json"),
        help="Where to write the baseline JSON",
    )
    p_cap.set_defaults(func=cmd_capture)

    p_check = sub.add_parser("check", help="Compare current CSV to baseline")
    p_check.add_argument("--baseline", required=True)
    p_check.add_argument(
        "--current",
        required=True,
        help="Usually deep_e2e_report_latest.csv from a new run",
    )
    p_check.add_argument(
        "--strict-high",
        nargs="*",
        default=[],
        help="run_id values that must not lose total row count vs baseline",
    )
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
