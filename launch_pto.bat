@echo off
title PTO Scraper Launcher
color 0A

echo.
echo ========================================
echo    PTO Scraper Setup and Launcher
echo ========================================
echo.

:menu
echo Choose an option:
echo 1. Setup PTO Chrome Profile (First Time)
echo 2. Test Existing Profile
echo 3. Backup Current Profile
echo 4. Restore Profile from Backup
echo 5. Export Profile to File
echo 6. Import Profile from File
echo 7. Launch PTO Scraper
echo 8. Launch Full App (Backend + Frontend)
echo 9. Exit
echo.

set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto test
if "%choice%"=="3" goto backup
if "%choice%"=="4" goto restore
if "%choice%"=="5" goto export
if "%choice%"=="6" goto import
if "%choice%"=="7" goto launch_scraper
if "%choice%"=="8" goto launch_full
if "%choice%"=="9" goto exit
goto menu

:setup
echo.
echo Setting up PTO Chrome Profile...
cd backend
python setup_pto_profile.py
cd ..
echo.
pause
goto menu

:test
echo.
echo Testing existing profile...
cd backend
python setup_pto_profile.py
cd ..
echo.
pause
goto menu

:backup
echo.
echo Creating backup of current profile...
cd backend
python profile_manager.py
cd ..
echo.
pause
goto menu

:restore
echo.
echo Restoring profile from backup...
cd backend
python profile_manager.py
cd ..
echo.
pause
goto menu

:export
echo.
echo Exporting profile to file...
cd backend
python profile_manager.py
cd ..
echo.
pause
goto menu

:import
echo.
echo Importing profile from file...
cd backend
python profile_manager.py
cd ..
echo.
pause
goto menu

:launch_scraper
echo.
echo Launching PTO Scraper...
cd backend
echo Starting backend server...
start "PTO Backend" cmd /k "python main.py"
cd ..
echo.
echo Backend server started on http://localhost:5001
echo You can now access the PTO scraper API endpoints.
echo.
pause
goto menu

:launch_full
echo.
echo Launching Full Application...
echo.

echo Starting backend server...
cd backend
start "PTO Backend" cmd /k "python main.py"
cd ..

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo Starting frontend...
cd frontend
start "PTO Frontend" cmd /k "npm start"
cd ..

echo.
echo Full application launched!
echo Backend: http://localhost:5001
echo Frontend: http://localhost:3000
echo.
echo Press any key to return to menu...
pause >nul
goto menu

:exit
echo.
echo Goodbye!
exit 