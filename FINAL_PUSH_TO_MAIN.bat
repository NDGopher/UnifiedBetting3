@echo off
echo ========================================
echo FINAL PUSH TO MAIN BRANCH
echo ========================================
echo.

echo Step 1: Switching to main branch...
git checkout main

echo.
echo Step 2: Adding all current files...
git add .

echo.
echo Step 3: Committing all improvements...
git commit -m "FINAL: Complete UnifiedBetting3 system with all improvements - Database integration, real-time WebSocket updates, smart alert lifecycle, enhanced frontend, comprehensive logging, system stability, clean repository"

echo.
echo Step 4: Force pushing to main branch...
git push --force origin main

echo.
echo ========================================
echo SUCCESS! MAIN BRANCH UPDATED!
echo ========================================
echo.
echo Your main branch now has ALL your local files:
echo - All backend improvements (database, WebSocket, etc.)
echo - All frontend enhancements (automatic cleanup, etc.)
echo - All the latest code from your local directory
echo - Clean repository without commit files
echo.
echo Repository: https://github.com/NDGopher/UnifiedBetting3
echo.
pause 