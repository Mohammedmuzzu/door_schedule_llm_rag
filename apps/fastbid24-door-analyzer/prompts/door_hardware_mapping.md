# Door → Hardware Set Mapping Prompt

For each door:
- Read door.hardware_set.
- Find matching hardware_set.
- If match exists and status is active, expand all hardware items under that door.
- If existing_to_remain, do not map new hardware.
- If no match, create QA issue.
- If hardware set has zero items, create QA issue.
