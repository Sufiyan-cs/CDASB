@echo off
:: Setup window styling
color 0B
title Smart Coding - Server Launcher

echo =====================================================================
echo  Smart Coding - Multi-Server Launcher
echo =====================================================================
echo.

:: Detect Python executable
echo [1/3] Checking dependencies...
set "PYTHON_EXE="

if exist "C:\Users\SUFIYAN\AppData\Local\Programs\Python\Python314\python.exe" (
    set "PYTHON_EXE=C:\Users\SUFIYAN\AppData\Local\Programs\Python\Python314\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python not found. Please ensure Python is installed and added to PATH.
    pause
    exit /b 1
)
echo  - Python: OK (%PYTHON_EXE%)

:: Detect NPM
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm command not found. Please ensure Node.js is installed and added to PATH.
    pause
    exit /b 1
)
echo  - Node/NPM: OK
echo.

:: Launch Backend
echo [2/3] Launching FastAPI Backend Server...
echo      Port: 8000
echo      Command: "%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
start "Smart Coding - Backend (FastAPI)" cmd /k "cd /d "%~dp0backend" && "%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Launch Frontend
echo [3/3] Launching Next.js Frontend Server...
echo      Port: 3000
echo      Command: npm run dev
start "Smart Coding - Frontend (Next.js)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo =====================================================================
echo  Both servers have been launched in separate windows:
echo   - Backend API URL:    http://localhost:8000
echo   - Backend Swagger UI: http://localhost:8000/docs
echo   - Frontend App URL:   http://localhost:3000
echo =====================================================================
echo.
echo Press any key to close this launcher (servers will keep running in their own windows).
pause >nul
