# 🎯 Unified Betting App

## ✅ Quick Checklist (Before You Start)

- [ ] Python 3.8+
- [ ] Node.js 16+
- [ ] Google Chrome browser
- [ ] Windows 10/11 (primary support)
- [ ] **BetBCK Chrome Extension** (from `betbck_extension/` in this repo, see below)
- [ ] **Pinnacle Odds Dropper (POD) Chrome Extension** (must be obtained separately, see below)
- [ ] (Optional but recommended) All Chrome windows closed before launching
- [ ] (First time only) PTO Chrome profile set up (`python backend/setup_pto_profile.py`)
- [ ] (First time only) Config files in place (see below)

A comprehensive betting automation platform that combines real-time odds analysis, automated scraping, and intelligent betting recommendations.

## 🚀 Features

### **Core Functionality**
- **Real-time EV Analysis**: Automatic calculation of Expected Value (EV) for betting opportunities
- **Multi-Source Integration**: Combines Pinnacle odds with BetBCK for arbitrage opportunities
- **POD (Pinnacle Odds Dropper) Integration**: Real-time alerts for odds movements
- **PTO (Prop Trading Opportunities) Scraper**: Automated prop bet monitoring
- **Chrome Extension**: Seamless BetBCK integration with one-click betting

### **Advanced Features**
- **Smart Process Management**: Automatic cleanup of all processes and Chrome windows
- **Beautiful PowerShell UI**: Colored output with progress indicators and status messages
- **Comprehensive Logging**: Detailed logging for positive EV changes and system events
- **Error Recovery**: Robust error handling and automatic retry mechanisms
- **Port Management**: Automatic port detection and conflict resolution

### **User Experience**
- **One-Click Launch**: Single `launch.bat` file starts everything
- **Automatic Cleanup**: Close PowerShell window to stop all services
- **Real-time Updates**: Live EV/NVP updates in the frontend
- **Browser Notifications**: Desktop alerts for high EV opportunities
- **Responsive Design**: Modern React frontend with Material-UI

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+**
- **Chrome Browser**
- **Windows 10/11** (primary support)

## 🛠️ Installation

### **Quick Start**
1. **Clone the repository**
   ```bash
   git clone https://github.com/NDGopher/UnifiedBetting2.git
   cd UnifiedBetting2
   ```

2. **Run the setup script**
   ```bash
   # On Windows:
   setup_dependencies.bat
   
   # On Mac/Linux:
   python setup_dependencies.py
   ```

3. **Launch the application**
   ```bash
   python launch.py
   ```

The setup script will automatically:
- Create a Python virtual environment
- Install all backend dependencies
- Install all frontend dependencies
- Verify everything is working

### **Manual Setup (Optional)**
If you prefer manual setup:

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

3. **PTO Profile Setup**
   ```bash
   cd backend
   python setup_pto_profile.py
   ```

## 🎮 Usage

### **Starting the App**
```bash
launch.bat
```

The app will start and display:
- Beautiful colored banner
- Progress indicators for each step
- Status messages with timestamps
- Success confirmation with all URLs

### **Stopping the App**
Simply **close the PowerShell window** that runs `launch.bat`. The system will automatically:
- Stop backend and frontend processes
- Close all Chrome windows (POD, BetBCK, PTO)
- Kill processes on ports 5001, 3000-3010
- Clean up all child processes

### **Alternative Stop Methods**
- **Ctrl+C**: Graceful shutdown
- **shutdown.bat**: Force cleanup for emergencies

## 🏗️ Architecture

### **Backend (FastAPI)**
- **Port**: 5001
- **Framework**: FastAPI with Uvicorn
- **Features**:
  - Real-time POD alert processing
  - BetBCK scraping automation
  - Pinnacle odds fetching
  - EV calculation engine
  - PTO scraper integration

### **Frontend (React)**
- **Port**: 3000 (auto-detected)
- **Framework**: React with TypeScript
- **UI**: Material-UI components
- **Features**:
  - Real-time EV display
  - POD alerts table
  - PTO props monitoring
  - EV calculator
  - One-click betting integration

### **Chrome Extension**
- **Location**: `betbck_extension/`
- **Features**:
  - BetBCK tab automation
  - Real-time EV/NVP popup
  - One-click bet placement
  - Auto-login handling

### **PTO Scraper**
- **Location**: `backend/pto_scraper.py`
- **Features**:
  - Automated prop bet monitoring
  - Chrome profile management
  - Real-time data extraction
  - Cloudflare bypass

## 📊 Components

### **POD Alerts**
- Real-time odds movement alerts
- EV calculation and filtering
- Positive EV market highlighting
- Browser notifications for high EV opportunities

### **EV Calculator**
- Manual EV calculations
- American/Decimal odds support
- Real-time results
- Kelly criterion integration

### **Prop Builder**
- PTO prop monitoring
- Real-time EV updates
- Sport filtering
- Direct BetBCK integration

## 🔧 Configuration

### **Backend Config** (`backend/config.json`)
```json
{
  "pto": {
    "chrome_user_data_dir": "path/to/chrome/profile",
    "enable_auto_scraping": true
  }
}
```

### **Chrome Extension**
- Automatically installed when launching
- No manual configuration required
- Uses `window.postMessage` for communication

## 🚨 Troubleshooting

### **Common Issues**

#### **Dependency Installation Hangs**
If the launch script gets stuck at "Installing backend dependencies...":

1. **Cancel the script** (Ctrl+C or close the window)
2. **Run the manual setup script**:
   ```bash
   python setup_dependencies.py
   ```
3. **Then try launching again**:
   ```bash
   launch.bat
   ```

**Alternative manual installation**:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ../frontend
npm install
```

#### **Port Already in Use**
```bash
shutdown.bat
# Wait a few seconds
launch.bat
```

#### **Chrome Windows Don't Close**
- Run `shutdown.bat` to force cleanup
- Or manually close Chrome tabs

#### **PTO Profile Issues**
```bash
cd backend
python setup_pto_profile.py
```

#### **Dependencies Missing**
The launch script automatically installs missing dependencies. If issues persist:
```bash
cd backend
pip install -r requirements.txt
cd ../frontend
npm install
```

### **Logs and Debugging**
- **Backend logs**: Displayed in PowerShell with color coding
- **Frontend logs**: Browser console (F12)
- **Extension logs**: Chrome DevTools for extension

## 📈 Performance

### **Optimizations**
- **Process Management**: Automatic cleanup prevents memory leaks
- **Port Detection**: Finds free ports automatically
- **Error Recovery**: Robust retry mechanisms
- **Caching**: Intelligent data caching for performance

### **Monitoring**
- Real-time process status
- Port usage monitoring
- Memory usage tracking
- Error rate monitoring

## 🔒 Security

### **Best Practices**
- **Local Development**: All services run locally
- **No Sensitive Data**: Config files excluded from git
- **Process Isolation**: Each component runs in separate process
- **Error Handling**: Comprehensive error catching

### **Sensitive Files**
The following files are excluded from git and should be added manually:
- `backend/config.json`
- `backend/.env`
- Chrome profile directories

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### **Code Style**
- **Python**: PEP 8 compliance
- **JavaScript/TypeScript**: ESLint configuration
- **React**: Functional components with hooks
- **Documentation**: Comprehensive docstrings

## 📝 Recent Updates

### **v2.0 - Major UI/UX Improvements**
- ✅ **Beautiful PowerShell UI**: Colored output with progress bars
- ✅ **Automatic Process Cleanup**: Close window to stop everything
- ✅ **Enhanced Logging**: Positive EV change notifications
- ✅ **Improved Error Handling**: Better error messages and recovery
- ✅ **Chrome Window Management**: Automatic cleanup of browser tabs

### **v1.5 - Stability Improvements**
- ✅ **Race Condition Fixes**: Eliminated shared state issues
- ✅ **EV Filtering**: Only shows realistic EV values (-20% to +20%)
- ✅ **Extension Messaging**: Robust communication without hardcoded IDs
- ✅ **Backend Robustness**: Better error handling and recovery

### **v1.0 - Core Features**
- ✅ **POD Integration**: Real-time odds alerts
- ✅ **BetBCK Scraping**: Automated odds collection
- ✅ **EV Calculation**: Real-time expected value analysis
- ✅ **Chrome Extension**: BetBCK automation
- ✅ **PTO Scraper**: Prop bet monitoring

## 📞 Support

### **Getting Help**
1. **Check the logs**: PowerShell output and browser console
2. **Run shutdown.bat**: Force cleanup and restart
3. **Check prerequisites**: Ensure Python/Node.js versions
4. **Review configuration**: Verify config.json setup

### **Common Commands**
```bash
# Start the app
launch.bat

# Force cleanup
shutdown.bat

# Manual backend start
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 5001

# Manual frontend start
cd frontend
npm start
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pinnacle Odds Dropper**: For real-time odds data
- **BetBCK**: For betting platform integration
- **Material-UI**: For beautiful React components
- **FastAPI**: For high-performance backend
- **Selenium**: For web automation

---

**🎯 Ready to start betting smarter? Run `launch.bat` and let the automation begin!**

## 🚨 Required Chrome Extensions

### 1. **BetBCK Chrome Extension**
- **Location:** This repo, in the `betbck_extension/` folder.
- **How to install:**
  1. Open Chrome and go to `chrome://extensions/`
  2. Enable **Developer mode** (top right)
  3. Click **Load unpacked**
  4. Select the `betbck_extension/` folder from this repo

### 2. **Pinnacle Odds Dropper (POD) Chrome Extension**
- **Location:** _Not included in this repo_ (must be obtained separately)
- **How to install:**
  1. Obtain the extension from the official source or your team
  2. Open Chrome and go to `chrome://extensions/`
  3. Enable **Developer mode**
  4. Click **Load unpacked**
  5. Select the folder containing the POD extension

**⚠️ Both extensions must be loaded and enabled in Chrome for the Unified Betting App to function correctly.**

## 🔧 Troubleshooting

### Common Issues

#### "No pyvenv.cfg file" Error
**Problem:** Virtual environment is missing or corrupted.

**Solution:** Run the setup script again:
```bash
python setup_dependencies.py
```

#### "Failed to upgrade pip" Error
**Problem:** Pip upgrade fails but installation continues.

**Solution:** This is usually harmless. The app will still work. If you want to fix it:
```bash
cd backend
venv\Scripts\python -m pip install --upgrade pip --force-reinstall
```

#### "Module not found" Errors
**Problem:** Dependencies not installed properly.

**Solution:** Reinstall dependencies:
```bash
cd backend
venv\Scripts\pip install -r requirements.txt --no-cache-dir
```

#### Port Already in Use
**Problem:** Ports 3000 or 5001 are already occupied.

**Solution:** The launcher will automatically find free ports, or manually kill processes:
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:3000 | xargs kill -9
```

#### Chrome Profile Issues
**Problem:** PTO scraper can't access Chrome profile.

**Solution:** Set up PTO profile:
```bash
cd backend
python setup_pto_profile.py
```

### Manual Setup (If Automatic Setup Fails)

If the automatic setup fails, you can set up dependencies manually:

#### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

#### Frontend Setup
```bash
cd frontend
npm install
```

### System Requirements

- **Windows 10/11** (recommended) or **Mac/Linux**
- **8GB RAM** minimum (16GB recommended)
- **2GB free disk space**
- **Stable internet connection**

### Getting Help

If you're still having issues:

1. **Check the logs:** Look for error messages in the console output
2. **Verify prerequisites:** Make sure Python 3.8+ and Node.js 16+ are installed
3. **Check internet:** Ensure you have a stable internet connection
4. **Restart:** Sometimes a simple restart fixes issues
5. **Clean install:** Delete the `backend/venv` and `frontend/node_modules` folders and run setup again

## 📁 Project Structure

```
UnifiedBetting2/
├── backend/                 # Python backend
│   ├── venv/               # Virtual environment (auto-created)
│   ├── requirements.txt    # Python dependencies
│   └── ...
├── frontend/               # React frontend
│   ├── node_modules/       # Node.js dependencies (auto-created)
│   ├── package.json        # Frontend dependencies
│   └── ...
├── launch.py              # Main launcher script
├── setup_dependencies.py  # Dependency setup script
└── setup_dependencies.bat # Windows setup script
```

## 🔄 Updates

When you pull updates from GitHub:

1. **Run setup again** to ensure dependencies are up to date:
   ```bash
   python setup_dependencies.py
   ```

2. **Launch normally:**
   ```bash
   python launch.py
   ```

The setup script is smart enough to only install what's needed, so it's safe to run multiple times. 

## 🧹 OneDrive Sync Issues & Auto-Cleanup (Windows)

If you use this project inside a OneDrive-synced folder on Windows, you may encounter sync errors due to auto-generated folders like `.config` or `~` (especially inside `node_modules`). These are created by some dependencies and are not needed for backup or sync.

To prevent OneDrive sync issues:

1. **Run the cleanup script:**
   ```bash
   python scripts/onedrive_cleanup.py
   ```
   This will safely remove problematic folders/files that OneDrive can't sync. It will not touch your source code or important files.

2. **When to run:**
   - After running `npm install` or updating dependencies
   - Before committing or pushing code
   - Whenever you see OneDrive sync errors about `.config` or `~` folders

3. **What it does:**
   - Recursively deletes `.config` and `~` folders/files from the project
   - Prints what it removes
   - Safe for all normal development workflows

**Note:** If you ever move the project outside OneDrive, you may not need this step. This script is only needed for Windows/OneDrive users. 