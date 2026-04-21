# 🧠 AI Developer Handbook: Door Schedule RAG Pipeline

**Welcome, future AI Coding Assistant!** 
If the user has asked you to modify, debug, or extend this repository, **read this document first**. 

This repository processes horrific, extremely high-variance A0 architectural submittal PDFs generated from broken CAD tools. To hit a >99% data extraction fidelity on 140+ projects, we had to implement highly specific architectural patches. If you blindly refactor `agent.py`, `page_extractor.py`, or `prompts.py` using standard RAG assumptions, you **WILL BREAK THE PIPELINE**.

Below are the 5 critical architectural "trapdoors" we discovered and fixed. **Do not remove this logic.**

---

## 1. The "Optical Illusion" Font Corruption
**Symptom:** You extract text from a PDF, and `pymupdf` natively returns thousands of characters of total garbage (e.g. `(cid:10) (cid:40) yx`). As a result, the Gatekeeper classifies the page as `OTHER` because the word "DOOR" isn't found. Yet, if you look at the PDF visually, the table renders perfectly!
**The Truth:** CAD software often exports PDFs with heavily corrupted embedded font definitions. 
**The Fix:** Inside `page_extractor.py`, look at `_is_text_gibberish()`. It calculates the alphanumeric and vowel density of the extracted text. If the density drops below 35%, the pipeline assumes Font Corruption, **throws away the natively extracted text**, and forcefully reboots the page using **PaddleOCR** (`img2table` use_ocr=True) to physically read the image shapes. Do not remove this heuristic.

## 2. Mixed Hardware Schedules (The `MIXED` Heuristic)
**Symptom:** Hardware schedules usually don't have the word "Door" on them. As a result, the "Fast Gatekeeper" (which checks for simple keywords) often aggressively rejects valid hardware schedules.
**The Fix:** Inside `page_extractor.py`, there is a deterministic upgrade rule: if the gatekeeper detects regex patterns like `SET #`, `HW SET`, or `HDWE`, it will automatically override the page classification to `MIXED` instead of `OTHER`. Do not strictly enforce the word "door" for classification.

## 3. The A0 Blueprint Truncation Trap 
**Symptom:** Huge A0 PDFs (the size of literal dining tables) can contain 100+ doors and generate 30,000+ characters of raw markdown when extracted. The LLM crashes or returns incomplete arrays.
**The Truth:** Standard prompt token buffers were overflowing, AND OpenAI's Vision model `gpt-4o` automatically downscales large images to `768x2000px`, causing massive dense tables to blur into 1-pixel illegible dots.
**The Fix:** 
1. `config.py` sets `MAX_PAGE_CHARS = 35000`. Do not lower this.
2. Inside `page_extractor.py`, if `native_text_len > 20000`, the pipeline **forces an image dropout** (`base64_img = None`). This prevents OpenAI Vision from downscaling and forces the LLM to rely purely on the text layer. 

## 4. The Agentic Hardware Fallback
**Symptom:** A page is classified perfectly as `DOOR_SCHEDULE`. Doors are extracted nicely. But ZERO hardware items are extracted, even though there's a hardware table at the bottom of the page.
**The Truth:** `DOOR_SCHEDULE` pages often don't trigger the hardware extraction loop if the LLM thinks it only needs to look for doors.
**The Fix:** In `agent.py`, inside the `process_pdf()` loop: if a page is classified as `DOOR_SCHEDULE` but the text natively mentions "Hardware Set", the pipeline forces a dynamic `llm_extract.extract_hardware_llm()` fallback pass over that same page. 

## 5. Borderless Key-Value Matrix Prompting
**Symptom:** Standard HTML or Markdown table parsing (even OpenAI's Vision) fails to see tables because the architect literally didn't draw any lines. Doors are listed in vertical floating text blocks (e.g. "DOOR TYPE: A \n FRAME TYPE: B").
**The Truth:** To an LLM, these look like paragraphs, not tables.
**The Fix:** In `prompts.py`, `Instruction 17` explicitly tells the LLM to treat "distinct vertical clusters or unbordered Key-Value text rows as separate door rows aggressively".

---

**Summary:** 
Do not assume standard table parsing works in construction PDFs. The pipeline functions entirely via a hybrid **Heuristic Gatekeeper + Optical/Vector Dual-Engine + Multi-LLM Extraction logic**. 
If you add new features, plug them into the existing fallback structures inside `agent.py`.
