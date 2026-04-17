import requests
import json
import base64
from pathlib import Path
from config import OPENAI_API_KEY

def test():
    print("Testing OpenAI GPT-4o with Image payload and JSON mode...")
    
    # Read a tiny dummy image (1x1 pixel) just to trigger the vision API
    img_path = Path(r"C:\Users\muzaf\my_lab\sushmita_proj\pdfs\Project 2 _lessthan10doors(1).pdf")
    # Actually just send a tiny image base64
    tiny_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII="

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a test agent. Output JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this image in JSON. Output must be raw JSON."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{tiny_base64}"}}
            ]}
        ],
        "temperature": 0.0,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print("Status Code:", r.status_code)
        
        js = r.json()
        print("\n--- RAW JSON DUMP ---")
        print(json.dumps(js, indent=2))
        
        if "error" in js:
            print("\nFATAL ERROR:", js["error"]["message"])
            
    except Exception as e:
        print("Crash:", e)

if __name__ == "__main__":
    test()
