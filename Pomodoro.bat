@echo off
setlocal
REM ==========================================
REM FocusFlow Launcher (Universal Version)
REM ==========================================

REM Get the script directory
set "PROJECT_PATH=%~dp0"
cd /d "%PROJECT_PATH%"

REM Check main.py
if not exist "main.py" (
    echo [ERROR] Incorrect path, main.py not found.
    pause
    exit /b
)

REM Check virtual environment
if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment ".venv" not found.
    echo Run: py -3.11 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b
)

echo Starting FocusFlow...
start "Pomodoro" ".venv\Scripts\pythonw.exe" "main.py"

exit
