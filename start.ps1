# ResearchMind AI - One-click startup
Write-Host "Starting ResearchMind AI..." -ForegroundColor Cyan

# Start backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\venv\Scripts\activate; uvicorn app.main:app --reload --port 8000"

# Start frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npx serve . -p 5500"

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "Backend:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5500" -ForegroundColor Green
Write-Host ""

# Open browser
Start-Process "http://localhost:5500"
