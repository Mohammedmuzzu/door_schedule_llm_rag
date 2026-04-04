import os
import sys
from pathlib import Path
import logging
import argparse

# Enable UTF-8 encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from config import PDF_FOLDER, OUTPUT_DIR
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True,
)
logger = logging.getLogger("run_bulk")

def main():
    parser = argparse.ArgumentParser(description="Bulk PDF Extraction")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of PDFs processed")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG context injection")
    args = parser.parse_args()

    print("==================================================")
    print("🚀 Initializing Bulk Extraction Pipeline")
    print("⏳ Loading ML models (this may take up to 30 seconds)...")
    print("==================================================")
    
    # Deferred import so the user sees the boot message before torch blocks the thread
    from pipeline import run_pipeline

    logger.info("Starting bulk extraction process over %s...", PDF_FOLDER)
    
    df_doors, df_comp = run_pipeline(
        pdf_folder=PDF_FOLDER,
        output_dir=OUTPUT_DIR,
        max_pdfs=args.limit,
        use_rag=not args.no_rag,
    )
    
    logger.info("Bulk extraction finished.")
    logger.info(f"Total Doors rows: {len(df_doors)}")
    logger.info(f"Total Component rows: {len(df_comp)}")
    logger.info(f"Output saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
