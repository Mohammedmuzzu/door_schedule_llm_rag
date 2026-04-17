import logging
from pathlib import Path
import pdfplumber
from prompts import build_door_prompt
from llm_extract import _openai_chat

def debug_project_9():
    pdf_path = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -9_lessthan10doors\Project -9\Door Schedule and Hardware Set.pdf")
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[0].extract_text()
        
    prompt = build_door_prompt([], text, max_chars=16000)
    print("Sending prompt to OpenAI...")
    
    # We will pass base64_image=None for this purely text test to see how the raw JSON array falls apart.
    content = _openai_chat(prompt["system"], prompt["user"], force_json=False, base64_image=None)
    
    with open("project_9_debug_output.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Debug output written to project_9_debug_output.txt")

if __name__ == "__main__":
    debug_project_9()
