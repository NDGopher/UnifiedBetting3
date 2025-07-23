@echo off
echo 🎯 Starting BuckeyeScraper EV Server (Simple Mode)
echo.
echo This server matches the original NDGopher pattern:
echo - No automatic scraping on startup
echo - Manual button clicks only
echo - Simple Flask server
echo.

cd backend
python simple_buckeye_server.py

pause 