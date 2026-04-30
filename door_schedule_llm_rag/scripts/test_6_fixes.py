"""Test the fixes against the 6 ZERO_EXTRACT failures"""
import sys, os, tempfile
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)-16s | %(message)s',
                    stream=sys.stderr, datefmt='%H:%M:%S', force=True)

from pathlib import Path
from pipeline import run_pipeline

fails = [
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 13\Door Schedule & Hardware.pdf', 'P13_DoorHW'),
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 14\A6.0.pdf', 'P14_A6'),
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 16\Door Schedule.pdf', 'P16_Door'),
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Door Schedule.pdf', 'P17_Door'),
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project - 17\Hardware Schedule.pdf', 'P17_HW'),
    (r'C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -17_lessthan10doors\Project -17\A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf', 'P17_A003'),
]

print('=' * 80)
print('  TESTING 6 ZERO_EXTRACT FIXES')
print('=' * 80)

results = []
for pdf_path, label in fails:
    p = Path(pdf_path)
    print(f'\n--- {label}: {p.name} ---')
    
    with tempfile.TemporaryDirectory() as td:
        try:
            df_d, df_h = run_pipeline(pdf_files=[p], output_dir=td, use_rag=True)
            doors = len(df_d) if not df_d.empty else 0
            hw = len(df_h) if not df_h.empty else 0
            status = 'OK' if (doors > 0 or hw > 0) else 'STILL_ZERO'
            results.append((label, doors, hw, status))
            print(f'  -> {doors} doors, {hw} HW items -> {status}')
            if doors > 0:
                print(f'  Door nums: {list(df_d["door_number"].head(5))}')
        except Exception as e:
            results.append((label, 0, 0, f'ERROR: {e}'))
            print(f'  -> ERROR: {e}')

print('\n' + '=' * 80)
print('  RESULTS SUMMARY')
print('=' * 80)
for label, doors, hw, status in results:
    emoji = '✓' if status == 'OK' else '✗'
    print(f'  {emoji} {label:15s}: {doors:3d} doors, {hw:3d} HW -> {status}')
fixed = sum(1 for _, _, _, s in results if s == 'OK')
print(f'\n  Fixed: {fixed}/{len(results)}')
