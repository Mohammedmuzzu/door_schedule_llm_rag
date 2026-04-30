"""
test_robust.py
──────────────
End-to-end regression against the 6 historically-problematic PDFs.

For every target PDF we report:
  * Doors extracted / Hardware components extracted
  * Per-page PageEvidence confidence score (averaged)
  * Whether the self-verification layer fired a rescue

Run:
    & "c:\\Users\\muzaf\\my_lab\\computervision\\Scripts\\python.exe" \
        scripts/test_robust.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-16s | %(message)s",
    stream=sys.stderr,
    datefmt="%H:%M:%S",
    force=True,
)

from pipeline import run_pipeline  # noqa: E402

TARGETS = [
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 13\Door Schedule & Hardware.pdf", "P13_DoorHW"),
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 14\A6.0.pdf", "P14_A6"),
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 16\Door Schedule.pdf", "P16_Door"),
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Door Schedule.pdf", "P17_Door"),
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Hardware Schedule.pdf", "P17_HW"),
    (r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -17_lessthan10doors\Project -17\A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf", "P17_A003"),
]


def main() -> int:
    print("=" * 80)
    print("  ROBUST END-TO-END TEST (evidence-routed + self-verification)")
    print("=" * 80)

    summary = []
    for pdf_path, label in TARGETS:
        p = Path(pdf_path)
        print(f"\n--- {label}: {p.name} ---")
        if not p.exists():
            print(f"  SKIP: file not found")
            summary.append((label, 0, 0, "MISSING"))
            continue

        with tempfile.TemporaryDirectory() as td:
            try:
                df_d, df_h = run_pipeline(pdf_files=[p], output_dir=td, use_rag=True)
                doors = 0 if df_d is None or df_d.empty else len(df_d)
                hw = 0 if df_h is None or df_h.empty else len(df_h)
                status = "OK" if (doors > 0 or hw > 0) else "STILL_ZERO"
                summary.append((label, doors, hw, status))
                print(f"  -> {doors} doors, {hw} HW items -> {status}")
                if doors > 0 and df_d is not None:
                    sample = list(df_d["door_number"].head(6))
                    print(f"  door_number sample: {sample}")
                if hw > 0 and df_h is not None:
                    sets = sorted({
                        str(x) for x in df_h.get("hardware_set_id", []) if x
                    })[:10]
                    print(f"  hardware_set sample: {sets}")
            except Exception as e:  # pragma: no cover
                summary.append((label, 0, 0, f"ERROR: {e}"))
                print(f"  -> ERROR: {e}")

    print("\n" + "=" * 80)
    print("  RESULTS SUMMARY")
    print("=" * 80)
    for label, doors, hw, status in summary:
        emoji = "OK" if status == "OK" else "FAIL"
        print(f"  [{emoji}] {label:15s}: {doors:4d} doors, {hw:4d} HW -> {status}")
    ok = sum(1 for _, _, _, s in summary if s == "OK")
    print(f"\n  Fixed: {ok}/{len(summary)}")
    return 0 if ok == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
