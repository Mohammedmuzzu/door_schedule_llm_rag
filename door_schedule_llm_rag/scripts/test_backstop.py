"""Test backstop logic against failing PDFs"""
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz

def check_backstop(name, pdf_path):
    doc = fitz.open(pdf_path)
    txt = doc[0].get_text()
    doc.close()
    upper = txt.upper()
    
    print(f'\n=== {name} ===')
    print(f'Fitz text len: {len(txt)}')
    
    # Check schedule keywords (same as backstop)
    for kw in ("DOOR SCHEDULE", "DOOR NO", "DOOR NUMBER", "DOOR MARK", 
               "HARDWARE SET", "HW SET", "HDWR SET", "FRAME TYPE",
               "FIRE RATING", "DOOR TYPE"):
        if kw in upper:
            print(f'  Schedule KW: {kw} ✓')
    
    # Door number patterns
    door_nums = re.findall(r'\b\d{3,4}[A-Za-z]?\b', txt)
    real_doors = [n for n in door_nums if not (1900 <= int(re.match(r'\d+', n).group()) <= 2099)]
    print(f'  Door-like numbers: {len(real_doors)} -> {real_doors[:10]}')
    
    # Dimension patterns
    has_dims = bool(re.search(r"\d+['\u2019]\s*-?\s*\d+\"", txt))
    print(f'  Has dimensions: {has_dims}')
    
    # Hardware keywords
    for kw in ('HINGE', 'CLOSER', 'LOCKSET', 'DEADBOLT', 'THRESHOLD', 'DOOR STOP', 'KICK PLATE'):
        if kw in upper:
            print(f'  HW keyword: {kw} ✓')
    
    # Check the ACTUAL CONTENT that pdfplumber sends (which is what the backstop sees)
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        plumber_text = page.extract_text() or ''
        tables = page.extract_tables()
        plumber_tables_md = ''
        for t in tables:
            for row in t:
                plumber_tables_md += ' | '.join(str(c or '') for c in row) + '\n'
        
        combined = plumber_text + plumber_tables_md
        combined_upper = combined.upper()
        
        print(f'\n  PDFPLUMBER text: {len(plumber_text)} chars')
        print(f'  PDFPLUMBER tables: {len(tables)} tables, {len(plumber_tables_md)} chars combined')
        
        # Re-check backstop against combined pdfplumber content
        has_schedule_kw2 = any(kw in combined_upper for kw in (
            "DOOR SCHEDULE", "DOOR NO", "DOOR NUMBER", "DOOR MARK", 
            "HARDWARE SET", "HW SET", "HDWR SET", "FRAME TYPE",
            "FIRE RATING", "DOOR TYPE",
        ))
        door_nums2 = re.findall(r'\b\d{3,4}[A-Za-z]?\b', combined)
        real_doors2 = [n for n in door_nums2 if not (1900 <= int(re.match(r'\d+', n).group()) <= 2099)]
        has_dims2 = bool(re.search(r"\d+['\u2019]\s*-?\s*\d+\"", combined))
        
        print(f'  Combined schedule KW: {has_schedule_kw2}')
        print(f'  Combined door nums: {len(real_doors2)}')
        print(f'  Combined dimensions: {has_dims2}')
        
        # Will backstop fire?
        has_hw2 = any(kw in combined_upper for kw in ("HINGE", "CLOSER", "LOCKSET", "DEADBOLT", "THRESHOLD", "DOOR STOP", "KICK PLATE"))
        would_fire = (has_schedule_kw2 and (len(real_doors2) >= 2 or has_dims2)) or \
                     (len(real_doors2) >= 5 and has_dims2) or \
                     (len(real_doors2) >= 3 and has_hw2)
        print(f'  BACKSTOP WOULD FIRE: {would_fire}')

# Test the 3 machine-readable failures
check_backstop("Project 13", r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 13\Door Schedule & Hardware.pdf')
check_backstop("Project 16", r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 16\Door Schedule.pdf')
check_backstop("P17/A0.03", r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -17_lessthan10doors\Project -17\A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf')
