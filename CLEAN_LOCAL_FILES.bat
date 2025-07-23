@echo off
echo ========================================
echo CLEANING LOCAL COMMIT FILES
echo ========================================
echo.

echo Removing commit files from local directory...

del COMMIT_MESSAGE.md
del commit_to_github.md
del CLEANUP_SUMMARY.md
del force_commit.bat
del force_commit.ps1
del force_commit.py
del force_commit_fixed.bat
del simple_commit.bat
del COMMIT_NOW.bat
del COMMIT_NOW.ps1
del FORCE_PUSH_FIX.bat
del FIX_BRANCH_AND_CLEAN.bat
del MANUAL_FIX_COMMANDS.md

echo.
echo ========================================
echo LOCAL FILES CLEANED!
echo ========================================
echo.
echo All commit files have been removed from your local directory.
echo Your project is now completely clean!
echo.
echo Repository: https://github.com/NDGopher/UnifiedBetting3
echo.
pause 