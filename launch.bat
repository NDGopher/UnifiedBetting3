@echo off
REM Unified Betting App Launcher
REM This batch file launches the app using launch.py, which now always starts the backend with uvicorn for WebSocket support.
REM No changes needed here unless you want to add more logging or checks.

python launch.py

REM If we get here, the script has exited
echo.
echo Application has stopped.
echo All processes and windows have been cleaned up.
echo.
pause 