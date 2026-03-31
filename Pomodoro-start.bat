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
if not exist "envipomo\Scripts\pythonw.exe" (
    echo [ERROR] Virtual environment "envipomo" not found.
    echo Please ensure you have created the environment as per README.md.
    pause
    exit /b
)

REM ==========================================
REM Launch Application (No Console Window)
REM ==========================================
echo Starting FocusFlow, please wait...

REM Use pythonw.exe to launch without a console window
start "FocusFlow" "envipomo\Scripts\pythonw.exe" "main.py"

REM Exit the script
exit
