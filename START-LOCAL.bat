@echo off
title AI Recruitment Agent (no Docker)
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 or newer from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during install.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo Install Node.js LTS from https://nodejs.org/
  pause
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python virtual environment...
  python -m venv .venv
)

echo Installing Python packages...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo pip install failed.
  pause
  exit /b 1
)

echo Checking database...
".venv\Scripts\python.exe" -c "import socket; s=socket.create_connection(('127.0.0.1',5432),3); s.close()"
if errorlevel 1 (
  echo PostgreSQL is not running on localhost:5432.
  echo Install PostgreSQL 16, set user/password to postgres/postgres,
  echo create a database named recruitment, then double-click this file again.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  echo Database setup failed. Create database "recruitment" as user postgres.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" scripts\seed_recruiter_dashboard.py

if not exist "frontend\node_modules" (
  echo Installing dashboard packages...
  pushd frontend
  call npm install
  popd
)

echo Starting API and dashboard...
start "AI Recruitment API" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "AI Recruitment Dashboard" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 8 /nobreak >nul
start http://localhost:3000

echo.
echo Opened http://localhost:3000
echo Login: recruiter
echo Password: recruiter-review
echo.
echo Leave the two black windows open. Close them or use STOP-LOCAL.bat to stop.
pause
