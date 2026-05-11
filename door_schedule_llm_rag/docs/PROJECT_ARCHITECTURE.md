# 🏢 Door Schedule & Hardware LLM Extractor - Architecture Guide

This document encapsulates the entire lifecycle, architecture, skills, and hard-earned engineering findings of the Architectural PDF Extraction Pipeline.

---

## 1. Environment & Setup

### Virtual Environment Enforcement
The extraction dependencies (like `pdfplumber`, `PyMuPDF`, `streamlit`, and `pandas`) reside in a specific local workspace.
- **Python Path:** `c:\Users\muzaf\my_lab\computervision\Scripts\python.exe`
- **Streamlit Path:** `c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe`
- **Activation Script:** `c:\Users\muzaf\my_lab\computervision\Scripts\Activate.ps1`

**CRITICAL:** Never use the bare system `python` or `streamlit` command. Running outside the `computervision` environment will result in dependency resolution failures on Windows. 

### Running the Application
To run the primary application UI from the project root (`sushmita_proj/door_schedule_llm_rag/`):
```powershell
& "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
```

---

## 2. Dynamic LLM Architecture

The pipeline evolved from being statically bound to OpenAI models into a dynamic, highly flexible, multi-provider inference system.

### The `LLMConfig` Singleton
The application uses a Global configuration pattern injected dynamically via the Streamlit interface without requiring hard restarts or `.env` modifications:
- **OpenAI (Primary):** Fastest and most accurate. Default model is `gpt-4o-mini`.
- **Groq:** Lightning-fast cloud inference with Llama variants.
- **Ollama (Local Fallback):** For 100% offline local inference (e.g., `llama3.2`, `qwen2.5-coder`).

The script `llm_extract.py` utilizes fallback chains mapping unsupported or token-limited models to compatible APIs based on the active provider.

---

## 3. Formatting Generalization (The "Extraction Skills")

The biggest technical challenge overcome was preventing the LLM from hallucinating or skipping data when fed non-standard architectural conventions. The following extraction scenarios were identified and mapped into the rigid system prompts (`prompts.py`).

### A. The "Tabular Matrix" vs "Vertical Profile" Problem
Not all door schedules are standard grids. Some (e.g., *Project 7*) list items as nested Key-Value forms or grouped blocks:
- **Tabular:** Explicit Row-by-Row matrices.
- **Vertical Profiles:** Repeating blocks reading `DOOR TYPE: ALUM... FRAME FINISH: CLEAR...`
**The Solution:** The LLM prompts were augmented to explicitly classify "profiles" as discrete rows, treating each cluster exactly like a row in a standard schedule.

### B. Synthesized Identifiers (Doors & Hardware)
- **Missing Door Marks:** If a door didn't have a numeric `101`, it was skipped. We now force the LLM to adopt alphanumeric IDs (e.g., `Type A`) as the `door_number` to prevent data loss.
- **Hardware Integration:** Hardware lists are often blended directly underneath a door's block instead of placed in a separate formally numbered "HARDWARE SET NO. X" table. The pipeline is instructed to **synthesize generic IDs (e.g., `HW-TypeA`)** so the relational mapping between the hardware logic and the door schedule never breaks. 

### C. Quantity Formatting
In division 8 specifications, hardware quantities appear natively as `(3 EA.)`, `1-1/2 PAIRS`, or `LOT`. The prompt rules are specifically crafted to reduce this noisy text into pure integers or verbatim configurations.

---

## 4. UI Rendering and `st.dataframe` Crashes (React Error #185)

During deployment, a massive issue blocked Streamlit rendering (React Error `#185`). 

**The Root Cause:** The `page_extractor` sometimes pulls highly complex Key-Value dictionaries into the `extra_fields` JSON dict. Streamlit leverages **PyArrow** to render DataFrames dynamically into its UI. PyArrow immediately crashed when attempting to serialize nested Python dictionaries into flat Arrow columns.

**The Fix:** 
Before passing standard Pandas DataFrames into the UX component, the pipeline aggressively transforms all elements to strings locally:
```python
st.dataframe(df_doors.astype(str), width="stretch")
```
This entirely solved the frontend crashing issue while preserving the high-quality source dict outputs for Excel and CSV downloads.

---

## 5. Architectural NLP Anomaly Logging (Project - 9)
During automated audits, key multi-format weaknesses in OCR parsing were identified and patched at the prompt layer.

### A. The Two-Column Hardware Trap
* **The Bug:** Certain Division 8 hardware sets (e.g., Project 9) render sets side-by-side. Text scrapers compress these columns horizontally into a single line: `Set: 1.0 Set: 23.0`. The LLM ignored the right-side values 100% of the time, dropping massive amounts of data.
* **The Fix:** Explicit prompt guidelines injected into `SYSTEM_HARDWARE` instructing the agent to split interleaved columns mathematically and extract horizontally decoupled arrays.

### B. Borderless Table Swaps (Door No. vs Room Name)
* **The Bug:** When vertical borders are absent, row text condenses sequentially into `[Room Name] [Door Number]` or vice versa (`MAIN ENTRY 100`). LLMs default to Left-to-Right binding, mapping the textual room name to the `door_number` property and vice versa.
* **The Fix:** Mandatory deterministic overriding inside `SYSTEM_DOOR` teaching the model that isolated generic digits adjoining complex words in an unbordered text block permanently map to `door_number` regardless of semantic sequential order.
