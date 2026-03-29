# Setup and run LLM extraction pipeline
# 1. Ensure Ollama is installed (https://ollama.com) and running
# 2. Pull llama3.2, then run extraction on all PDFs

$ErrorActionPreference = "Stop"
$ollamaUrl = "http://localhost:11434"

Write-Host "Checking Ollama..." -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "$ollamaUrl/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Ollama is running." -ForegroundColor Green
} catch {
    Write-Host "Ollama is not running or not installed." -ForegroundColor Red
    Write-Host "1. Install from https://ollama.com"
    Write-Host "2. Start Ollama (it may start with Windows or run 'ollama serve')"
    Write-Host "3. Run this script again."
    exit 1
}

$models = $r.models | ForEach-Object { $_.name }
if ($models -notmatch "llama3.2") {
    Write-Host "Pulling llama3.2 (one-time download)..." -ForegroundColor Cyan
    & ollama pull llama3.2
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to pull model. Run manually: ollama pull llama3.2" -ForegroundColor Red
        exit 1
    }
    Write-Host "Done." -ForegroundColor Green
} else {
    Write-Host "llama3.2 already present." -ForegroundColor Green
}

Write-Host "Running extraction pipeline on all PDFs..." -ForegroundColor Cyan
python run_llm_pipeline.py
Write-Host "Output folder: extracted_data\" -ForegroundColor Green
