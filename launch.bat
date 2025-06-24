@echo off
echo Starting Unified Betting App...

REM Check if Python is installed
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if Node.js is installed
echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed! Please install Node.js.
    pause
    exit /b 1
)

REM Create and activate virtual environment
echo Setting up Python virtual environment...
cd backend
if not exist venv (
    echo Creating new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment!
        cd ..
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install requirements
echo Activating virtual environment and installing requirements...
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment!
    cd ..
    pause
    exit /b 1
)

echo Installing backend requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install backend requirements!
    cd ..
    pause
    exit /b 1
)
cd ..

REM Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
echo Running npm install...
call npm install
if errorlevel 1 (
    echo Failed to install frontend dependencies!
    cd ..
    pause
    exit /b 1
)
cd ..

REM Start the application
echo Starting application...
echo Current directory: %CD%
echo Starting Python launch script...
python launch.py
if errorlevel 1 (
    echo Failed to start the application!
    pause
    exit /b 1
)

pause 