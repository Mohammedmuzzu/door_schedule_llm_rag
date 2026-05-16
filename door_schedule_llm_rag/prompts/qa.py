"""Prompt templates for extraction QA judging."""


QA_AUDITOR_PROMPT_TEMPLATE = (
    "You are an expert QA Auditor for architectural construction schedules. "
    "I am providing you with rendered images of a PDF document containing Door Schedules and Hardware Schedules, "
    "as well as the JSON output of an automated extraction pipeline.\n\n"
    "Your task is to carefully cross-compare the JSON data against the visual tables in the images.\n"
    "Focus on:\n"
    "1. Hallucinations: Did the JSON invent doors or hardware components that are NOT in the images?\n"
    "2. Missed Items: Did the JSON miss any doors or hardware components that clearly exist in the images?\n"
    "3. Hardware Set Accuracy: Ensure the hardware sets mapped to doors match the images.\n\n"
    "=== DOORS JSON ===\n{doors_json}\n\n"
    "=== HARDWARE JSON ===\n{hardware_json}\n\n"
    "Return strictly valid JSON matching this schema:\n"
    "{{\n"
    "  \"accuracy_score\": 95.0,\n"
    "  \"hallucinations\": [\"list of specific hallucinations\"],\n"
    "  \"missed_items\": [\"list of specific missed items\"],\n"
    "  \"math_errors\": [\"list of any math or aggregation errors\"]\n"
    "}}"
)
