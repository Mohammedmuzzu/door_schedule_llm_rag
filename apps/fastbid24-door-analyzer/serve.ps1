param(
    [int]$Port = 8503
)

$ErrorActionPreference = "Stop"

$Python = "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment Python not found: $Python"
}

Set-Location -LiteralPath $Root
Write-Host "Serving FastBid24 Door Analyzer at http://127.0.0.1:$Port/"
& $Python -m http.server $Port --bind 127.0.0.1
