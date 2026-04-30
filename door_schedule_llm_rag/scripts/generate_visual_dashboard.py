"""
Apple-to-Apple Visual Audit Dashboard Generator.

Renders every relevant page of every processed PDF as a high-res screenshot
alongside the pipeline's extracted tabular data. Outputs a self-contained
HTML file that can be opened in any browser for rapid human QA.

Usage:
    python scripts/generate_visual_dashboard.py

Output:
    qa_out/visual_dashboard/apple_to_apple.html
"""
import sys
import base64
import logging
from pathlib import Path
from datetime import datetime

# Fix path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import fitz  # PyMuPDF
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("dashboard")

BASE_DIR = Path(__file__).resolve().parent.parent
QA_DIR = BASE_DIR / "qa_out" / "deep_e2e"
DASH_DIR = BASE_DIR / "qa_out" / "visual_dashboard"
EDGE_LOG = BASE_DIR / "docs" / "EDGE_CASE_LOG.md"


# ══════════════════════════════════════════════════════════════════
#  PDF Page Rendering
# ══════════════════════════════════════════════════════════════════

def render_page_b64(pdf_path: Path, page_num: int, dpi: int = 150) -> str:
    """Render a single PDF page to a base64-encoded JPEG."""
    try:
        doc = fitz.open(str(pdf_path))
        if page_num >= len(doc):
            doc.close()
            return ""
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("jpeg")
        doc.close()
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        log.warning("Render fail %s p%d: %s", pdf_path.name, page_num, e)
        return ""


def get_page_count(pdf_path: Path) -> int:
    try:
        doc = fitz.open(str(pdf_path))
        n = len(doc)
        doc.close()
        return n
    except:
        return 0


# ══════════════════════════════════════════════════════════════════
#  Edge Case Auto-Logging
# ══════════════════════════════════════════════════════════════════

def log_edge_case(project_id: str, pdf_name: str, page_num: int, issue: str):
    """Append an auto-detected edge-case to the EDGE_CASE_LOG."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"""
### Auto-Detected: {project_id} / Page {page_num + 1}
- **PDF Name:** `{pdf_name}`
- **Timestamp:** {now}
- **Visual Anomaly:** {issue}
- **Resolution Needed:** Pending human review via Apple-to-Apple Dashboard.

"""
    try:
        with open(EDGE_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        log.warning("Could not log edge case: %s", e)


# ══════════════════════════════════════════════════════════════════
#  HTML Dashboard Generation
# ══════════════════════════════════════════════════════════════════

HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple-to-Apple Visual Audit Dashboard</title>
    <style>
        :root { --bg: #0f172a; --surface: #1e293b; --border: #334155; --text: #f8fafc; --muted: #94a3b8; --accent: #38bdf8; --green: #4ade80; --pink: #f472b6; --red: #ef4444; --orange: #fb923c; }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); padding: 20px; }
        h1 { text-align: center; color: var(--accent); font-size: 28px; margin-bottom: 5px; }
        .subtitle { text-align: center; color: var(--muted); margin-bottom: 30px; font-size: 14px; }
        .stats-bar { display: flex; justify-content: center; gap: 30px; margin-bottom: 40px; flex-wrap: wrap; }
        .stat { background: var(--surface); padding: 15px 25px; border-radius: 10px; text-align: center; }
        .stat .num { font-size: 28px; font-weight: 700; color: var(--accent); }
        .stat .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
        .project-card { background: var(--surface); border-radius: 12px; margin-bottom: 50px; padding: 25px; border: 1px solid var(--border); }
        .project-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap:wrap; }
        .project-header h2 { color: var(--accent); font-size: 20px; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 5px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .badge-ok { background: #064e3b; color: var(--green); }
        .badge-warn { background: #78350f; color: var(--orange); }
        .badge-err { background: #7f1d1d; color: var(--red); }
        .page-section { margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border); }
        .page-section h3 { color: var(--pink); font-size: 16px; margin-bottom: 10px; }
        .split { display: flex; gap: 20px; }
        .split .col { flex: 1; min-width: 0; overflow: auto; max-height: 700px; }
        .split img { width: 100%; border-radius: 8px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }
        th { background: var(--bg); color: var(--muted); padding: 8px 6px; text-align: left; position: sticky; top: 0; z-index: 1; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
        td { padding: 6px; border-bottom: 1px solid var(--border); color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
        tr:hover td { background: rgba(56,189,248,0.05); }
        .empty-note { color: var(--red); font-style: italic; padding: 20px; }
        .toggle-btn { background: var(--border); color: var(--text); border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .toggle-btn:hover { background: var(--accent); color: var(--bg); }
        .collapsed { display: none; }
        .summary-table { margin: 20px auto; max-width: 900px; }
        .nav { position: fixed; top: 20px; right: 20px; z-index: 100; }
        .nav a { display: block; color: var(--accent); font-size: 12px; margin-bottom: 4px; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
    </style>
    <script>
        function toggleSection(id) {
            var el = document.getElementById(id);
            el.classList.toggle('collapsed');
        }
    </script>
</head>
<body>
    <h1>🔍 Apple-to-Apple Visual Audit Dashboard</h1>
    <p class="subtitle">Auto-generated at {timestamp} — Scroll to visually compare PDF layouts vs. extracted data</p>
"""

HTML_FOOTER = """
</body>
</html>
"""


def df_to_html(df: pd.DataFrame, max_rows: int = 50) -> str:
    """Convert a DataFrame to a styled HTML table string."""
    if df.empty:
        return '<p class="empty-note">⚠️ No data extracted for this category.</p>'
    
    # Drop columns that are always empty or not useful for display
    display_df = df.dropna(axis=1, how='all').head(max_rows)
    return display_df.to_html(index=False, classes="data", na_rep="—", escape=True)


def build_dashboard():
    """Main dashboard builder."""
    DASH_DIR.mkdir(parents=True, exist_ok=True)

    # Find all tested projects
    if not QA_DIR.exists():
        log.error("QA output directory not found: %s. Run the benchmark first!", QA_DIR)
        return

    report_path = QA_DIR / "deep_e2e_report.csv"
    if not report_path.exists():
        log.error("Benchmark report not found: %s. Run the benchmark first!", report_path)
        return

    report_df = pd.read_csv(report_path)
    if "run_id" not in report_df.columns:
        log.error(
            "Benchmark report is from the old non-unique format. "
            "Re-run tests/deep_e2e_benchmark.py before generating this dashboard."
        )
        return

    projects = report_df.to_dict("records")

    log.info("Found %d tested PDF runs. Building dashboard...", len(projects))

    total_doors = 0
    total_hw = 0
    total_pages_rendered = 0
    edge_cases_found = 0

    project_cards_html = ""

    for proj_idx, row in enumerate(projects):
        run_id = str(row.get("run_id") or "")
        project_id = str(row.get("project_id") or run_id)
        excel_path = Path(str(row.get("output_dir") or (QA_DIR / run_id))) / "extraction_results_llm.xlsx"
        pdf_path = Path(str(row.get("pdf_path") or ""))
        if not pdf_path or not pdf_path.exists():
            log.warning("No source PDF found for run: %s", run_id)
            continue
        if not excel_path.exists():
            log.warning("No extraction workbook found for run: %s", run_id)
            continue

        log.info("[%d/%d] Processing: %s (%s)", proj_idx + 1, len(projects), run_id, pdf_path.name)

        # Load extraction results
        try:
            door_df = pd.read_excel(excel_path, sheet_name="Door Schedule")
        except:
            door_df = pd.DataFrame()

        try:
            hw_df = pd.read_excel(excel_path, sheet_name="Hardware Components")
        except:
            hw_df = pd.DataFrame()

        n_doors = len(door_df)
        n_hw = len(hw_df)
        total_doors += n_doors
        total_hw += n_hw

        # Determine status badge
        status = str(row.get("status") or "")
        if n_doors == 0 and n_hw == 0:
            badge = '<span class="badge badge-err">ZERO EXTRACT</span>'
            edge_cases_found += 1
            log_edge_case(project_id, pdf_path.name, 0, "Zero doors AND zero hardware extracted.")
        elif n_doors == 0:
            badge = '<span class="badge badge-warn">HW ONLY</span>'
        elif n_hw == 0:
            badge = '<span class="badge badge-warn">DOORS ONLY</span>'
        else:
            badge = '<span class="badge badge-ok">OK</span>'

        # Get total pages
        n_pages = get_page_count(pdf_path)

        # Build per-page sections
        pages_html = ""
        for page_idx in range(min(n_pages, 20)):  # Cap at 20 pages per PDF for dashboard size
            # Filter extracted data for this page
            page_doors = door_df[door_df["page"] == page_idx + 1] if "page" in door_df.columns and not door_df.empty else pd.DataFrame()
            page_hw = hw_df[hw_df["page"] == page_idx + 1] if "page" in hw_df.columns and not hw_df.empty else pd.DataFrame()

            # Skip pages with zero data AND pages that likely aren't schedule pages
            if page_doors.empty and page_hw.empty:
                continue

            total_pages_rendered += 1

            # Render PDF page image
            b64_img = render_page_b64(pdf_path, page_idx, dpi=150)
            if not b64_img:
                continue

            section_id = f"proj_{proj_idx}_page_{page_idx}"

            pages_html += f"""
            <div class="page-section">
                <h3>📄 Page {page_idx + 1} 
                    <button class="toggle-btn" onclick="toggleSection('{section_id}')">Toggle</button>
                    <span style="color:var(--muted); font-size:12px; margin-left:10px;">
                        {len(page_doors)} doors, {len(page_hw)} HW items
                    </span>
                </h3>
                <div id="{section_id}" class="split">
                    <div class="col">
                        <h4 style="color:var(--pink); margin-bottom:8px;">PDF Source (Ground Truth)</h4>
                        <img src="data:image/jpeg;base64,{b64_img}" alt="Page {page_idx + 1}">
                    </div>
                    <div class="col">
                        <h4 style="color:var(--green); margin-bottom:8px;">Pipeline Extraction</h4>
            """

            if not page_doors.empty:
                pages_html += f"<h5 style='margin-top:10px;'>🚪 Doors ({len(page_doors)})</h5>"
                pages_html += df_to_html(page_doors)

            if not page_hw.empty:
                pages_html += f"<h5 style='margin-top:15px;'>⚙️ Hardware ({len(page_hw)})</h5>"
                pages_html += df_to_html(page_hw)

            if page_doors.empty and page_hw.empty:
                pages_html += '<p class="empty-note">No data extracted from this page.</p>'

            pages_html += """
                    </div>
                </div>
            </div>
            """

        # Only add project card if there are pages to show
        if not pages_html:
            # Still add a minimal card for zero-extract projects
            if n_doors == 0 and n_hw == 0:
                b64_img = render_page_b64(pdf_path, 0, dpi=120)
                project_cards_html += f"""
                <div class="project-card" id="project_{proj_idx}">
                    <div class="project-header">
                        <h2>📦 {run_id}</h2>
                        {badge}
                    </div>
                    <p style="color:var(--muted);">{project_id} · {pdf_path.name} — {n_pages} pages · {status}</p>
                    <div class="split" style="margin-top:15px;">
                        <div class="col">
                            <img src="data:image/jpeg;base64,{b64_img}" alt="Page 1" style="max-height:400px;">
                        </div>
                        <div class="col">
                            <p class="empty-note">⚠️ ZERO EXTRACT — No doors or hardware were recovered from this document.</p>
                        </div>
                    </div>
                </div>
                """
            continue

        project_cards_html += f"""
        <div class="project-card" id="project_{proj_idx}">
            <div class="project-header">
                <h2>📦 {run_id}</h2>
                <div>
                    {badge}
                    <span style="color:var(--muted); font-size:13px; margin-left:15px;">
                        {project_id} · {n_doors} doors · {n_hw} HW items · {n_pages} pages · {status}
                    </span>
                </div>
            </div>
            <p style="color:var(--muted); font-size:13px;">{pdf_path.name}</p>
            {pages_html}
        </div>
        """

    # Build stats bar
    stats_html = f"""
    <div class="stats-bar">
        <div class="stat"><div class="num">{len(projects)}</div><div class="label">PDF Runs</div></div>
        <div class="stat"><div class="num">{total_doors}</div><div class="label">Total Doors</div></div>
        <div class="stat"><div class="num">{total_hw}</div><div class="label">HW Components</div></div>
        <div class="stat"><div class="num">{total_pages_rendered}</div><div class="label">Pages Audited</div></div>
        <div class="stat"><div class="num">{edge_cases_found}</div><div class="label">Edge Cases</div></div>
    </div>
    """

    # Assemble final HTML
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = HTML_HEADER.replace("{timestamp}", timestamp)
    html += stats_html
    html += project_cards_html
    html += HTML_FOOTER

    # Write output
    output_path = DASH_DIR / "apple_to_apple.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    log.info("=" * 60)
    log.info("Dashboard generated successfully!")
    log.info("  PDF Runs:    %d", len(projects))
    log.info("  Total Doors: %d", total_doors)
    log.info("  Total HW:    %d", total_hw)
    log.info("  Pages:       %d", total_pages_rendered)
    log.info("  Edge Cases:  %d", edge_cases_found)
    log.info("  Output:      %s", output_path.resolve())
    log.info("=" * 60)


if __name__ == "__main__":
    build_dashboard()
