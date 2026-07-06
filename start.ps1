Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " Smart Coding - Multi-Server Launcher" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/3] Checking dependencies..." -ForegroundColor Yellow
$PythonExe = ""
if (Test-Path "C:\Users\SUFIYAN\AppData\Local\Programs\Python\Python314\python.exe") {
    $PythonExe = "C:\Users\SUFIYAN\AppData\Local\Programs\Python\Python314\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
}

if ($PythonExe) {
    Write-Host " - Python: OK ($PythonExe)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] python command not found. Please ensure Python is installed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    Exit
}

# Check NPM
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host " - Node/NPM: OK" -ForegroundColor Green
} else {
    Write-Host "[ERROR] npm command not found. Please ensure Node.js is installed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    Exit
}
Write-Host ""

# Launch Backend
Write-Host "[2/3] Launching FastAPI Backend Server..." -ForegroundColor Yellow
Write-Host "     Port: 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot/backend'; & '$PythonExe' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -WindowStyle Normal

# Launch Frontend
Write-Host "[3/3] Launching Next.js Frontend Server..." -ForegroundColor Yellow
Write-Host "     Port: 3000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot/frontend'; npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " Both servers have been launched in separate PowerShell windows:" -ForegroundColor Cyan
Write-Host "  - Backend API URL:    http://localhost:8000" -ForegroundColor White
Write-Host "  - Backend Swagger UI: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Frontend App URL:   http://localhost:3000" -ForegroundColor White
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
