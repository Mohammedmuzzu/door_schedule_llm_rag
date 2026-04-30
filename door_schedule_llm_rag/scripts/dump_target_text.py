from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from page_extractor import extract_structured_page  # noqa: E402


TARGETS = [
    Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 62\A400_ DOOR WINDOW SCHEDULE Rev.1 markup.pdf"),
    Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 9\019 A602 DOOR HARDWARE SETS.PDF"),
]


def main() -> int:
    out_dir = Path("qa_out/target_text")
    out_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in TARGETS:
        text, page_type, is_continuation, _ = extract_structured_page(pdf_path, 0, max_chars=35000)
        out_path = out_dir / f"{pdf_path.stem[:80].replace(' ', '_')}.txt"
        out_path.write_text(text, encoding="utf-8", errors="replace")
        print(f"{pdf_path.name}: type={page_type} cont={is_continuation} len={len(text)} -> {out_path}")
        print(text[:1200].encode("ascii", "ignore").decode("ascii", "ignore"))
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
