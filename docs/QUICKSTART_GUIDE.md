# Unified Betting App Quickstart Guide

## 1. Prerequisites
- Node.js (for frontend)
- Python 3.8+ (for backend)
- Chrome browser (for extensions)

## 2. Chrome Extensions

### A. BetBCK Helper Extension
- **Purpose:** Automates BetBCK search, shows always-on-top EV popup, and can auto-fill/search bets.
- **Setup:**
  1. Go to `chrome://extensions/` in Chrome.
  2. Enable Developer Mode.
  3. Click "Load unpacked" and select the `betbck_extension` folder.
  4. Pin the extension for easy access.
- **How it works:**
  - Listens for messages from the web app (via `window.postMessage`).
  - Automates BetBCK tab: focuses, searches, and shows a popup with real-time EV/NVP.
  - Handles login status and can auto re-login if credentials are pre-filled.

### B. (Optional) PTO/Other Extensions
- If you use a PTO extension, repeat the above steps for its folder.

## 3. Running the App

### A. Backend
- Install Python dependencies:
  ```sh
  cd backend
  pip install -r requirements.txt
  ```
- Start the backend:
  ```sh
  python -m uvicorn main:app --host 0.0.0.0 --port 5001 --reload
  ```

### B. Frontend
- Install Node dependencies:
  ```sh
  cd frontend
  npm install
  ```
- Start the frontend:
  ```sh
  npm start
  ```
- Open [http://localhost:3000](http://localhost:3000) in Chrome.

### C. Launch Scripts
- You can use `launch.bat` to start everything at once on Windows.
- For advanced users, consider Docker Compose for cross-platform deployment.

## 4. Missing Files on Fresh Load
- **config.json** (in `backend/`): Add your BetBCK credentials and API keys.
- **.env** files: If required, create and fill in environment variables as per README.
- **Chrome extension folders**: Not included in some distributions; download or clone from the repo.

## 5. How the Extensions Interact
- The web app sends messages to the extension using `window.postMessage`.
- The extension automates BetBCK in a separate tab, types search terms, and shows a popup with live odds/EV.
- The extension can detect if you are logged out and prompt for re-login.

## 6. Troubleshooting
- If you see "Receiving end does not exist" errors, reload the extension and the BetBCK tab.
- If the backend fails to start, check for missing dependencies or config files.
- For extension issues, check the Chrome extension page for errors and reload as needed.

## 7. Support
- See the main README for more details, or open an issue on GitHub if you get stuck. 