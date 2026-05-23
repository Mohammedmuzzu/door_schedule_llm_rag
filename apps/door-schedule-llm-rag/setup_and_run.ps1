# Launch the Door Schedule LLM RAG Streamlit app.

$ErrorActionPreference = "Stop"

$Streamlit = "c:\Users\muzaf\my_lab\computervision\Scripts\streamlit.exe"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $Streamlit)) {
    throw "Streamlit not found in required virtual environment: $Streamlit"
}

Set-Location -LiteralPath $AppRoot
& $Streamlit run app.py
