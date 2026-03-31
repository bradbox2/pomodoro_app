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

REM Check and activate virtual environment
if not exist "envipomo\Scripts\activate.bat" (
    echo [ERROR] Virtual environment "envipomo" not found.
    pause
    exit /b
)

echo Starting FocusFlow...
call "envipomo\Scripts\activate.bat"
start "Pomodoro" pythonw.exe main.py

exit