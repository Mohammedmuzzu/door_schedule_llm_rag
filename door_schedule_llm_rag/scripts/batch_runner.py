import os
import glob
import subprocess
import sys

out_dir = 'c:\\Users\\muzaf\\my_lab\\sushmita_proj\\door_schedule_llm_rag\\scratch_qa_full'
os.makedirs(out_dir, exist_ok=True)

all_pdfs = glob.glob('c:\\Users\\muzaf\\my_lab\\sushmita_proj\\pdfs\\**\\*.pdf', recursive=True)
all_pdfs = [p for p in all_pdfs if 'PRD' not in p.upper()]

chunk_size = 5
total_chunks = (len(all_pdfs) + chunk_size - 1) // chunk_size

# Write a tiny worker script
worker_script = os.path.join(os.path.dirname(__file__), "worker.py")
with open(worker_script, "w") as f:
    f.write("""
import sys
import os
import json
from pathlib import Path

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from pipeline import run_pipeline
from llm_extract import llm_config

llm_config.set('openai', 'gpt-4o-mini')

chunk_dir = sys.argv[1]
pdf_files = json.loads(sys.argv[2])

print(f"Worker starting chunk for {len(pdf_files)} files: {chunk_dir}")
run_pipeline(pdf_folder='.', output_dir=chunk_dir, pdf_files=pdf_files)
""")

import json

for i in range(total_chunks):
    chunk_files = all_pdfs[i*chunk_size : (i+1)*chunk_size]
    chunk_dir = os.path.join(out_dir, f'chunk_{i}')
    os.makedirs(chunk_dir, exist_ok=True)
    
    if os.path.exists(os.path.join(chunk_dir, 'door_schedule_llm.csv')):
        print(f'Chunk {i} already processed.')
        continue
        
    print(f'\\n--- Spawning Subprocess for Chunk {i}/{total_chunks} ---')
    # Run the worker script with the current chunk
    python_exe = "c:\\\\Users\\\\muzaf\\\\my_lab\\\\computervision\\\\Scripts\\\\python.exe"
    subprocess.run([python_exe, worker_script, chunk_dir, json.dumps(chunk_files)])
