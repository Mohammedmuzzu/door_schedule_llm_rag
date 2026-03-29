# Hardware Schedule (Division 8) Extraction Rules

## Goal
Extract hardware set headers and component rows from Division 8 PDFs. Text may be in table form, paragraph form, or mixed.

## Critical Rule: No Quantity Modification
**The quantities in Division 8 ALREADY account for the door configuration (single vs pair).**
Extract quantities EXACTLY as stated. Do NOT double, multiply, or modify them in any way.

## Instructions
1. **Set headers:** When you see "HARDWARE SET NO. 1", "GROUP 2", "Set: 3", "HARDWARE GROUP NO. 103 – SGL Office Lock", that starts a new hardware set. Assign hardware_set_id for ALL following components until the next set header.
2. **Set name:** Extract the functional name after the set number, e.g., "SGL Office Lock", "PR Exterior Storeroom Lock/CLSR". Include it in hardware_set_name.
3. **Component lines:** Each usually starts with a quantity (number), then optionally a unit (EA, PAIR, SET), then a description. E.g., "2 EA HINGE", "1 CLOSER", "3 EA 1-1/2 PAIR BUTT HINGE".
4. **Required fields:** hardware_set_id, qty, description. Unit defaults to "EA".
5. **Optional fields:** catalog_number, finish_code, manufacturer_code — extract when present.
6. **Skip non-hardware lines:** Notes like "Provided by owner", "See detail 5/A", wall descriptions, drawing references.
7. **Output valid JSON only.** No markdown, no text.

## Common Component Types
- HINGE / BUTT HINGE / ANCHOR HINGE / NRP HINGE
- LOCK / LOCKSET / PASSAGE / OFFICE LOCK / STOREROOM LOCK
- CLOSER / SURFACE CLOSER / OVERHEAD CLOSER
- DOOR STOP / WALL STOP / FLOOR STOP
- THRESHOLD / SADDLE
- SEAL / GASKET / WEATHERSTRIP / SMOKE SEAL
- COORDINATOR
- FLUSH BOLT / MANUAL FLUSH BOLT
- SILENCER
- KICK PLATE / PROTECTION PLATE
- VIEWER / PEEPHOLE
- EXIT DEVICE / PANIC BAR

## Common Manufacturers
IVE (Ives), FAL (Falcon), LCN, ZER (Zero), DON (Don-Jo), PEM (Pemko), HAG (Hager), SCH (Schlage), YAL (Yale), KWN (Kawneer), STO (Stanley)

## Example Input
```
HARDWARE GROUP NO. 103 – SGL Office Lock
Applicable Doors: 1419, 1419A

QTY  UNIT  DESCRIPTION               CATALOG NO.      FINISH  MFR
3    EA    HINGE                      5BB1 4.5 X 4.5   626     IVE
1    EA    OFFICE LOCK                MA521H DN        626     FAL
1    EA    SURFACE CLOSER             4040XP           689     LCN
1    EA    WALL STOP                  WS406/407CCV     626     IVE
1    SET   SILENCER                   SR64             —       IVE
```

## Example Output
[{"hardware_set_id":"103","hardware_set_name":"SGL Office Lock","qty":3,"unit":"EA","description":"HINGE","catalog_number":"5BB1 4.5 X 4.5","finish_code":"626","manufacturer_code":"IVE","notes":null},{"hardware_set_id":"103","hardware_set_name":"SGL Office Lock","qty":1,"unit":"EA","description":"OFFICE LOCK","catalog_number":"MA521H DN","finish_code":"626","manufacturer_code":"FAL","notes":null},{"hardware_set_id":"103","hardware_set_name":"SGL Office Lock","qty":1,"unit":"EA","description":"SURFACE CLOSER","catalog_number":"4040XP","finish_code":"689","manufacturer_code":"LCN","notes":null},{"hardware_set_id":"103","hardware_set_name":"SGL Office Lock","qty":1,"unit":"EA","description":"WALL STOP","catalog_number":"WS406/407CCV","finish_code":"626","manufacturer_code":"IVE","notes":null},{"hardware_set_id":"103","hardware_set_name":"SGL Office Lock","qty":1,"unit":"SET","description":"SILENCER","catalog_number":"SR64","finish_code":null,"manufacturer_code":"IVE","notes":null}]
