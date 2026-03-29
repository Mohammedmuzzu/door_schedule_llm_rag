"""
Entry point: seed RAG (if needed), then run LLM extraction pipeline.

Usage:
  python run_llm_pipeline.py                 # all PDFs in default directory
  python run_llm_pipeline.py --max 3         # process first 3 PDFs
  python run_llm_pipeline.py --file path.pdf # process exactly ONE specific PDF
  python run_llm_pipeline.py --pdf-dir PATH  # custom PDF folder
"""
import os
import sys

# Force unbuffered output so logs appear immediately in PowerShell
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import PDF_FOLDER, OUTPUT_DIR


def check_ollama():
    """Check if Ollama is running and has a model available."""
    import requests
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL

    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        model_base = OLLAMA_MODEL.split(":")[0]

        if not any(model_base in m for m in models):
            print(f"Model '{OLLAMA_MODEL}' not found. Available: {models}")
            print(f"Pulling {OLLAMA_MODEL}...")
            import subprocess
            subprocess.run(["ollama", "pull", OLLAMA_MODEL], check=True)

        print(f"OK: Ollama running with model '{OLLAMA_MODEL}'")
        return True

    except requests.exceptions.ConnectionError:
        print("ERR: Ollama is not running. Please start it:")
        print("  1. Install from https://ollama.com")
        print("  2. Run: ollama serve")
        print(f"  3. Run: ollama pull {OLLAMA_MODEL}")
        return False
    except Exception as e:
        print(f"ERR: Ollama check failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="Door Schedule LLM + RAG Extraction Pipeline")
    ap.add_argument("--file", type=str, default=None, help="Path to a single specific PDF to process")
    ap.add_argument("--max", type=int, default=None, help="Max PDFs to process")
    ap.add_argument("--no-rag", action="store_true", help="Disable RAG retrieval")
    ap.add_argument("--seed-only", action="store_true", help="Only seed RAG, then exit")
    ap.add_argument("--pdf-dir", default=PDF_FOLDER, help="PDF folder path")
    ap.add_argument("--out-dir", default=OUTPUT_DIR, help="Output folder")
    ap.add_argument("--skip-ollama-check", action="store_true", help="Skip Ollama availability check")
    args = ap.parse_args()

    # Seed RAG
    if args.seed_only:
        from rag_store import seed_door_instructions, seed_hardware_instructions
        n_door = seed_door_instructions()
        n_hw = seed_hardware_instructions()
        print(f"RAG seeded: {n_door} door chunks, {n_hw} hardware chunks.")
        return

    # Check Ollama
    if not args.skip_ollama_check:
        if not check_ollama():
            sys.exit(1)

    # Auto-seed RAG if needed
    if not args.no_rag:
        try:
            from rag_store import get_client, CHROMA_COLLECTION_DOOR
            client = get_client()
            if client:
                try:
                    coll = client.get_collection(CHROMA_COLLECTION_DOOR)
                    if coll.count() == 0:
                        raise ValueError("empty")
                except Exception:
                    print("Seeding RAG store...")
                    from rag_store import seed_door_instructions, seed_hardware_instructions
                    seed_door_instructions()
                    seed_hardware_instructions()
        except Exception as e:
            print(f"RAG seed warning: {e}")

    # Run pipeline
    from pipeline import run_pipeline
    df_doors, df_components = run_pipeline(
        pdf_folder=args.pdf_dir,
        output_dir=args.out_dir,
        max_pdfs=args.max,
        use_rag=not args.no_rag,
        pdf_files=[Path(args.file)] if args.file else None,
    )

    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"  Doors extracted:     {len(df_doors)}")
    print(f"  Hardware components: {len(df_components)}")
    print(f"  Output: {Path(args.out_dir) / 'extraction_results_llm.xlsx'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
