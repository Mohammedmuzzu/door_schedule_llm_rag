$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe"

Push-Location $BackendDir
try {
  & $Python app.py
}
finally {
  Pop-Location
}
