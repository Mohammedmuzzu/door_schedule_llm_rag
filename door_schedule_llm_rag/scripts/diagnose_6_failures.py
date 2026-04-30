"""Diagnose the 6 ZERO_EXTRACT failures"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import fitz, pdfplumber

fails = [
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 13\Door Schedule & Hardware.pdf',
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 14\A6.0.pdf',
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 16\Door Schedule.pdf',
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Door Schedule.pdf',
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Hardware Schedule.pdf',
    r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -17_lessthan10doors\Project -17\A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf',
]

for pdf_path in fails:
    p = Path(pdf_path)
    sep = '=' * 80
    print(f'\n{sep}')
    print(f'  {p.parent.name} / {p.name}')
    print(sep)

    # PyMuPDF text
    doc = fitz.open(str(p))
    for i, page in enumerate(doc):
        txt = page.get_text()
        print(f'  Page {i+1}: fitz text = {len(txt)} chars')
        if len(txt) < 2000:
            print(f'  TEXT: {repr(txt[:500])}')
        else:
            print(f'  TEXT SAMPLE: {repr(txt[:300])}...')
    doc.close()

    # pdfplumber tables
    try:
        with pdfplumber.open(str(p)) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                plumber_text = page.extract_text() or ''
                print(f'  Page {i+1}: plumber tables = {len(tables)}, plumber text = {len(plumber_text)} chars')
                if tables:
                    for ti, t in enumerate(tables):
                        rows = len(t)
                        cols = len(t[0]) if t else 0
                        print(f'    Table {ti}: {rows} rows x {cols} cols')
                        for ri in range(min(3, rows)):
                            row_preview = [str(c)[:30] for c in (t[ri][:6] if len(t[ri]) > 6 else t[ri])]
                            print(f'      Row {ri}: {row_preview}')
                elif len(plumber_text) < 500:
                    print(f'  PLUMBER TEXT: {repr(plumber_text[:300])}')
    except Exception as e:
        print(f'  pdfplumber error: {e}')
    
    # img2table check
    try:
        from img2table.document import PDF as Img2TablePDF
        from img2table.ocr import TesseractOCR
        ocr = TesseractOCR(lang='eng')
        img_pdf = Img2TablePDF(str(p))
        tables = img_pdf.extract_tables(ocr=ocr, implicit_rows=True, implicit_columns=True, borderless_tables=True)
        for pg_idx, pg_tables in tables.items():
            if pg_tables:
                print(f'  img2table page {pg_idx}: {len(pg_tables)} tables')
                for ti, tbl in enumerate(pg_tables):
                    df = tbl.df
                    print(f'    Table {ti}: {df.shape[0]} rows x {df.shape[1]} cols')
                    if df.shape[0] > 0:
                        print(f'    Headers: {list(df.columns[:6])}')
                        print(f'    Row 0: {list(df.iloc[0][:6])}')
            else:
                print(f'  img2table page {pg_idx}: no tables found')
    except Exception as e:
        print(f'  img2table error: {e}')
