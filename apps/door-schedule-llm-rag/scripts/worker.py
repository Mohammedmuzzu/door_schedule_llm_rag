
import sys
import os
import json
from pipeline import run_pipeline
from llm_extract import llm_config

llm_config.set('openai', 'gpt-4o-mini')

chunk_dir = sys.argv[1]
pdf_files = json.loads(sys.argv[2])

print(f"Worker starting chunk for {len(pdf_files)} files: {chunk_dir}")
run_pipeline(pdf_folder='.', output_dir=chunk_dir, pdf_files=pdf_files)
