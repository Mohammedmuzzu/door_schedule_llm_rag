"""
page_evidence.py
────────────────
Single source of truth for page-level structural signals.

Goal
    Move away from scattered regex heuristics sprinkled across page_extractor,
    agent, and pipeline modules. Every downstream routing / verification
    decision should read from `PageEvidence` instead of re-computing similar
    patterns with slightly-different thresholds.

    This module is intentionally pure (no LLM calls, no file I/O). The text
    passed in is already the final merged content used for extraction, so the
    evidence perfectly mirrors what the extractor/LLM will see.

Why this design
    Robustness to PDF format variations (PRD requirement) is best achieved by
    treating extraction as a scoring problem:
        collect evidence -> estimate expected counts -> extract -> verify
    not as an if/elif ladder of format-specific rules. Adding new formats
    should only require adding signals here, never forking the code path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════
# Regex primitives (compiled once)
# ═══════════════════════════════════════════════════════════════════
_RE_DOOR_NUM = re.compile(r"\b\d{2,4}[A-Za-z]?\b")
_RE_DIMENSION = re.compile(r"\d+\s*['\u2019]\s*-?\s*\d+\s*\"")
_RE_CAD_SHORTHAND = re.compile(r"\b\d{3,4}\s*[xX]\s*\d{3,4}\b")
_RE_SET_HEADER = re.compile(
    r"(?:^|\n)\s*(?:HARDWARE\s+SET|HARDWARE\s+GROUP|HDWE\s+SET|HDWR\s+SET|HW\s+SET|"
    r"SET\s*NO\.?|GROUP\s*NO\.?|HW\s*[#\-]?\s*\d+|SET\s*[#\-]?\s*\d+|GROUP\s*[#\-]?\s*\d+)"
    r"\s*[\.:\-]?\s*[\w\d\-]*",
    re.IGNORECASE,
)
_RE_HW_COMPONENT = re.compile(
    r"\b(?:HINGE|CLOSER|LOCKSET|DEADLOCK|DEADBOLT|STRIKE|THRESHOLD|WEATHERSTRIP|"
    r"KICK\s*PLATE|DOOR\s*STOP|FLOOR\s*STOP|WALL\s*STOP|SMOKE\s*SEAL|GASKET|"
    r"SILENCER|PANIC|EXIT\s*DEVICE|COORDINATOR|FLUSH\s*BOLT|SURFACE\s*BOLT|"
    r"OVERHEAD\s*STOP|POWER\s*TRANSFER|ELECTRIC\s*STRIKE)\b",
    re.IGNORECASE,
)
_RE_SCHEDULE_HEADER = re.compile(
    r"\b(?:DOOR\s+SCHEDULE|HARDWARE\s+SCHEDULE|DOOR\s+NO\.?|DOOR\s+NUMBER|"
    r"DOOR\s+MARK|FRAME\s+TYPE|FIRE\s+RATING|HDWR\s+SET|HARDWARE\s+SET)\b",
    re.IGNORECASE,
)
_RE_TITLE_BLOCK = re.compile(
    r"\b(?:PROJECT\s+NO|PROJECT\s+LOCATION|DRAWN\s+BY|CHECKED\s+BY|"
    r"SHEET\s+(?:NO|NUMBER)|PHONE\s*:|WWW\.|ARCHITECTS?|REVISIONS?\b|"
    r"FIRST\s+ISSUED\s+ON|STREET|SUITE|ZIP|CITY,?\s*STATE)\b",
    re.IGNORECASE,
)
_RE_CID_GARBAGE = re.compile(r"\(cid:\d+\)")
_RE_BROKEN_COLS = (
    re.compile(r"\bDOO\s*\|\s*R\b", re.IGNORECASE),
    re.compile(r"\bSCH\s*\|\s*EDULE\b", re.IGNORECASE),
    re.compile(r"\bNUM\s*\|\s*BER\b", re.IGNORECASE),
    re.compile(r"\bFI\s*\|\s*RE\b", re.IGNORECASE),
    re.compile(r"\bHAR\s*\|\s*DWARE\b", re.IGNORECASE),
)


# ═══════════════════════════════════════════════════════════════════
# Data structure
# ═══════════════════════════════════════════════════════════════════
@dataclass
class PageEvidence:
    """
    Structural evidence collected from already-extracted page text.

    Counts are intentionally raw; higher-level modules can compose confidence
    scores from them. Keeping them as primitive integers makes the class easy
    to log, diff across extractor versions, and serialize for debugging.
    """

    # door/row level signals
    real_door_numbers: int = 0          # unique door-mark-like numbers (excludes years)
    dimensions: int = 0                 # 3'-0" style tokens
    cad_shorthand: int = 0              # 3070 / 30x70 style
    row_lines: int = 0                  # lines with a door number AND dimension/keyword
    schedule_headers: int = 0           # DOOR SCHEDULE / FIRE RATING / etc.

    # hardware-set signals
    hw_set_headers: int = 0             # HARDWARE SET NO. / GROUP X
    hw_components: int = 0              # HINGE, CLOSER, etc.

    # noise signals
    title_block_markers: int = 0
    cid_garbage: int = 0
    broken_columns: int = 0             # fragmented-table pipe patterns

    # summary metadata
    text_length: int = 0
    distinct_door_sample: List[str] = field(default_factory=list)

    # ── Derived helpers ────────────────────────────────────────────
    @property
    def is_door_schedule(self) -> bool:
        return (
            self.row_lines >= 2
            or (self.real_door_numbers >= 4 and self.schedule_headers >= 3)
            or (self.dimensions >= 3 and self.real_door_numbers >= 3)
        )

    @property
    def is_hardware_schedule(self) -> bool:
        return self.hw_set_headers >= 1 and self.hw_components >= 3

    @property
    def is_title_block_only(self) -> bool:
        """Strong title-block fingerprint with near-zero schedule content."""
        has_schedule_body = (
            self.row_lines >= 2
            or self.dimensions >= 2
            or self.hw_components >= 3
            or self.hw_set_headers >= 1
        )
        return (
            self.title_block_markers >= 2
            and not has_schedule_body
            and self.real_door_numbers <= 3
        )

    @property
    def is_corrupt(self) -> bool:
        """Heavy CID garbage or highly fragmented columns."""
        if self.text_length <= 0:
            return False
        cid_ratio = self.cid_garbage / max(self.text_length, 1)
        return cid_ratio > 0.05 or self.broken_columns >= 1

    def expected_door_rows(self) -> int:
        """
        Best-effort minimum door count based on evidence.

        Priority of signals:
          1. `row_lines` is the most reliable — it counts lines that contain
             both a door-number-like token AND a schedule keyword/dimension,
             so false positives (years, addresses, note numbers) are rare.
          2. As a secondary signal we use `real_door_numbers` capped by the
             number of dimensional tokens divided by ~3 (each door typically
             carries several dimensions: width, height, thickness, frame size
             — so raw `dimensions` roughly triple-counts doors).

        We deliberately do *not* take the maximum of the two — the earlier
        version did, which caused systematic overestimation on schedule pages
        where raw dimension counts are much larger than row counts.
        """
        strong = self.row_lines
        dims_signal = max(self.dimensions // 3, self.cad_shorthand)
        weak = min(self.real_door_numbers, dims_signal) if dims_signal else 0

        if strong >= 3:
            # Strong signal present — trust it, but let weak nudge it upward
            # modestly if it's *much* larger (>= 2×). This catches cases where
            # row_lines missed fragmented rows but other signals are plentiful.
            if weak >= strong * 2:
                return int((strong + weak) / 2)
            return strong
        # Without strong signal, fall back to weak.
        return max(strong, weak)

    def expected_hw_sets(self) -> int:
        """Best-effort minimum hardware-set count."""
        if self.hw_components < 3:
            return 0
        return max(1, self.hw_set_headers)

    def as_dict(self) -> Dict[str, int]:
        return {
            "real_door_numbers": self.real_door_numbers,
            "dimensions": self.dimensions,
            "cad_shorthand": self.cad_shorthand,
            "row_lines": self.row_lines,
            "schedule_headers": self.schedule_headers,
            "hw_set_headers": self.hw_set_headers,
            "hw_components": self.hw_components,
            "title_block_markers": self.title_block_markers,
            "cid_garbage": self.cid_garbage,
            "broken_columns": self.broken_columns,
            "text_length": self.text_length,
            "expected_door_rows": self.expected_door_rows(),
            "expected_hw_sets": self.expected_hw_sets(),
            "is_door_schedule": self.is_door_schedule,
            "is_hardware_schedule": self.is_hardware_schedule,
            "is_title_block_only": self.is_title_block_only,
            "is_corrupt": self.is_corrupt,
        }


# ═══════════════════════════════════════════════════════════════════
# Extraction
# ═══════════════════════════════════════════════════════════════════
def _real_doors(text: str) -> Tuple[int, List[str]]:
    seen: List[str] = []
    for token in _RE_DOOR_NUM.findall(text):
        m = re.match(r"\d+", token)
        if not m:
            continue
        val = int(m.group())
        # exclude years (1900-2099)
        if 1900 <= val <= 2099:
            continue
        if token not in seen:
            seen.append(token)
    return len(seen), seen[:10]


def _row_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        if not _RE_DOOR_NUM.search(line):
            continue
        upper = line.upper()
        if _RE_DIMENSION.search(line):
            count += 1
            continue
        if any(
            kw in upper
            for kw in (
                "EXISTING", "NEW", "HM", "WD", "ALUM", "FRAME",
                "LOCK", "HINGE", "CLOSER", "PAIR", "PR ",
                "GL-", "HDWR", "HARDWARE",
            )
        ):
            count += 1
    return count


def _broken_columns(text: str) -> int:
    return sum(1 for pat in _RE_BROKEN_COLS if pat.search(text))


def collect(text: str) -> PageEvidence:
    """
    Build a `PageEvidence` object from arbitrary extracted page text.

    The function is safe on empty / None input and returns a zero-valued
    evidence object so callers never need to guard against None.
    """
    if not text:
        return PageEvidence()

    door_count, door_sample = _real_doors(text)
    evidence = PageEvidence(
        real_door_numbers=door_count,
        dimensions=len(_RE_DIMENSION.findall(text)),
        cad_shorthand=len(_RE_CAD_SHORTHAND.findall(text)),
        row_lines=_row_lines(text),
        schedule_headers=len(_RE_SCHEDULE_HEADER.findall(text)),
        hw_set_headers=len(_RE_SET_HEADER.findall(text)),
        hw_components=len(_RE_HW_COMPONENT.findall(text)),
        title_block_markers=len(_RE_TITLE_BLOCK.findall(text)),
        cid_garbage=len(_RE_CID_GARBAGE.findall(text)),
        broken_columns=_broken_columns(text),
        text_length=len(text),
        distinct_door_sample=door_sample,
    )
    return evidence


def confidence_score(evidence: PageEvidence) -> float:
    """
    Continuous 0..1 confidence score that the page text is extractable
    without needing OCR / Vision escalation.

    Used purely for routing; not as a hard gate.
    """
    if evidence.text_length <= 0:
        return 0.0
    positive = (
        evidence.row_lines * 4.0
        + evidence.dimensions * 1.5
        + evidence.schedule_headers * 1.5
        + evidence.hw_components * 2.0
        + evidence.hw_set_headers * 3.0
        + min(evidence.real_door_numbers, 50) * 0.5
    )
    negative = (
        evidence.cid_garbage * 2.0
        + evidence.broken_columns * 8.0
        + (evidence.title_block_markers * 1.0 if evidence.is_title_block_only else 0.0)
    )
    raw = positive - negative
    return max(0.0, min(1.0, raw / 60.0))
