@echo off
echo.
echo ========================================
echo   UNIFIED BETTING APP - SETUP SCRIPT
echo ========================================
echo.
echo This script will set up all dependencies for the Unified Betting App.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo Python and Node.js found. Starting setup...
echo.

REM Run the Python setup script
python setup_dependencies.py

if errorlevel 1 (
    echo.
    echo Setup failed! Check the errors above.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SETUP COMPLETED SUCCESSFULLY!
echo ========================================
echo.
echo You can now run 'python launch.py' to start the application.
echo.
pause 