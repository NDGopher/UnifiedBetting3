@echo off
echo ========================================
echo UPDATING MAIN BRANCH WITH ALL FILES
echo ========================================
echo.

echo Step 1: Adding all current files...
git add .

echo.
echo Step 2: Committing current state...
git commit -m "UPDATE: Clean repository with all latest improvements - Database integration, real-time WebSocket updates, smart alert lifecycle, enhanced frontend, comprehensive logging, system stability"

echo.
echo Step 3: Pushing to main branch...
git push origin main

echo.
echo ========================================
echo MAIN BRANCH UPDATED!
echo ========================================
echo.
echo Your main branch now has all the latest files:
echo - All backend improvements
echo - All frontend enhancements  
echo - Database integration
echo - Real-time WebSocket updates
echo - Smart alert lifecycle management
echo - Enhanced logging and debugging
echo - System stability improvements
echo.
echo Repository: https://github.com/NDGopher/UnifiedBetting3
echo.
pause 