# ==============================================================================
# VeriAlert — Multi-Agent AI Framework for Real-Time Disaster Intelligence
# Single-Command PowerShell Startup Launcher
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  VeriAlert — Multi-Agent AI Framework for Real-Time Disaster Intelligence" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Check Python Virtual Environment
$PythonExe = Join-Path $ScriptDir "backend\venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Virtual environment not found at backend\venv!" -ForegroundColor Red
    Write-Host "Please create one and install dependencies:"
    Write-Host "  python -m venv backend\venv"
    Write-Host "  backend\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# 2. Check Docker Infrastructure
Write-Host "[1/3] Checking Database and Redis Infrastructure..." -ForegroundColor Yellow
$DockerRunning = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) { $DockerRunning = $true }
} catch {
    $DockerRunning = $false
}

if ($DockerRunning) {
    Write-Host "      Docker active. Starting PostgreSQL and Redis containers..." -ForegroundColor Green
    docker-compose up -d
} else {
    Write-Host "      [NOTICE] Docker not running. Using built-in SQLite & Local Cache fallback." -ForegroundColor DarkYellow
}

# 3. Open Web Browser
Write-Host "[2/3] Launching Web Browser at http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process "http://localhost:8000"

# 4. Start Uvicorn Server
Write-Host "[3/3] Starting VeriAlert FastAPI Server on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "      Press CTRL+C to terminate the server." -ForegroundColor Gray
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location (Join-Path $ScriptDir "backend")
& $PythonExe -m uvicorn app.main:app --port 8000 --reload
