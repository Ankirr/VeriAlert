@echo off
title VeriAlert — Disaster Intelligence & Veracity Platform
echo ==============================================================================
echo   VeriAlert — Multi-Agent AI Framework for Real-Time Disaster Intelligence
echo ==============================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python Virtual Environment
if not exist "backend\venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at backend\venv!
    echo Please create one and install dependencies using:
    echo   python -m venv backend\venv
    echo   backend\venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: 2. Check and start Docker services if Docker is running
echo [1/3] Checking Database and Redis Infrastructure...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo       Docker detected. Starting PostgreSQL and Redis containers...
    docker-compose up -d
) else (
    echo       [NOTICE] Docker is not running. Using built-in SQLite & Local Cache fallback.
)

:: 3. Open Web Browser
echo [2/3] Launching Web Browser at http://localhost:8000 ...
timeout /t 2 /nobreak >nul
start http://localhost:8000

:: 4. Start Uvicorn Server
echo [3/3] Starting VeriAlert FastAPI Server on http://localhost:8000 ...
echo       Press CTRL+C to terminate the server.
echo ==============================================================================
echo.
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
pause
