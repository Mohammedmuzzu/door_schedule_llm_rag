import pdfplumber
from pathlib import Path

def dump_text():
    pdf_path = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\project 1_less10doors.pdf")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        print("===== TEXT =====")
        print(text)
        
if __name__ == "__main__":
    dump_text()
