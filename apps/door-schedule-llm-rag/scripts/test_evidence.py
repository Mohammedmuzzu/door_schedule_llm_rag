"""Quick test: check if evidence now counts small door numbers."""
import sys
sys.path.append(".")
from page_evidence import collect

# Simulated text snippet from Project 3 (has doors 01-07)
test_text = """
DOOR SCHEDULE
DOOR NUMBER  DESCRIPTION  SIZE  DOOR MATERIAL  TYPE  FINISH  FRAME MATERIAL  FINISH  HEAD  JAMB  SILL  FIRE RATING  HARDWARE  REMARKS
01  STORE FRONT ENTRY - EXISTING  3'-6" x 7'-0"  GLASS  A  EXISTING  ALUMINUM  FACTORY  ----  ----  ----  1
02  STORE FRONT ENTRY - EXISTING  3'-6" x 7'-0"  GLASS  A  EXISTING  ALUMINUM  FACTORY  ----  ----  ----  1
03  REAR EXIT - EXISTING  3'-6" x 7'-0"  ALUMINUM  B  EXISTING  ALUMINUM  FACTORY  ----  ----  ----  1
04  RESTROOM  3'-0" x 7'-0"  SOLID CORE  C  P-2  3/M4.0  4/M4.0  ----  ----  3  UNDERCUT 3/4"
05  RESTROOM 2  3'-0" x 7'-0"  SOLID CORE  C  P-2  3/M4.0  4/M4.0  ----  ----  3  UNDERCUT 3/4"
06  DRY STORAGE  3'-0" x 7'-0"  SOLID CORE  D  P-2  3/M4.0  4/M4.0  ----  ----  2  UNDERCUT 1/4"
07  DRY STORAGE  3'-0" x 7'-0"  SOLID CORE  D  P-2  3/M4.0  4/M4.0  ----  ----  2  UNDERCUT 3/4"
"""

ev = collect(test_text)
print(f"real_door_numbers: {ev.real_door_numbers}")
print(f"dimensions: {ev.dimensions}")
print(f"row_lines: {ev.row_lines}")
print(f"expected_door_rows: {ev.expected_door_rows()}")
print(f"distinct_door_sample: {ev.distinct_door_sample}")
print(f"is_door_schedule: {ev.is_door_schedule}")
