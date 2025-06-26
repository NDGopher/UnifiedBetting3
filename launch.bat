@echo off
title Unified Betting App Launcher
echo ========================================
echo    UNIFIED BETTING APP LAUNCHER
echo ========================================
echo.
echo Starting the application...
echo Close this window to stop all services and clean up.
echo.
cd /d %~dp0

REM Install psutil and pywin32 if not available
python -c "import psutil" 2>nul || (
    echo Installing psutil for process management...
    python -m pip install psutil
)

python -c "import win32api" 2>nul || (
    echo Installing pywin32 for Windows signal handling...
    python -m pip install pywin32
)

REM Launch the application
python launch.py

REM If we get here, the script has exited
echo.
echo Application has stopped.
echo All processes and windows have been cleaned up.
echo.
pause 