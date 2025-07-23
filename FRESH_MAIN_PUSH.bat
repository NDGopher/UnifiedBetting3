@echo off
echo ========================================
echo FRESH PUSH TO MAIN BRANCH
echo ========================================
echo.

echo Step 1: Checking current branch...
git branch

echo.
echo Step 2: Adding ALL files to staging...
git add -A

echo.
echo Step 3: Checking what files are staged...
git status

echo.
echo Step 4: Committing ALL changes...
git commit -m "COMPLETE: UnifiedBetting3 system with all improvements - Database integration, real-time WebSocket updates, smart alert lifecycle, enhanced frontend, comprehensive logging, system stability, clean repository"

echo.
echo Step 5: Force pushing to main branch...
git push --force origin master:main

echo.
echo ========================================
echo FRESH PUSH COMPLETED!
echo ========================================
echo.
echo Check your repository: https://github.com/NDGopher/UnifiedBetting3
echo.
echo If it still doesn't show all files, we may need to:
echo 1. Create a new repository
echo 2. Or reset the git history
echo.
pause 