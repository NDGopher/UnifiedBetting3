@echo off
title Unified Betting App Shutdown
echo ========================================
echo    UNIFIED BETTING APP SHUTDOWN
echo ========================================
echo.
echo Cleaning up all processes and windows...
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

REM Run cleanup script
python -c "
import psutil
import time
import subprocess
import sys

print('🔍 Looking for processes to clean up...')

# Kill processes on our ports
ports = [5001, 3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007, 3008, 3009, 3010]
for port in ports:
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections():
                if conn.laddr.port == port:
                    print(f'Killing process on port {port}')
                    proc.terminate()
                    time.sleep(0.5)
        except:
            pass

# Close Chrome windows related to the app
target_keywords = [
    'pinnacleoddsdropper.com',
    'betbck.com', 
    'localhost:3000',
    'localhost:5001',
    'unified betting',
    'POD',
    'PTO'
]

print('🔍 Looking for Chrome windows to close...')
chrome_closed = False
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] and 'chrome' in proc.info['name'].lower():
            cmdline = ' '.join(proc.info['cmdline'] or [])
            for keyword in target_keywords:
                if keyword.lower() in cmdline.lower():
                    print(f'Closing Chrome window with keyword: {keyword}')
                    try:
                        proc.terminate()
                        time.sleep(0.5)
                        chrome_closed = True
                    except:
                        pass
                    break
    except:
        pass

if not chrome_closed:
    print('No Chrome windows found to close')

print('✅ Cleanup complete!')
"

echo.
echo Cleanup finished!
echo All processes and windows have been stopped.
echo.
pause 