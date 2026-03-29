---
description: How to run Python commands in this project
---

# Python Virtual Environment

This project uses a **shared virtual environment** located at:

```
c:\Users\muzaf\my_lab\computervision\
```

## CRITICAL RULES

// turbo-all

1. **ALWAYS activate the venv before running any Python command:**
   ```powershell
   & "c:\Users\muzaf\my_lab\computervision\Scripts\Activate.ps1"
   ```

2. **Or directly use the venv Python executable:**
   ```powershell
   & "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe" <script.py>
   ```

3. **For pip installs, always use the venv pip:**
   ```powershell
   & "c:\Users\muzaf\my_lab\computervision\Scripts\pip.exe" install <package>
   ```

4. **For streamlit, use the venv streamlit:**
   ```powershell
   & "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe" run app.py
   ```

## NEVER use system Python

- Do NOT use `python` or `pip` directly — those point to the Windows Store Python 3.10.
- Always prefix with the full venv path or activate first.

## Installed packages (key ones)

- streamlit 1.32.2
- pdfplumber 0.11.9
- pandas 2.3.3
- pydantic 2.12.5
- requests 2.27.1
- openpyxl 3.1.5
- python-dotenv 1.2.1

## Working directory

The main application code lives in:
```
c:\Users\muzaf\my_lab\sushmita_proj\door_schedule_llm_rag\
```
