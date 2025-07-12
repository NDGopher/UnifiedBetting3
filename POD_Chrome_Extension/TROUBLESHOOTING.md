# POD Chrome Extension Troubleshooting Guide

## Issues Found and Fixed:

### 1. ✅ **Backend Server Not Running**
- **Problem**: Extension was trying to send data to `http://localhost:5001/pod_alert` but no server was running
- **Solution**: Started FastAPI backend server on port 5001
- **Command**: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 5001`

### 2. ✅ **Invalid JSON in manifest.json**
- **Problem**: Comments in JSON file made it invalid
- **Solution**: Removed comments from manifest.json
- **Fixed**: Lines 4 and 16 had invalid comments

### 3. ✅ **Wrong Server Path in start_server.bat**
- **Problem**: start_server.bat was pointing to wrong directory
- **Solution**: Updated to point to correct backend directory

## How to Test if Extension is Working:

### 1. Check Backend Server
```bash
curl http://localhost:5001/test
```
Should return: `{"status":"success","message":"Backend is working!"}`

### 2. Check Extension in Chrome
1. Go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `POD_Chrome_Extension` folder
4. Check for any errors in the extension card

### 3. Test Extension on POD Terminal
1. Go to `https://www.pinnacleoddsdropper.com/terminal`
2. Open Chrome DevTools (F12)
3. Check Console for messages like:
   - "POD Content Script (Your Working Base - v5 EventId Focus) Loaded"
   - "POD Terminal: Found container"
   - "POD Terminal: MutationObserver is now active"

### 4. Test Communication
1. Open the test page: `POD_Chrome_Extension/test_extension.html`
2. Check if extension is detected and communicating

## Common Issues:

### Extension Not Loading
- Check manifest.json is valid JSON (no comments)
- Ensure all files are present
- Check Chrome extension errors

### No Alerts Being Sent
- Verify backend server is running on port 5001
- Check Chrome DevTools Console for errors
- Verify you're on the correct POD terminal page

### Background Script Issues
- Check background.js console logs
- Verify webRequest permissions are working
- Test message passing between content and background scripts

## Debugging Steps:

1. **Check Backend Logs**: Look at the terminal where you started the backend server
2. **Check Chrome Console**: Open DevTools on POD terminal page
3. **Check Extension Logs**: Go to `chrome://extensions/` and click "service worker" for background script logs
4. **Test API Endpoint**: Use curl or browser to test `http://localhost:5001/pod_alert`

## Restore from OneDrive (if needed):
If you need to restore from OneDrive backup:
```bash
# Copy from OneDrive backup
cp -r "C:\Users\steph\OneDrive\Desktop\DevProjects\scripts\pod_automation\pod_alert_extension - telegram version before updated HTML and server\*" "POD_Chrome_Extension\"
``` 