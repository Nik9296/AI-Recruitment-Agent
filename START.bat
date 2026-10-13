@echo off
title AI Recruitment Agent
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  echo Install Python from https://www.python.org/downloads/
  pause
  exit /b 1
)
python run.py
pause
