# One-command local setup for a new Windows laptop.
# Requires Docker Desktop.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed. Install Docker Desktop, start it, then run this script again."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
    Write-Host "Optional: add GOOGLE_API_KEY to .env if you want JD analysis."
} else {
    Write-Host "Using existing .env (not overwritten)"
}

Write-Host "Starting Postgres, API, dashboard, and demo seed..."
docker compose up --build -d

$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/ready" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host "API is still starting. Check: docker compose logs backend"
} else {
    Write-Host "API is ready."
}

Write-Host ""
Write-Host "Dashboard:  http://localhost:3000"
Write-Host "API docs:   http://127.0.0.1:8000/docs"
Write-Host "Login:      recruiter  /  recruiter-review"
Write-Host "(unless you changed RECRUITER_USERNAME / RECRUITER_PASSWORD in .env)"
Write-Host ""
Write-Host "Stop later with: docker compose down"
