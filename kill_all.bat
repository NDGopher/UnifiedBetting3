@echo off
echo Killing all Unified Betting processes...

echo Force killing Chrome processes...
taskkill /f /im chrome.exe 2>nul
taskkill /f /im chromedriver.exe 2>nul

echo Force killing Python processes...
taskkill /f /im python.exe 2>nul

echo Force killing Node processes...
taskkill /f /im node.exe 2>nul

echo Killing processes on ports 5001 and 3000-3010...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3001') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3002') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3003') do taskkill /f /pid %%a 2>nul

echo.
echo Cleanup complete!
echo Note: If Chrome shows a "restore pages" dialog, click "Don't restore"
pause 