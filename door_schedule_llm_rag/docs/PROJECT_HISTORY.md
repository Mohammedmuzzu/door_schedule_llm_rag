# The Architectural Evolution of Door Schedule RAG

*A chronological repository of testing, iterations, and ultimate fixes over a 1-month development cycle.*

## Overview
This document serves as the absolute "Source of Truth" for how this codebase transitioned from a basic local LLM script to an enterprise-grade, massive scale PDF extraction pipeline capable of parsing 140+ real-world construction documents with >99% structural fidelity.

Future Coding Assistants tracking this repository should read this first to understand *why* certain Python engineering models and heuristical fallbacks exist in the codebase.

---

## Phase 1: Local Inference & Hardware Acceleration (February - March)
### The Problem
The initial pipeline was built around local inference using `Ollama` (`Qwen2.5` and `Llama3`). Processing large, complex, 10+ column architectural tables locally on an RTX 3060 (12GB VRAM) led to chronic out-of-memory errors and context window timeouts.

### The Fix
The pipeline architecture was fundamentally rewritten to strictly manage tokens. 
- Integrated `pdfplumber` to extract pure markdown tables, significantly reducing the "noise" (like image vectors) fed to the LLM. 
- Enforced strict JSON parsing schemas (`schema.py` using Pydantic).
- Setup the `llm_extract.py` script with auto-retry logic specifically to repair broken JSON chunks caused by local LLM hallucination mid-stream.

---

## Phase 2: Heuristic Gatekeeping vs. Hybrid RAG (Early April)
### The Problem
Processing 32 random A0 PDFs led to massive performance degradation because the LLM was forced to individually analyze cover sheets, building notes, and standard elevations, causing hallucinations when it desperately tried to map windows onto "Door Schedules".

### The Fix
We introduced the **Hybrid Classification Engine** (`page_extractor.py`). 
- **Layer 1:** A blazing fast Regex Gatekeeper. If it sees `DOOR`, `SCHEDULE`, `HW`, `HDWE`, it passes to Layer 2. If it misses completely, it forces `OTHER` and skips the LLM entirely, saving thousands of tokens.
- **Layer 2:** The "LLM Arbiter". It reads the page and officially classifies it as `DOOR_SCHEDULE`, `HARDWARE_SET`, `MIXED`, or `OTHER`.

---

## Phase 3: The 140-PDF Edge Case Benchmark & Optical Fixes (Late April)
### The Problem
Running an intensive scale benchmark across 140 PDFs revealed catastrophic edge-cases in the architectural industry:
1. **The "Orphan Hardware" Spill:** The Gatekeeper perfectly classified a page as `DOOR_SCHEDULE`, meaning the Agent only extracted doors... but the architect squeezed a hardware list at the bottom! Over 100 hardware nodes were lost.
2. **The "Optical Illusion" Font Bug:** 14 PDFs failed with `ZERO_EXTRACT`. Natively, `pymupdf` extracted thousands of characters of random wingdings (`cid:`) due to corrupted CAD font tables, but the PDF looked perfect to the human eye!
3. **The A0-Blueprint Truncation:** Dense A0 blueprints have 60+ rows, pushing raw markdown over 30,000 characters.

### The Production Fixes (Current State)
We implemented "The Limit Break" patches:
- **Agentic Fallback Loop (`agent.py`):** If a `DOOR_SCHEDULE` extraction yields any text regarding hardware sets, the internal agent forcibly re-triggers a dynamic hardware query on the exact same page.
- **The Gibberish-OCR Reboot (`page_extractor.py`):** We mapped an algebraic heuristic over extracted text tracking alphanumeric and vowel density. If it drops below 35% (the Font Bug), we instantly drop the native string and trigger pure optical image detection via `img2table` and **PaddleOCR**.
- **A0 Image Payloads:** If the page generates over 25,000 text characters, the OpenAI Vision API attempts to compress the payload (downscaling to 768px), which blurs the A0 pdf into mush. We actively track extraction character limits and intentionally *drop* the `base64` image if the text is exceptionally dense, forcing the LLM back to semantic parsing.

---

### Final Implementation State
The pipeline is now stabilized. **DO NOT REMOVE** the optical gibberish fallbacks or the agent loops. If you want to train the LLM on new broken PDF tables, simply append the visual table markdown format into the RAG files inside the `instructions/` directory so the core `prompts.py` behavior is unaffected.
