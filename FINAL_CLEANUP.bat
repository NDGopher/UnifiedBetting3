@echo off
echo ========================================
echo FINAL CLEANUP - REMOVING TEMP FILES
echo ========================================
echo.

echo Step 1: Removing temporary files from git tracking...
git rm --cached FRESH_MAIN_PUSH.bat
git rm --cached NUCLEAR_OPTION.bat
git rm --cached UPDATE_MAIN_BRANCH.bat
git rm --cached MANUAL_UPDATE_COMMANDS.md
git rm --cached CLEAN_LOCAL_FILES.bat
git rm --cached FINAL_PUSH_TO_MAIN.bat

echo.
echo Step 2: Deleting temporary files locally...
del FRESH_MAIN_PUSH.bat
del NUCLEAR_OPTION.bat
del UPDATE_MAIN_BRANCH.bat
del MANUAL_UPDATE_COMMANDS.md
del CLEAN_LOCAL_FILES.bat
del FINAL_PUSH_TO_MAIN.bat

echo.
echo Step 3: Adding the clean state...
git add .

echo.
echo Step 4: Committing the clean repository...
git commit -m "CLEAN: Final clean repository - UnifiedBetting3 system with all improvements - Database integration, real-time WebSocket updates, smart alert lifecycle, enhanced frontend, comprehensive logging, system stability"

echo.
echo Step 5: Pushing clean repository to main...
git push origin main

echo.
echo ========================================
echo FINAL CLEANUP COMPLETED!
echo ========================================
echo.
echo Your repository is now completely clean:
echo - All temporary files removed
echo - All commit files removed
echo - Clean, professional repository
echo - All your improvements preserved
echo.
echo Repository: https://github.com/NDGopher/UnifiedBetting3
echo.
pause 