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

REM Install psutil if not available
python -c "import psutil" 2>nul || (
    echo Installing psutil for process management...
    python -m pip install psutil
)

REM Launch the application
python launch.py

REM If we get here, the script has exited
echo.
echo Application has stopped.
echo All processes and windows have been cleaned up.
echo.
pause 