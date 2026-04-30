"""
RAG store: persist instructions and examples in ChromaDB for retrieval.
Uses sentence-transformers for local embeddings.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("rag")

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    _RAG_AVAILABLE = True
except ImportError:
    logger.warning("chromadb or sentence-transformers not installed. RAG disabled.")
    _RAG_AVAILABLE = False

from config import (
    RAG_DATA_DIR,
    INSTRUCTIONS_DIR,
    CHROMA_COLLECTION_DOOR,
    CHROMA_COLLECTION_HARDWARE,
    RAG_TOP_K,
    EMBEDDING_MODEL,
)

# Lazy-loaded embedding model
_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None and _RAG_AVAILABLE:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def embed(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    if model is None:
        return [[0.0] * 384 for _ in texts]  # Fallback
    return model.encode(texts, show_progress_bar=False).tolist()


_chroma_client = None

def get_client():
    global _chroma_client
    if not _RAG_AVAILABLE:
        return None
    if _chroma_client is not None:
        return _chroma_client
        
    path = os.path.join(RAG_DATA_DIR, "chroma")
    Path(path).mkdir(parents=True, exist_ok=True)
    _chroma_client = chromadb.PersistentClient(
        path=path,
        settings=Settings(anonymized_telemetry=False),
    )
    return _chroma_client


def seed_door_instructions() -> int:
    """Load door schedule instructions and add to Chroma."""
    client = get_client()
    if client is None:
        return 0

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_DOOR,
        metadata={"description": "Door schedule extraction rules and examples"},
        embedding_function=None, # Prevents chromadb from auto-loading its own transformers model
    )

    path = INSTRUCTIONS_DIR / "door_schedule_rules.md"
    if not path.exists():
        logger.warning("No door instructions at %s", path)
        return 0

    text = path.read_text(encoding="utf-8")
    # Split by ## sections
    parts = [p.strip() for p in text.split("## ") if p.strip()]
    if not parts:
        parts = [text]

    ids = [f"door_rule_{i}" for i in range(len(parts))]
    embeddings = embed(parts)
    collection.upsert(ids=ids, documents=parts, embeddings=embeddings)
    logger.info("Seeded %d door instruction chunks", len(parts))
    return len(parts)


def seed_hardware_instructions() -> int:
    """Load hardware schedule instructions and add to Chroma."""
    client = get_client()
    if client is None:
        return 0

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_HARDWARE,
        metadata={"description": "Hardware schedule extraction rules and examples"},
        embedding_function=None, # Prevents chromadb from auto-loading its own transformers model
    )

    path = INSTRUCTIONS_DIR / "hardware_schedule_rules.md"
    if not path.exists():
        logger.warning("No hardware instructions at %s", path)
        return 0

    text = path.read_text(encoding="utf-8")
    parts = [p.strip() for p in text.split("## ") if p.strip()]
    if not parts:
        parts = [text]

    ids = [f"hw_rule_{i}" for i in range(len(parts))]
    embeddings = embed(parts)
    collection.upsert(ids=ids, documents=parts, embeddings=embeddings)
    logger.info("Seeded %d hardware instruction chunks", len(parts))
    return len(parts)


def query_door_instructions(page_text: str, top_k: Optional[int] = None) -> List[str]:
    """Retrieve relevant door-schedule instruction chunks."""
    top_k = top_k or RAG_TOP_K
    client = get_client()
    if client is None:
        return []

    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_DOOR, embedding_function=None)
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []

    query_text = page_text[:3000].strip() or "door schedule table extraction"
    query_emb = embed([query_text])
    result = collection.query(
        query_embeddings=query_emb,
        n_results=min(top_k, count),
    )
    if result and result.get("documents"):
        return result["documents"][0]
    return []


def query_hardware_instructions(page_text: str, top_k: Optional[int] = None) -> List[str]:
    """Retrieve relevant hardware-schedule instruction chunks."""
    top_k = top_k or RAG_TOP_K
    client = get_client()
    if client is None:
        return []

    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_HARDWARE, embedding_function=None)
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []

    query_text = page_text[:3000].strip() or "hardware set component extraction"
    query_emb = embed([query_text])
    result = collection.query(
        query_embeddings=query_emb,
        n_results=min(top_k, count),
    )
    if result and result.get("documents"):
        return result["documents"][0]
    return []
