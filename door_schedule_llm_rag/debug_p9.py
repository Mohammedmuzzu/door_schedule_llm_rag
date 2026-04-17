import logging
from pathlib import Path
from page_extractor import extract_structured_page
from llm_extract import _openai_chat
from prompts import build_door_prompt

def debug_project_9():
    pdf_path = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project -9_lessthan10doors\Project -9\Door Schedule and Hardware Set.pdf")
    # This precisely mimics the bulk_qa logic so we can inspect the exact mapped string chunk:
    text_chunk, pg_type, is_cont, base64_image = extract_structured_page(pdf_path, 0)
    
    prompt = build_door_prompt([], text_chunk, max_chars=16000)
    
    print("= TEXT CHUNK EXTRACTED FROM PAGE =")
    print(text_chunk[:1500])
    print("\n= SENDING API PAYLOAD =")
    
    content = _openai_chat(prompt["system"], prompt["user"], force_json=False, base64_image=base64_image)
    
    with open("project_9_debug_output.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Debug output written to project_9_debug_output.txt")

if __name__ == "__main__":
    debug_project_9()
