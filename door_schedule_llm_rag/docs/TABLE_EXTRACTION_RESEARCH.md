# PDF Table Extraction: Research & Comparison

## Document Type: Door Schedule PDFs

- **Mixed layouts**: Bordered tables (door schedule), borderless text blocks (hardware descriptions)
- **Construction/architectural** PDFs with idiosyncratic formats
- **Some may be scanned** (OCR needed for those)

---

## Tool Comparison (2024–2025)

| Tool | Best For | Pros | Cons |
|------|----------|------|------|
| **pdfplumber** | Mixed layouts, borderless, fine control | Python-native, no Java, tunable (lines/text strategy), already validated | Borderless tables can be tricky; may over-segment |
| **Camelot** | Bordered (lattice), whitespace (stream) | High accuracy for lattice tables, built-in accuracy metrics, better cell alignment | Archived (atlanhq); requires OpenCV + Ghostscript; stream mode inconsistent on borderless |
| **Tabula** | Fast batch, consistent PDFs | Simple API | Requires Java; weak on borderless |
| **Layout-parser** | DL-based, complex layouts | Handles complex layouts, OCR | Heavy (PyTorch, models); overkill for digital PDFs |
| **Table Transformer (TATR)** | Complex layouts, merged cells, scanned | Best for difficult cases | Slow; GPU recommended; separate text extraction |
| **Unstructured** | General doc parsing | `partition_pdf`, hi_res strategy | Heavy deps (tesseract); better for scanned |

---

## Selection for Door Schedule Pipeline

### Primary: **pdfplumber**
- Already in use and validated on project 1
- Handles both bordered and borderless (text strategy)
- No extra system dependencies
- Fine-grained control for quirky layouts

### Optional: **Camelot** (lattice mode)
- Best for clearly bordered door schedule tables
- Better cell alignment when lines are present
- Use as fallback when pdfplumber tables are sparse or noisy

### Not chosen (for now)
- **Layout-parser / TATR**: Overkill for digital PDFs; add later if scanned PDFs become common
- **Unstructured**: Heavier; consider for OCR/scan strategy
- **Tabula**: Java dependency; pdfplumber + Camelot cover the use case

---

## Implementation: Multi-Backend Strategy

```
TABLE_EXTRACTION_BACKEND = "pdfplumber" | "camelot" | "auto"
```

- **pdfplumber**: Current behavior (lines → text strategy)
- **camelot**: Use Camelot lattice + stream for tables (when installed)
- **auto**: Try pdfplumber first; if tables are empty or poor quality, try Camelot

### Camelot Installation (optional)
```bash
pip install "camelot-py[cv]"
# Requires: OpenCV, Ghostscript on system
```

---

## References

- [Camelot vs others](https://github.com/atlanhq/camelot/wiki/Comparison-with-other-PDF-Table-Extraction-libraries-and-tools)
- [arXiv: PDF Parsing Tools Comparative Study](https://arxiv.org/abs/2410.09871)
- [pdfplumber table extraction](https://www.pdfplumber.com/can-pdfplumber-extract-tables-from-pdfs/)
- [Unstructured table extraction](https://docs.unstructured.io/examplecode/codesamples/apioss/table-extraction-from-pdf)
