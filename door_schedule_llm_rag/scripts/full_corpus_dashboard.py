"""
Generate apple-to-apple QA artifacts for a full corpus run.

Inputs:
    qa_out/full_corpus_*/deep_e2e_report.csv
    qa_out/full_corpus_*/runs/<run_id>/extraction_results_llm.xlsx

Outputs:
    qa_out/full_corpus_*/visual_dashboard/apple_to_apple.html
    qa_out/full_corpus_*/triage_report.csv
    qa_out/full_corpus_*/triage_summary.json
    qa_out/full_corpus_*/visual_dashboard/screenshots/*.jpg
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

import pandas as pd


APP_DIR = Path(__file__).resolve().parent.parent


def _read_sheet(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    try:
        return pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()


def _render_page(pdf_path: Path, page_idx: int, image_path: Path, dpi: int = 130) -> bool:
    if image_path.exists():
        return True
    try:
        import fitz

        image_path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open(str(pdf_path))
        if page_idx >= len(doc):
            doc.close()
            return False
        pix = doc[page_idx].get_pixmap(dpi=dpi)
        pix.save(str(image_path))
        doc.close()
        return True
    except Exception:
        return False


def _safe_rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def _df_to_html(df: pd.DataFrame, columns: list[str], max_rows: int = 80) -> str:
    if df.empty:
        return "<p class='empty'>No rows extracted.</p>"
    display_cols = [c for c in columns if c in df.columns]
    if not display_cols:
        display_cols = list(df.columns[:10])
    out = df[display_cols].head(max_rows).copy()
    return out.to_html(index=False, escape=True, na_rep="")


def _score_row(row: pd.Series) -> tuple[str, list[str]]:
    issues: list[str] = []
    pdf_name = str(row["pdf_name"]).lower()
    hardware_only_name = any(word in pdf_name for word in ("hardware", "division 08", "division_08")) and "door schedule" not in pdf_name and "door & hardware" not in pdf_name and "door_hardware" not in pdf_name
    if row["status"] != "ok":
        issues.append("pipeline_error")
    if row["doors"] == 0 and row["hardware"] == 0:
        issues.append("zero_extract")
    elif row["doors"] == 0 and not hardware_only_name:
        issues.append("no_doors")
    elif row["hardware"] == 0 and "hardware" in pdf_name:
        issues.append("no_hardware")
    if row.get("duplicate_doors", 0) > 0:
        issues.append("duplicate_doors")
    if row.get("doors", 0) > 0:
        if row.get("missing_width", 0) / max(row["doors"], 1) > 0.5:
            issues.append("missing_width_gt_50pct")
        if row.get("missing_height", 0) / max(row["doors"], 1) > 0.5:
            issues.append("missing_height_gt_50pct")
        if row.get("missing_hw_set", 0) / max(row["doors"], 1) > 0.8:
            issues.append("missing_hw_set_gt_80pct")

    severity = "ok"
    if any(i in issues for i in ("pipeline_error", "zero_extract", "no_doors")):
        severity = "high"
    elif issues:
        severity = "medium"
    return severity, issues


def _failure_taxonomy(row: pd.Series, issues: list[str]) -> list[str]:
    """Map QA symptoms to the production failure taxonomy used for review."""
    taxonomy: list[str] = []
    issue_set = set(issues)
    name = str(row.get("pdf_name", "")).lower()

    if "pipeline_error" in issue_set:
        taxonomy.append("table detection failure")
    if "zero_extract" in issue_set or "no_doors" in issue_set:
        taxonomy.append("table detection failure")
        if int(row.get("crop_count", 0) or 0) > 0:
            taxonomy.append("wrong page classification")
        else:
            taxonomy.append("OCR failure")
    if "no_hardware" in issue_set and "hardware" in name:
        taxonomy.append("bad hardware-set join")
        taxonomy.append("bad schema mapping")
    if "duplicate_doors" in issue_set:
        taxonomy.append("duplicate record")
    if "missing_width_gt_50pct" in issue_set or "missing_height_gt_50pct" in issue_set:
        taxonomy.append("unit / dimension normalization issue")
        taxonomy.append("bad schema mapping")
    if "missing_hw_set_gt_80pct" in issue_set:
        taxonomy.append("bad hardware-set join")
    if int(row.get("crop_rescue_attempt_pages", 0) or 0) > 0 and int(row.get("crop_door_added", 0) or 0) + int(row.get("crop_hw_added", 0) or 0) == 0:
        taxonomy.append("low-confidence skip")
    if int(row.get("crop_count", 0) or 0) > 0 and int(row.get("doors", 0) or 0) == 0 and int(row.get("hardware", 0) or 0) == 0:
        taxonomy.append("OCR failure")
        taxonomy.append("rotated text failure")
    if int(row.get("duplicate_doors", 0) or 0) == 0 and int(row.get("doors", 0) or 0) > 0 and ("missing_width_gt_50pct" in issue_set or "missing_height_gt_50pct" in issue_set):
        taxonomy.append("merged-cell failure")
        taxonomy.append("row segmentation failure")
    if int(row.get("hardware", 0) or 0) > 0 and int(row.get("doors", 0) or 0) == 0 and "hardware" not in name:
        taxonomy.append("wrong page classification")

    return list(dict.fromkeys(taxonomy))


def build_artifacts(run_root: Path, max_pages_per_pdf: int = 20) -> None:
    report_path = run_root / "deep_e2e_report.csv"
    if not report_path.exists():
        raise FileNotFoundError(report_path)

    report = pd.read_csv(report_path).fillna("")
    if "completed_at" in report.columns:
        report = report.sort_values("completed_at")
    report = report.drop_duplicates(subset=["run_id"], keep="last").reset_index(drop=True)
    latest_report_path = run_root / "deep_e2e_report_latest.csv"
    report.to_csv(latest_report_path, index=False)
    triage_rows = []
    dashboard_dir = run_root / "visual_dashboard"
    shots_dir = dashboard_dir / "screenshots"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []
    total_rendered = 0

    for _, row in report.iterrows():
        severity, issues = _score_row(row)
        taxonomy = _failure_taxonomy(row, issues)
        triage_row = row.to_dict()
        triage_row["severity"] = severity
        triage_row["issues"] = ";".join(issues)
        triage_row["failure_taxonomy"] = ";".join(taxonomy)
        triage_rows.append(triage_row)

        pdf_path = Path(str(row["pdf_path"]))
        output_dir = Path(str(row["output_dir"]))
        excel_path = output_dir / "extraction_results_llm.xlsx"
        doors = _read_sheet(excel_path, "Door Schedule")
        hardware = _read_sheet(excel_path, "Hardware Components")

        page_candidates: set[int] = set()
        if not doors.empty and "page" in doors.columns:
            page_candidates.update(int(p) for p in doors["page"].dropna().unique() if str(p).strip())
        if not hardware.empty and "page" in hardware.columns:
            page_candidates.update(int(p) for p in hardware["page"].dropna().unique() if str(p).strip())
        if not page_candidates:
            page_candidates.add(1)

        page_sections = []
        for page_num in sorted(page_candidates)[:max_pages_per_pdf]:
            page_idx = max(0, int(page_num) - 1)
            shot_path = shots_dir / f"{row['run_id']}_p{page_num}.jpg"
            rendered = _render_page(pdf_path, page_idx, shot_path)
            if not rendered:
                continue
            total_rendered += 1
            page_doors = doors[doors["page"] == page_num] if not doors.empty and "page" in doors.columns else doors
            page_hw = hardware[hardware["page"] == page_num] if not hardware.empty and "page" in hardware.columns else hardware
            rel_img = _safe_rel(shot_path, dashboard_dir)
            page_sections.append(
                f"""
                <section class="page">
                  <h3>Page {page_num}: {len(page_doors)} doors, {len(page_hw)} hardware rows</h3>
                  <div class="split">
                    <div><img src="{html.escape(rel_img)}" alt="PDF page {page_num}"></div>
                    <div>
                      <h4>Doors</h4>
                      {_df_to_html(page_doors, ["door_number", "from_room", "room_name", "door_width", "door_height", "door_material", "frame_material", "hardware_set", "fire_rating", "remarks"])}
                      <h4>Hardware</h4>
                      {_df_to_html(page_hw, ["hardware_set_id", "hardware_set_name", "qty", "unit", "description", "catalog_number", "finish_code", "manufacturer_code"])}
                    </div>
                  </div>
                </section>
                """
            )

        cards.append(
            f"""
            <article class="card {severity}">
              <h2>{html.escape(str(row['pdf_name']))}</h2>
              <p><b>Run:</b> {html.escape(str(row['run_id']))}</p>
              <p><b>Status:</b> {html.escape(str(row['status']))} | <b>Severity:</b> {severity} | <b>Issues:</b> {html.escape('; '.join(issues) or 'none')}</p>
              <p><b>Failure Taxonomy:</b> {html.escape('; '.join(taxonomy) or 'none')}</p>
              <p><b>Counts:</b> {row['doors']} doors, {row['hardware']} hardware rows, {row['pages']} pages, {row['elapsed_s']}s</p>
              <p><b>Crop Rescue:</b> attempted on {row.get('crop_rescue_attempt_pages', 0)} pages, added rows on {row.get('crop_rescue_pages', 0)} pages, +{row.get('crop_door_added', 0)} doors, +{row.get('crop_hw_added', 0)} hardware rows ({row.get('crop_count', 0)} crops detected)</p>
              <p><b>PDF:</b> {html.escape(str(row['pdf_path']))}</p>
              {''.join(page_sections)}
            </article>
            """
        )

    triage = pd.DataFrame(triage_rows)
    triage_path = run_root / "triage_report.csv"
    triage.to_csv(triage_path, index=False)
    summary = {
        "pdfs": int(len(triage)),
        "status_counts": triage["status"].value_counts().to_dict() if not triage.empty else {},
        "severity_counts": triage["severity"].value_counts().to_dict() if not triage.empty else {},
        "doors": int(triage["doors"].sum()) if "doors" in triage.columns else 0,
        "hardware": int(triage["hardware"].sum()) if "hardware" in triage.columns else 0,
        "crop_count": int(triage["crop_count"].sum()) if "crop_count" in triage.columns else 0,
        "crop_rescue_attempt_pages": int(triage["crop_rescue_attempt_pages"].sum()) if "crop_rescue_attempt_pages" in triage.columns else 0,
        "crop_rescue_pages": int(triage["crop_rescue_pages"].sum()) if "crop_rescue_pages" in triage.columns else 0,
        "crop_door_added": int(triage["crop_door_added"].sum()) if "crop_door_added" in triage.columns else 0,
        "crop_hw_added": int(triage["crop_hw_added"].sum()) if "crop_hw_added" in triage.columns else 0,
        "pages_rendered": total_rendered,
    }
    if "failure_taxonomy" in triage.columns and not triage.empty:
        taxonomy_counts: dict[str, int] = {}
        for value in triage["failure_taxonomy"].fillna(""):
            for item in str(value).split(";"):
                item = item.strip()
                if item:
                    taxonomy_counts[item] = taxonomy_counts.get(item, 0) + 1
        summary["failure_taxonomy_counts"] = taxonomy_counts
    (run_root / "triage_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Full Corpus Apple-to-Apple QA</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:24px; }}
h1 {{ color:#38bdf8; }}
.summary, .card {{ background:#1e293b; border:1px solid #334155; border-radius:12px; padding:18px; margin:18px 0; }}
.card.high {{ border-left:6px solid #ef4444; }}
.card.medium {{ border-left:6px solid #f59e0b; }}
.card.ok {{ border-left:6px solid #22c55e; }}
.split {{ display:grid; grid-template-columns: minmax(360px, 1fr) minmax(360px, 1fr); gap:18px; align-items:start; }}
img {{ max-width:100%; border:1px solid #475569; border-radius:8px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; margin-bottom:16px; }}
th,td {{ border-bottom:1px solid #334155; padding:5px; vertical-align:top; }}
th {{ color:#93c5fd; text-align:left; position:sticky; top:0; background:#0f172a; }}
.empty {{ color:#f87171; }}
.page {{ border-top:1px solid #334155; margin-top:16px; padding-top:12px; }}
</style>
</head>
<body>
<h1>Full Corpus Apple-to-Apple QA</h1>
<div class="summary"><pre>{html.escape(json.dumps(summary, indent=2))}</pre></div>
{''.join(cards)}
</body>
</html>
"""
    html_path = dashboard_dir / "apple_to_apple.html"
    html_path.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {triage_path}")
    print(f"Wrote {html_path}")
    print(json.dumps(summary, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--max-pages-per-pdf", type=int, default=20)
    args = parser.parse_args()
    build_artifacts(Path(args.run_root), max_pages_per_pdf=args.max_pages_per_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
