# Unified Betting App - Shutdown Guide

## 🚀 Starting the App

Use the `launch.bat` file to start the entire application:

```bash
launch.bat
```

This will:
- Start the backend server (FastAPI on port 5001)
- Start the frontend server (React on port 3000)
- Open Pinnacle Odds Dropper in Chrome
- Launch PTO scraper
- Open BetBCK in Chrome

## 🛑 Stopping the App

### Option 1: Close the PowerShell Window (Recommended)
Simply close the PowerShell window that runs `launch.bat`. The script will automatically:
- Stop the backend process
- Stop the frontend process
- Close all Chrome windows related to the app (POD, BetBCK, PTO)
- Kill any processes on ports 5001, 3000-3010
- Clean up all child processes

### Option 2: Use Ctrl+C
Press `Ctrl+C` in the PowerShell window to gracefully shut down all services.

### Option 3: Manual Shutdown Script
If you need to manually clean up everything, run:

```bash
shutdown.bat
```

This will forcefully clean up all processes and Chrome windows.

## 🔧 What Gets Cleaned Up

When you close the PowerShell window, the system automatically:

1. **Stops Backend Process**
   - FastAPI server on port 5001
   - PTO scraper
   - All Python processes

2. **Stops Frontend Process**
   - React development server
   - Node.js processes

3. **Closes Chrome Windows**
   - Pinnacle Odds Dropper tabs
   - BetBCK tabs
   - Localhost:3000 (frontend)
   - Localhost:5001 (backend API)
   - Any tabs with "POD" or "PTO" in the URL

4. **Kills Port Processes**
   - Any process using ports 5001, 3000-3010

## 🚨 Troubleshooting

### If Chrome Windows Don't Close
Sometimes Chrome windows might not close automatically. In this case:
1. Run `shutdown.bat` to force cleanup
2. Or manually close the Chrome tabs

### If Ports Are Still in Use
If you get "port already in use" errors when restarting:
1. Run `shutdown.bat` to kill all processes
2. Wait a few seconds
3. Try `launch.bat` again

### If Processes Are Stuck
If processes are stuck and won't terminate:
1. Open Task Manager
2. Look for Python, Node.js, or Chrome processes
3. End them manually
4. Run `shutdown.bat` to clean up

## 💡 Tips

- **Always use `launch.bat`** to start the app - this ensures proper process tracking
- **Close the PowerShell window** to stop everything cleanly
- **Use `shutdown.bat`** if you need to force cleanup
- The system will automatically install `psutil` if it's missing for process management

## 🔄 Restarting

To restart the app:
1. Close the current PowerShell window (this cleans up everything)
2. Wait a few seconds for cleanup to complete
3. Run `launch.bat` again

The app will start fresh with all processes properly managed. 