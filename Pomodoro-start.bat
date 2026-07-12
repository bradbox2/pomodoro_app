@echo off
setlocal
REM ==========================================
REM FocusFlow Launcher (no console window)
REM ==========================================

REM Resolve the project root (this script's directory)
set "PROJECT_PATH=%~dp0"
cd /d "%PROJECT_PATH%"

REM Check the application package
if not exist "src\focusflow\main.py" (
    echo [ERROR] src\focusflow\main.py not found. Run this from the project root.
    echo Current Directory: %cd%
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

REM Launch without a console window
set "PYTHONPATH=%PROJECT_PATH%src"
echo Starting FocusFlow, please wait...
start "FocusFlow" ".venv\Scripts\pythonw.exe" -m focusflow

exit
