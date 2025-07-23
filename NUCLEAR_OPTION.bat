@echo off
echo ========================================
echo NUCLEAR OPTION - FRESH START
echo ========================================
echo.

echo Step 1: Removing git folder to start fresh...
rmdir /s /q .git

echo.
echo Step 2: Initializing new git repository...
git init

echo.
echo Step 3: Adding remote origin...
git remote add origin https://github.com/NDGopher/UnifiedBetting3.git

echo.
echo Step 4: Adding ALL files...
git add -A

echo.
echo Step 5: Creating initial commit with everything...
git commit -m "INITIAL: Complete UnifiedBetting3 system with all improvements - Database integration, real-time WebSocket updates, smart alert lifecycle, enhanced frontend, comprehensive logging, system stability, clean repository"

echo.
echo Step 6: Force pushing to main branch...
git push --force origin master:main

echo.
echo ========================================
echo NUCLEAR OPTION COMPLETED!
echo ========================================
echo.
echo This should have pushed ALL your files to main branch.
echo Check: https://github.com/NDGopher/UnifiedBetting3
echo.
pause 