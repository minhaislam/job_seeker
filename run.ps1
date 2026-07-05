# Job Seeker App - PowerShell launcher
Write-Host "Starting Job Seeker App..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found." -ForegroundColor Red
    Write-Host "Copy .env.example to .env and add your ANTHROPIC_API_KEY"
    exit 1
}

$fastapiInstalled = pip show fastapi 2>$null
if (-not $fastapiInstalled) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host ""
Write-Host "App running at: http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop"
Write-Host ""

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
