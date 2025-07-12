@echo off
cd /d "%~dp0"
echo Starting PTO Profile Setup...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Change to backend directory
if not exist "backend" (
    echo ERROR: backend directory not found
    echo Please run this script from the UnifiedBetting2 root directory
    pause
    exit /b 1
)

cd backend

REM Check if setup_pto_profile.py exists
if not exist "setup_pto_profile.py" (
    echo ERROR: setup_pto_profile.py not found in backend directory
    pause
    exit /b 1
)

echo Running PTO Profile Setup...
python setup_pto_profile.py

echo.
echo Setup complete!
pause 