@echo off
setlocal
REM ==========================================
REM FocusFlow Launcher (Auto-detect Path)
REM ==========================================

REM Get the absolute path of the script's directory
set "PROJECT_PATH=%~dp0"
cd /d "%PROJECT_PATH%"

REM Check if main.py exists
if not exist "main.py" (
    echo [ERROR] main.py not found. Ensure the script is in the project root.
    echo Current Directory: %cd%
    pause
    exit /b
)

REM Check if the virtual environment exists
if not exist ".venv\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment ".venv" not found.
    echo Run: py -3.11 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b
)

REM ==========================================
REM Launch Application (No Console Window)
REM ==========================================
echo Starting FocusFlow, please wait...

REM Use pythonw.exe to launch without a console window
start "FocusFlow" ".venv\Scripts\pythonw.exe" "main.py"

REM Exit the script
exit
