import os
import glob
import time
import json
import pandas as pd
import fitz  # PyMuPDF
import base64
from dotenv import load_dotenv
from openai import OpenAI


# Load env for API keys
load_dotenv(".env")

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# We import run_pipeline from the existing codebase
from pipeline import run_pipeline

def render_pdf_to_base64_images(pdf_path):
    doc = fitz.open(pdf_path)
    base64_images = []
    # Limit to first 10 pages for cost and token limits during QA
    for page_idx in range(min(len(doc), 10)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=100) # Lower DPI to save tokens
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_images.append(b64)
    return base64_images

def ask_llm_judge(base64_images, doors_json, hardware_json):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return {
            "accuracy_score": 0.0,
            "hallucinations": ["OPENAI_API_KEY is missing. Please add it to .env."],
            "missed_items": [],
            "math_errors": []
        }
        
    client = OpenAI(api_key=api_key)
    
    prompt = (
        "You are an expert QA Auditor for architectural construction schedules. "
        "I am providing you with rendered images of a PDF document containing Door Schedules and Hardware Schedules, "
        "as well as the JSON output of an automated extraction pipeline.\n\n"
        "Your task is to carefully cross-compare the JSON data against the visual tables in the images.\n"
        "Focus on:\n"
        "1. Hallucinations: Did the JSON invent doors or hardware components that are NOT in the images?\n"
        "2. Missed Items: Did the JSON miss any doors or hardware components that clearly exist in the images?\n"
        "3. Hardware Set Accuracy: Ensure the hardware sets mapped to doors match the images.\n\n"
        f"=== DOORS JSON ===\n{doors_json}\n\n"
        f"=== HARDWARE JSON ===\n{hardware_json}\n\n"
        "Return strictly valid JSON matching this schema:\n"
        "{\n"
        "  \"accuracy_score\": 95.0,\n"
        "  \"hallucinations\": [\"list of specific hallucinations\"],\n"
        "  \"missed_items\": [\"list of specific missed items\"],\n"
        "  \"math_errors\": [\"list of any math or aggregation errors\"]\n"
        "}"
    )
    
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }
    ]
    
    for b64 in base64_images:
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high"
            }
        })
        
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error calling OpenAI QA Judge: {e}")
        return {
            "accuracy_score": 0.0,
            "hallucinations": [str(e)],
            "missed_items": [],
            "math_errors": []
        }

def run_qa_benchmark(target_dir="pdfs", max_pdfs=5):
    print(f"Starting QA Benchmark on {target_dir} (Max PDFs: {max_pdfs})")
    
    pdf_files = glob.glob(os.path.join(target_dir, "**", "*.pdf"), recursive=True)
    pdf_files = [f for f in pdf_files if "PRD" not in f] # Skip PRD
    
    if not pdf_files:
        print("No PDFs found.")
        return
        
    pdf_files = pdf_files[:max_pdfs]
    results = []
    
    for i, pdf_path in enumerate(pdf_files):
        print(f"\n[{i+1}/{len(pdf_files)}] Processing {pdf_path}...")
        
        # 1. Run pipeline extraction
        try:
            from llm_extract import llm_config
            llm_config.set("openai", "gpt-4o-mini")
            
            df_doors, df_comp = run_pipeline(pdf_files=[pdf_path], use_rag=True)
            
            doors_json = df_doors.to_json(orient="records") if not df_doors.empty else "[]"
            hardware_json = df_comp.to_json(orient="records") if not df_comp.empty else "[]"
            
            # 2. Render Images
            b64_images = render_pdf_to_base64_images(pdf_path)
            
            # 3. QA LLM Judge
            print("  -> Asking LLM Judge...")
            qa_res = ask_llm_judge(b64_images, doors_json, hardware_json)
            
            # 4. Record Result
            results.append({
                "PDF_Name": os.path.basename(pdf_path),
                "Path": pdf_path,
                "Accuracy_Score": qa_res.get("accuracy_score", 0),
                "Hallucinations": " | ".join(qa_res.get("hallucinations", [])),
                "Missed_Items": " | ".join(qa_res.get("missed_items", [])),
                "Math_Errors": " | ".join(qa_res.get("math_errors", []))
            })
            
        except Exception as e:
            print(f"  -> Pipeline failed: {e}")
            results.append({
                "PDF_Name": os.path.basename(pdf_path),
                "Path": pdf_path,
                "Accuracy_Score": 0,
                "Hallucinations": f"Extraction Pipeline Error: {e}",
                "Missed_Items": "",
                "Math_Errors": ""
            })
            
    df_results = pd.DataFrame(results)
    df_results.to_csv("qa_report.csv", index=False)
    print("\nBenchmark Complete! Saved to qa_report.csv")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pdfs", type=int, default=5, help="Max PDFs to process")
    parser.add_argument("--dir", type=str, default="pdfs", help="Directory to scan")
    args = parser.parse_args()
    
    run_qa_benchmark(target_dir=args.dir, max_pdfs=args.max_pdfs)
