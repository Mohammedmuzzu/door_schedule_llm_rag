"""
Structured schemas for Door Schedule and Division 8 Hardware extraction.
Matches the PRD schema exactly.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ═══════════════════════════════════════════════════════════════════
#  DOOR SCHEDULE ROW — matches PRD "Data Structure" section
# ═══════════════════════════════════════════════════════════════════
class DoorScheduleRow(BaseModel):
    """One row from a Door Schedule PDF."""
    door_number: str = Field(description="Unique door identifier, e.g. 101, 101A, D2")
    level_area: Optional[str] = Field(default=None, description="Level/Area/Floor, e.g. Level 1 – Area A")
    room_name: Optional[str] = Field(default=None, description="Room or location name")
    door_type: Optional[str] = Field(default=None, description="Door type reference, e.g. A5, B, 1")
    frame_type: Optional[str] = Field(default=None, description="Frame material: HM, ALUM, WD, etc.")
    frame_width: Optional[str] = Field(default=None, description="Frame width, e.g. 3'-0\"")
    frame_height: Optional[str] = Field(default=None, description="Frame height, e.g. 7'-0\"")
    door_width: Optional[str] = Field(default=None, description="Door opening width, e.g. 3'-0\", 6'-0\"")
    door_height: Optional[str] = Field(default=None, description="Door opening height, e.g. 7'-0\"")
    hardware_set: Optional[str] = Field(default=None, description="Hardware Set ID, e.g. 1, 103, 711C")
    fire_rating: Optional[str] = Field(default=None, description="Fire rating, e.g. 45 MIN, 1 HR, ----")
    head_jamb_sill_detail: Optional[str] = Field(default=None, description="Detail reference, e.g. A7.11")
    keyed_notes: Optional[str] = Field(default=None, description="Keyed callout reference, e.g. 12A")
    remarks: Optional[str] = Field(default=None, description="Comments/notes about the door")
    door_slab_material: Optional[str] = Field(default=None, description="Derived slab material, e.g. Plastic Laminate")
    vision_panel: Optional[str] = Field(default=None, description="Vision panel size, e.g. 4\"x24\"")
    glazing_type: Optional[str] = Field(default=None, description="Glass type if applicable")
    finish: Optional[str] = Field(default=None, description="Surface finish, e.g. STC 42, Painted Metal")
    is_pair: bool = Field(default=False, description="True if this is a pair/double door")
    door_leaves: int = Field(default=1, description="Number of leaves: 1 for single, 2 for pair")
    extra_fields: Optional[dict] = Field(default_factory=dict, description="Any extra or unrecognized fields found for this door")

    @field_validator("door_number", mode="before")
    @classmethod
    def clean_door_number(cls, v):
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("hardware_set", mode="before")
    @classmethod
    def clean_hardware_set(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        # Remove leading "Set", "HS", "#" etc.
        v = re.sub(r"^(?:set|hs|hw|hdwr|#)\s*", "", v, flags=re.IGNORECASE).strip()
        return v if v and v != "—" and v != "-" else None

    @field_validator("fire_rating", mode="before")
    @classmethod
    def clean_fire_rating(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        if v in ("----", "---", "--", "-", "N/A", "NA", "NONE", ""):
            return None
        return v


# ═══════════════════════════════════════════════════════════════════
#  HARDWARE COMPONENT ROW — matches PRD "Division 8" section
# ═══════════════════════════════════════════════════════════════════
class HardwareComponentRow(BaseModel):
    """One hardware component line under a hardware set in Division 8."""
    hardware_set_id: str = Field(description="Hardware set number/ID, e.g. 103, 1, 711C")
    hardware_set_name: Optional[str] = Field(default=None, description="Functional name, e.g. SGL Office Lock")
    qty: int = Field(description="Quantity per set (as-stated, includes pair adjustments)")
    unit: str = Field(default="EA", description="EA, PAIR, or SET")
    description: str = Field(description="Component description, e.g. HINGE, CLOSER")
    catalog_number: Optional[str] = Field(default=None, description="Catalog/model code")
    finish_code: Optional[str] = Field(default=None, description="Finish code, e.g. 626, 630")
    manufacturer_code: Optional[str] = Field(default=None, description="Manufacturer abbreviation, e.g. IVE, FAL")
    notes: Optional[str] = Field(default=None, description="Additional notes/comments")
    extra_fields: Optional[dict] = Field(default_factory=dict, description="Any extra or unrecognized fields found for this component")

    @field_validator("hardware_set_id", mode="before")
    @classmethod
    def clean_set_id(cls, v):
        if v is None:
            return "?"
        v = str(v).strip()
        v = re.sub(r"^(?:set|hs|hw|hdwr|group|#|no\.?)\s*", "", v, flags=re.IGNORECASE).strip()
        return v if v else "?"

    @field_validator("qty", mode="before")
    @classmethod
    def clean_qty(cls, v):
        if v is None:
            return 1
        try:
            return max(1, int(float(str(v).strip())))
        except (ValueError, TypeError):
            return 1

    @field_validator("unit", mode="before")
    @classmethod
    def clean_unit(cls, v):
        if v is None:
            return "EA"
        v = str(v).strip().upper()
        if v in ("EA", "EACH"):
            return "EA"
        if v in ("PR", "PAIR", "PRS", "PAIRS"):
            return "PAIR"
        if v in ("SET", "SETS"):
            return "SET"
        return "EA"


# ═══════════════════════════════════════════════════════════════════
#  HELPER: Deterministic pair detection from door width + type
# ═══════════════════════════════════════════════════════════════════
def detect_pair_from_width(width_str: Optional[str], door_type_str: Optional[str] = None) -> bool:
    """
    Deterministic pair detection:
    - Width >= 5'-0" (60 inches) is typically a pair
    - Door type containing 'PR', 'PAIR', 'DBL', 'DOUBLE' is a pair
    - Two width values like "3'-0\" x 3'-0\"" or "3'-0\" / 3'-0\"" is a pair
    """
    if door_type_str:
        dt = str(door_type_str).upper()
        if any(kw in dt for kw in ("PAIR", " PR ", "(PR)", "PR-", "-PR", "DBL", "DOUBLE")):
            return True

    if not width_str:
        return False

    w = str(width_str).strip()

    # Check for "x" or "/" separator indicating two leaves
    if re.search(r"\d.*[x/&].*\d", w, re.IGNORECASE):
        return True

    # Parse imperial: convert to inches
    m = re.search(r"(\d+)\s*['\u2019]\s*-?\s*(\d+)", w)
    if m:
        feet, inches = int(m.group(1)), int(m.group(2))
        total_inches = feet * 12 + inches
        if total_inches >= 60:  # 5'-0" or wider = pair
            return True

    # Parse plain number (inches)
    m2 = re.match(r"^(\d+)(?:\s*\")?$", w)
    if m2:
        if int(m2.group(1)) >= 60:
            return True

    return False


def door_schema_for_prompt() -> str:
    return """
Each door row must have these fields:
- door_number (REQUIRED): string, unique ID like "101", "101A", "D2"
- level_area (optional): floor/area, e.g. "Level 1", "Area A"
- room_name (optional): room or location name
- door_type (optional): door type code, e.g. "A5", "B", "1"
- frame_type (optional): HM, ALUM, WD, etc.
- frame_width (optional): frame width dimension
- frame_height (optional): frame height dimension
- door_width (optional): opening width, e.g. "3'-0\\"", "6'-0\\""
- door_height (optional): opening height, e.g. "7'-0\\""
- hardware_set (optional): hardware set ID, e.g. "1", "103", "711C"
- fire_rating (optional): fire rating, e.g. "45 MIN", "1 HR", null if "----" or not present
- head_jamb_sill_detail (optional): detail drawing reference
- keyed_notes (optional): keyed callout references
- remarks (optional): comments or notes
- door_slab_material (optional): slab material from type legend
- vision_panel (optional): vision panel size
- glazing_type (optional): glass type
- finish (optional): surface finish
- is_pair (optional): boolean, true ONLY if width >= 5'-0" or type says PAIR/DBL/DOUBLE
- extra_fields (optional): dictionary of any other key-value pairs/columns found in the row that do not map to the standard schema above.
"""


def hardware_schema_for_prompt() -> str:
    return """
Each hardware component must have:
- hardware_set_id (REQUIRED): the set number, e.g. "1", "103", "711C"
- hardware_set_name (optional): functional name, e.g. "SGL Office Lock", "PR Exterior"
- qty (REQUIRED): integer quantity AS STATED in the document (do NOT double for pairs)
- unit: "EA" | "PAIR" | "SET"
- description (REQUIRED): component name, e.g. "HINGE", "CLOSER", "LOCK"
- catalog_number (optional): model/catalog code
- finish_code (optional): finish code like "626", "630", "BK"
- manufacturer_code (optional): manufacturer abbreviation like "IVE", "FAL", "LCN"
- notes (optional): any notes or remarks for this component
- extra_fields (optional): dictionary of any other unrecognized properties found for this component
"""
