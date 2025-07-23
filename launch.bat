@echo off
echo.
echo ========================================
echo   UNIFIED BETTING APP - ONE CLICK
echo ========================================
echo.
echo Starting Unified Betting Application...
echo.

REM Run the Python launcher
python launch.py

REM If Python launcher fails, try setup first
if errorlevel 1 (
    echo.
    echo Launcher failed. Running setup first...
    echo.
    python setup_dependencies.py
    if errorlevel 1 (
        echo.
        echo Setup failed! Please check the errors above.
        pause
        exit /b 1
    )
    echo.
    echo Setup completed. Trying launcher again...
    echo.
    python launch.py
)

pause 