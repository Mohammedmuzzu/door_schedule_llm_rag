"""
run_store.py
────────────
Durable per-run JSONL logging.

Every invocation of `run_pipeline` opens a single JSONL file under
`rag_data/runs/<YYYY-MM-DD>/<timestamp>_<pdfstem>.jsonl`. Each line is one
structured event (pipeline_start, page_extracted, page_verified, anomaly,
pipeline_end). The format is deliberately append-only and append-safe so a
crash mid-run still leaves a readable log.

Why
    The Streamlit UI only shows the last 15 lines of stderr. That is fine
    for a live demo but worthless when a user reports "my Monday 3pm run
    extracted the wrong doors." With run_store in place, every run leaves a
    durable, searchable trail with:
        - what LLM + provider were used
        - per-page evidence, confidence, and verification report
        - which pages triggered a rescue (and how many rows it added)
        - overall timing

Directory layout
    rag_data/
        runs/
            2026-04-22/
                183045_A6.0.jsonl
                183401_Door_Schedule.jsonl
            latest.json         ← pointer to the most recent run file
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import RAG_DATA_DIR

logger = logging.getLogger("run_store")

RUNS_DIR = Path(RAG_DATA_DIR) / "runs"
LATEST_POINTER = Path(RAG_DATA_DIR) / "runs" / "latest.json"


def _safe_name(stem: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in stem)[:80]


@dataclass
class RunLogger:
    """
    One-run logger. Call `start()` before processing, `event()` per milestone,
    and `finish()` at the end. Thread-safe enough for single-process usage.
    """

    pdf_name: str
    provider: str
    model: str
    use_rag: bool = True
    mineru_available: bool = False
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    _path: Optional[Path] = None
    _start_time: float = 0.0
    _events: List[Dict[str, Any]] = field(default_factory=list)

    def start(self) -> Path:
        today = _dt.datetime.now().strftime("%Y-%m-%d")
        ts = _dt.datetime.now().strftime("%H%M%S")
        dirpath = RUNS_DIR / today
        dirpath.mkdir(parents=True, exist_ok=True)
        filename = f"{ts}_{_safe_name(Path(self.pdf_name).stem)}_{self.run_id}.jsonl"
        self._path = dirpath / filename
        self._start_time = time.time()
        self._write({
            "event": "pipeline_start",
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "pdf_name": self.pdf_name,
            "provider": self.provider,
            "model": self.model,
            "use_rag": self.use_rag,
            "mineru_available": self.mineru_available,
            "run_id": self.run_id,
        })
        _update_latest_pointer(self._path)
        return self._path

    def event(self, event_type: str, **payload: Any) -> None:
        record = {
            "event": event_type,
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "elapsed_s": round(time.time() - self._start_time, 2),
            **payload,
        }
        self._write(record)

    def finish(
        self,
        doors: int,
        hardware: int,
        status: str = "OK",
        error: Optional[str] = None,
    ) -> None:
        self._write({
            "event": "pipeline_end",
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "elapsed_s": round(time.time() - self._start_time, 2),
            "doors_extracted": doors,
            "hardware_extracted": hardware,
            "status": status,
            "error": error,
        })

    # ── internals ─────────────────────────────────────────────────
    def _write(self, record: Dict[str, Any]) -> None:
        self._events.append(record)
        if self._path is None:
            return
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception as e:  # pragma: no cover
            logger.warning("run_store write failed: %s", e)


def _update_latest_pointer(path: Path) -> None:
    try:
        LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
        LATEST_POINTER.write_text(
            json.dumps({"path": str(path), "ts": _dt.datetime.now().isoformat()}),
            encoding="utf-8",
        )
    except Exception as e:  # pragma: no cover
        logger.debug("latest pointer update failed: %s", e)


# ─── Read helpers (for UI / debugging) ────────────────────────────
def list_recent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Return a compact summary of the most recent runs, newest first.
    Each record: {path, pdf, doors, hw, status, elapsed_s, ts}.
    """
    if not RUNS_DIR.exists():
        return []
    files = []
    for day_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not day_dir.is_dir():
            continue
        for f in sorted(day_dir.glob("*.jsonl"), reverse=True):
            files.append(f)
            if len(files) >= limit:
                break
        if len(files) >= limit:
            break

    out = []
    for f in files:
        summary = _summarize_run_file(f)
        if summary:
            out.append(summary)
    return out


def _summarize_run_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        first = last = None
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if first is None:
                    first = record
                last = record
        if not first:
            return None
        return {
            "path": str(path),
            "pdf": first.get("pdf_name", ""),
            "provider": first.get("provider", ""),
            "model": first.get("model", ""),
            "doors": (last or {}).get("doors_extracted", 0),
            "hw": (last or {}).get("hardware_extracted", 0),
            "status": (last or {}).get("status", "PARTIAL"),
            "elapsed_s": (last or {}).get("elapsed_s", None),
            "started": first.get("ts", ""),
        }
    except Exception:
        return None
