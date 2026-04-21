# Door Schedule Extraction Rules

## Goal
Extract structured door schedule rows from PDF text. PDFs vary in layout: bordered tables, borderless tables, mixed layouts, multi-page tables, and merged cells.

## Instructions
1. **Extract EVERY door/opening row.** Never skip rows even if the table has merged cells, missing borders, or unusual layout.
2. **door_number is required.** It is usually a short alphanumeric code: 101, 101A, D2, 114A, 1421A. Ignore section headers like "DOOR TYPE 1", "NOTE:", or "DOOR SCHEDULE".
3. **Column identification:** Use context clues:
   - Numbers like 3'-0" or 7'-0" → width/height dimensions
   - Single digits in a column → hardware set ID
   - HM, ALUM, WD → frame type
   - 45 MIN, 1 HR → fire rating
   - Alphabetic short codes (A, B, A5, C-1) → door type
4. **Borderless & Key-Value tables:** Each line or block of text may be one row. Split on logical row boundaries. If you see floating text blocks instead of a table (e.g. "MARK: 101 \n DOOR TYPE: A \n HW SET: 1"), treat each vertical grouping as an exact data row!
5. **Multiple door numbers:** If a cell contains "100A 100B", output SEPARATE rows for each.
6. **Level/Area:** Look for section headers ABOVE groups of doors like "LEVEL 1", "Area A", "EXTERIOR DOORS". Apply to all subsequent doors in that group.
7. **Pair detection:** A door is a pair if its opening width >= 5'-0" (60 inches) OR the door type contains PR/PAIR/DBL/DOUBLE. If detected, override door_leaves to 2.
8. **Null defaults & Unknown Fields:** Leave standard fields null if you aren't sure. IF there are key-value pairs or extra columns that do not fit the formal schema (e.g., "Wall Throat", "Jamb Detail"), put them into the `extra_fields` JSON property.

## Common Column Headers (Variants)
- Door number: Door Number, Mark, Tag, No., Opening #, Door No.
- Level/Area: Level, Area, Floor, Zone, Location
- Room: Room Name, Location, Room/Location, Space Name
- Type: Door Type, Type, Configuration, Door Config
- Hardware: Hardware Set, HW Set, Hdwr Set, HDWR Set, Group
- Frame: Frame Type, Frame, Frame Material
- Size: Width, Height, Opening Size, Dimensions, W x H, Size
- Fire: Fire Rating, Fire Rate, FR, Fire Label
- Details: Head Detail, Jamb Detail, Sill Detail
- Material: Slab Material, Door Material
- Notes: Remarks, Comments, Notes, Description

## Example Input (table text)
```
LEVEL 1 AREA A
MARK  DOOR TYPE  FRAME  WIDTH   HEIGHT  HW SET  FIRE    COMMENTS
101A  A          HM     6'-0"   7'-0"   1       ----    ENTRANCE PAIR
101B  A          HM     6'-0"   7'-0"   1       ----
103   B          WD     3'-0"   7'-0"   4       45 MIN  OFFICE
104   C          HM     3'-0"   6'-8"   2       1 HR    STORAGE
```

## Example Output
[{"door_number":"101A","level_area":"Level 1 Area A","room_name":null,"door_type":"A","hardware_set":"1","door_width":"6'-0\"","door_height":"7'-0\"","frame_type":"HM","fire_rating":null,"remarks":"ENTRANCE PAIR","is_pair":true,"door_leaves":2},{"door_number":"101B","level_area":"Level 1 Area A","room_name":null,"door_type":"A","hardware_set":"1","door_width":"6'-0\"","door_height":"7'-0\"","frame_type":"HM","fire_rating":null,"remarks":null,"is_pair":true,"door_leaves":2},{"door_number":"103","level_area":"Level 1 Area A","room_name":"OFFICE","door_type":"B","hardware_set":"4","door_width":"3'-0\"","door_height":"7'-0\"","frame_type":"WD","fire_rating":"45 MIN","remarks":null,"is_pair":false,"door_leaves":1},{"door_number":"104","level_area":"Level 1 Area A","room_name":"STORAGE","door_type":"C","hardware_set":"2","door_width":"3'-0\"","door_height":"6'-8\"","frame_type":"HM","fire_rating":"1 HR","remarks":null,"is_pair":false,"door_leaves":1}]
