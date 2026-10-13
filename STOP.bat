@echo off
title Stop AI Recruitment Agent
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  pause
  exit /b 1
)
python stop.py
pause
