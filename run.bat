@echo off
echo Starting Job Seeker App...

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found.
    echo Copy .env.example to .env and add your ANTHROPIC_API_KEY
    pause
    exit /b 1
)

REM Install dependencies if needed
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo.
echo App running at: http://localhost:8000
echo Press Ctrl+C to stop
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
