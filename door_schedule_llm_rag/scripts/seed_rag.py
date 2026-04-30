"""
Seed the RAG store with instructions from the instructions/ folder.
Run once (or after updating instructions) before running the pipeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_store import seed_door_instructions, seed_hardware_instructions

if __name__ == "__main__":
    n_door = seed_door_instructions()
    n_hw = seed_hardware_instructions()
    print(f"RAG seeded: {n_door} door chunks, {n_hw} hardware chunks.")
    print("Run 'python run_llm_pipeline.py' to start extraction.")
