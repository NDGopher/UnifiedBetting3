@echo off
REM Manual Dependency Setup for Unified Betting App
REM Run this if launch.bat gets stuck at dependency installation

echo.
echo ========================================
echo   UNIFIED BETTING APP - MANUAL SETUP
echo ========================================
echo.

echo [INFO] Starting manual dependency setup...
echo [INFO] This will install all required packages
echo.

python setup_dependencies.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All dependencies installed successfully!
    echo [INFO] You can now run 'launch.bat' to start the application
) else (
    echo.
    echo [ERROR] Setup failed. Please check the error messages above.
    echo [INFO] You may need to:
    echo [INFO]   1. Check your internet connection
    echo [INFO]   2. Make sure Python 3.8+ is installed
    echo [INFO]   3. Make sure Node.js 16+ is installed
)

echo.
pause 