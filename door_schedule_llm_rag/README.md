# Door Schedule LLM + RAG Documentation

The **Door Schedule LLM + RAG** pipeline is designed to robustly parse highly variable, complex, or unstandardized structural PDFs. Instead of relying on rigid Python logic, this codebase utilizes local Large Language Model (LLM) inference (via Ollama) and a Retrieval-Augmented Generation (RAG) system to securely extract data.

---

## 🏗️ Folder Structure

```
├── .env                    # System configuration and LLM toggles
├── config.py               # Reads .env and defines globally used path constants
├── llm_extract.py          # LLM orchestration, JSON repair, and Pydantic validation
├── page_extractor.py       # Core PDF extraction (pdfplumber, pymupdf4llm, PaddleOCR)
├── prompts.py              # LLM System Prompts with strict anti-hallucination bounds
├── rag_store.py            # Local ChromaDB knowledge store and retriever operations
├── schema.py               # Pydantic schema models for strict structural extraction
├── seed_rag.py             # Script to initialize or rebuild the local vector database
├── run_llm_pipeline.py     # Main execution script
├── requirements.txt        # Exact dependencies
├── extracted_data/         # Auto-generated outputs (.xlsx, .csv)
├── instructions/           # RAG base rules parsed by 'seed_rag.py'
└── ../skills/              # Expert insight reports and analysis performed on source PDFs
```

## 🛠️ Environment Variables (.env)

The pipeline defaults strictly to local hardware to preserve privacy and prevent cloud rate-limiting.

| Variable                 | Purpose                                                                 | Default Value               |
|--------------------------|-------------------------------------------------------------------------|-----------------------------|
| `LLM_PROVIDER`           | Forces the extraction logic to run exclusively on `ollama`.                 | `ollama`                      |
| `OLLAMA_MODEL`           | Primary zero-shot JSON-adherent extraction model.                       | `qwen2.5:7b`                  |
| `OLLAMA_FALLBACK_MODELS` | Models to dynamically try if the primary times out or fails JSON parsing. | `llama3.1:8b,mistral:7b`      |
| `OLLAMA_TIMEOUT`         | Hard timeout ceiling for dense PDF inference.                           | `300` (5 minutes)             |
| `MAX_PAGE_CHARS`         | Slice limit to prevent small GPUs/Memory from context overloading.      | `8000`                        |
| `PDF_FOLDER`             | The directory containing architectural PDFs to parse.                   | `../pdfs`                     |

## 🚀 How to Run

### 1. Install Dependencies
Make sure you have a valid Python 3.10+ environment activated.
```bash
pip install -r requirements.txt
```

### 2. Prepare Local LLMs
Download and install [Ollama](https://ollama.com). Then, pull your configured models:
```bash
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
ollama pull mistral:7b
```

### 3. Initialize RAG Memory
The RAG store needs to be seeded with instruction context once (or anytime you modify `/instructions/`).
```bash
python run_llm_pipeline.py --seed-only
```

### 4. Execute Extraction
Process all PDFs placed inside the `PDF_FOLDER`:
```bash
python run_llm_pipeline.py
```

### Testing Limits
If you want to quickly test the pipeline robustness without parsing 30+ PDFs simultaneously, limit the run to a specific file or a batch threshold:
```bash
python run_llm_pipeline.py --max 3
python run_llm_pipeline.py --file "C:/absolute/path/to/project5_8doors.pdf"
```

---

## 🧠 The `skills` Repository 
We run extensive layout analyses on PDFs. The `skills` folder is populated with markdown reports that dictate how our system perceives varied layouts (borderless, rotated text, complex keys). These insights fuel the strict hallucination-guarding logic defined within `prompts.py` and enforce dynamic fallback pathways for `LLM` page classification inside `page_extractor.py`.

## ⚙️ Data Resilience 
If the architectural schedules contain non-standard details outside of division 8 definitions (e.g., "Weathershield Rating" or "Custom Paint Code"), the prompt and the extraction schema `extra_fields` dict will automatically scoop up those edge cases, preserving 100% of the customer's data without code changes.
