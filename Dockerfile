FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    DEPLOYMENT_ENV=production \
    LLM_PROVIDER=openai \
    MAX_PAGE_CHARS=16000 \
    RAG_DATA_DIR=/tmp/rag_data \
    OUTPUT_DIR=/tmp/extracted_data

WORKDIR $HOME/app

COPY --chown=user door_schedule_llm_rag/requirements.txt ./door_schedule_llm_rag/requirements.txt
RUN python -m pip install --user --upgrade pip \
    && python -m pip install --user -r door_schedule_llm_rag/requirements.txt

COPY --chown=user . .

WORKDIR $HOME/app/door_schedule_llm_rag

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
