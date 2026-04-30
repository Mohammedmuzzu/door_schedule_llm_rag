from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import run_pipeline  # noqa: E402


TARGETS = [
    Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 62\A400_ DOOR WINDOW SCHEDULE Rev.1 markup.pdf"),
    Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 9\019 A602 DOOR HARDWARE SETS.PDF"),
    Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 28\Door & Hardware Schedule.pdf"),
]


def main() -> int:
    for pdf_path in TARGETS:
        print(f"\n--- {pdf_path}")
        t0 = time.time()
        with tempfile.TemporaryDirectory() as td:
            df_d, df_h = run_pipeline(pdf_files=[pdf_path], output_dir=td, use_rag=True)

        door_count = 0 if df_d is None or df_d.empty else len(df_d)
        hw_count = 0 if df_h is None or df_h.empty else len(df_h)
        print(f"RESULT {door_count} doors, {hw_count} hw, {time.time() - t0:.1f}s")
        if door_count and "door_number" in df_d.columns:
            print("door sample:", list(df_d["door_number"].astype(str).head(10)))
        if hw_count and "hardware_set_id" in df_h.columns:
            hw_sets = sorted({str(x) for x in df_h["hardware_set_id"].dropna()})[:12]
            print("hw set sample:", hw_sets)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
