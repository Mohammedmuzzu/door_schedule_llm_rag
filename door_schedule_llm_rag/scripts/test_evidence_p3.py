"""Test: Check evidence from actual Project 3 PDF text."""
import sys, os
sys.path.insert(0, ".")
from pathlib import Path
from page_extractor import extract_structured_page
from page_evidence import collect, confidence_score

pdf_path = Path(r"c:\Users\muzaf\my_lab\sushmita_proj\pdfs\project 3_lessthan10door.pdf")
content, page_type, is_cont, b64img = extract_structured_page(pdf_path, 0)
print(f"Page type: {page_type}")
print(f"Content length: {len(content)}")
print(f"Has image: {b64img is not None}")

ev = collect(content)
print(f"\nEvidence:")
print(f"  real_door_numbers: {ev.real_door_numbers}")
print(f"  dimensions: {ev.dimensions}")
print(f"  row_lines: {ev.row_lines}")
print(f"  expected_door_rows: {ev.expected_door_rows()}")
print(f"  hw_set_headers: {ev.hw_set_headers}")
print(f"  hw_components: {ev.hw_components}")
print(f"  expected_hw_sets: {ev.expected_hw_sets()}")
print(f"  distinct_door_sample: {ev.distinct_door_sample}")
print(f"  confidence: {confidence_score(ev):.3f}")

# Simulate the rescue check
unique_doors = 6  # simulated extraction result
expected = ev.expected_door_rows()
print(f"\nRescue check: expected={expected}, unique={unique_doors}")
print(f"  3 <= {expected} < 15 and {unique_doors} > 0 and {unique_doors} < {expected}")
print(f"  Result: {3 <= expected < 15 and unique_doors > 0 and unique_doors < expected}")
