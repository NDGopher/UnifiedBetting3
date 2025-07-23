# Unified Betting System - Complete Explanation

## 🎯 **What You Get: One BAT File, Everything Works**

When you click `launch.bat`, here's exactly what happens:

### **1. System Check & Setup**
- ✅ Checks Python and Node.js are installed
- ✅ Creates virtual environment for backend
- ✅ Installs all dependencies (backend + frontend)
- ✅ Kills any existing processes on ports 3000-3010 and 5001

### **2. PTO Chrome Profile Setup**
- ✅ **Checks if PTO profile exists** and is working
- ✅ **If not working:** Opens Chrome setup wizard
- ✅ **You log in to PTO once** (Cloudflare + email code)
- ✅ **Profile is saved** for future use
- ✅ **Never asks for login again** (until session expires)

### **3. Opens Pinnacle Odds Dropper**
- ✅ **Automatically opens** https://pinnacleoddsdropper.com in your browser
- ✅ **For POD alerts** - this is what you use for alerts

### **4. Launches Backend Server**
- ✅ **Starts FastAPI server** on port 5001
- ✅ **Includes PTO scraper** running in background
- ✅ **Handles POD alerts** from Pinnacle Odds Dropper
- ✅ **Serves data to frontend**

### **5. Launches Frontend Server**
- ✅ **Starts React app** on port 3000-3010 (finds free port)
- ✅ **Opens in browser** automatically
- ✅ **Shows POD alerts** + **PTO props** in one interface

---

## 🔍 **Chrome Profile System Explained**

### **What is a Chrome Profile?**
A Chrome profile is like a separate browser instance with its own:
- ✅ **Cookies and login sessions**
- ✅ **Bookmarks and settings**
- ✅ **Extensions and preferences**

### **Why We Need It for PTO**
- 🔒 **Cloudflare protection** blocks automated access
- 🔐 **Login required** to access prop data
- 📧 **Email verification** needed (one-time)
- 💾 **Session persistence** keeps you logged in

### **How It Works**
1. **Creates dedicated profile** in `C:\Users\YourName\AppData\Local\PTO_Chrome_Profile`
2. **Completely separate** from your main Chrome browser
3. **You log in once** - Cloudflare challenge + email code
4. **Saves login session** - never asks again
5. **Scraper uses this profile** to access PTO data

### **Profile Locations by OS**
- **Windows:** `%USERPROFILE%\AppData\Local\PTO_Chrome_Profile`
- **macOS:** `~/Library/Application Support/PTO_Chrome_Profile`
- **Linux:** `~/.config/PTO_Chrome_Profile`

---

## 🚀 **Complete Workflow**

### **First Time Setup (New PC)**
```
1. Click launch.bat
2. System installs dependencies
3. Chrome opens for PTO login
4. You complete Cloudflare challenge
5. You enter email verification code
6. Chrome closes automatically
7. Backend starts with PTO scraper
8. Pinnacle Odds Dropper opens
9. Frontend opens with all data
```

### **Subsequent Launches**
```
1. Click launch.bat
2. System checks PTO profile (still logged in)
3. Backend starts with PTO scraper
4. Pinnacle Odds Dropper opens
5. Frontend opens with all data
```

### **Profile Transfer (New PC)**
```
1. On working PC: Export profile
2. Copy .zip file to new PC
3. On new PC: Import profile
4. Click launch.bat - everything works!
```

---

## 📊 **What You See in the Frontend**

### **POD Alerts Tab**
- ✅ **Real-time POD alerts** from Pinnacle Odds Dropper
- ✅ **EV calculations** and market analysis
- ✅ **BetBCK integration** for odds comparison

### **Prop Builder Tab (NEW)**
- ✅ **Live PTO props** with EV values
- ✅ **Filter by sport** (NBA, MLB, NFL, etc.)
- ✅ **Filter by EV threshold** (show only +5% EV)
- ✅ **Real-time updates** every 30 seconds
- ✅ **Color-coded EV indicators** (green = good, red = bad)
- ✅ **Scraper controls** (start/stop)

### **EV Calculator Tab**
- ✅ **Manual EV calculations**
- ✅ **Odds conversion tools**

---

## 🔧 **Technical Architecture**

### **Backend Components**
```
main.py
├── POD alert handling (existing)
├── PTO scraper integration (NEW)
├── API endpoints for both systems
└── Unified data management

pto_scraper.py (NEW)
├── Chrome profile management
├── Cloudflare bypass handling
├── PTO data parsing
└── Background scraping loop

setup_pto_profile.py (NEW)
├── Chrome profile creation
├── Cross-platform path handling
└── Configuration management
```

### **Frontend Components**
```
App.tsx
├── POD Alerts (existing)
├── Prop Builder (enhanced)
└── EV Calculator (existing)

PropBuilder.tsx (enhanced)
├── PTO data display
├── Filtering controls
├── Real-time updates
└── Scraper status
```

### **Data Flow**
```
Pinnacle Odds Dropper → POD Alerts → Backend → Frontend
PTO Website → PTO Scraper → Backend → Frontend
```

---

## 🛡️ **Security & Privacy**

### **Chrome Profile Security**
- ✅ **Isolated from main browser** - your regular browsing is unaffected
- ✅ **Local storage only** - no data sent to external servers
- ✅ **Profile encryption** - uses Chrome's built-in security
- ✅ **Session management** - automatic logout after inactivity

### **Data Privacy**
- ✅ **No personal data collected** - only betting odds and EV data
- ✅ **Local processing** - all calculations done on your machine
- ✅ **No tracking** - no analytics or user tracking
- ✅ **Secure storage** - config files stored locally

---

## 🔄 **Profile Management**

### **Automatic Backup**
- ✅ **Creates backups** in `pto_profile_backups/` directory
- ✅ **Includes metadata** (creation date, system info)
- ✅ **Compressed format** (.zip files)

### **Easy Transfer**
- ✅ **Export profile** to .zip file
- ✅ **Copy to new PC** via USB, cloud, etc.
- ✅ **Import profile** - everything works immediately
- ✅ **No re-login required** - session preserved

### **Profile Recovery**
- ✅ **Multiple backups** - keep several versions
- ✅ **Rollback capability** - restore previous working profile
- ✅ **Cross-platform** - works on Windows, macOS, Linux

---

## 🎯 **Key Benefits**

### **Unified Experience**
- ✅ **One launcher** - everything starts together
- ✅ **Single interface** - POD + PTO in one app
- ✅ **Consistent workflow** - same process every time

### **Portability**
- ✅ **Works on any PC** - just copy the project folder
- ✅ **Profile transfer** - move working setup easily
- ✅ **Cross-platform** - Windows, macOS, Linux

### **Reliability**
- ✅ **Automatic recovery** - handles connection issues
- ✅ **Error handling** - graceful failure management
- ✅ **Logging** - detailed status information

### **User-Friendly**
- ✅ **One-click setup** - minimal user interaction
- ✅ **Clear instructions** - step-by-step guidance
- ✅ **Status indicators** - know what's happening

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **PTO Login Problems**
```
Problem: "Login required but not completed"
Solution: 
1. Let Chrome open automatically
2. Complete Cloudflare challenge
3. Enter email verification code
4. Close Chrome when done
5. Setup continues automatically
```

#### **Profile Not Working**
```
Problem: "Profile test failed"
Solution:
1. Run setup again: python setup_pto_profile.py
2. Create fresh profile
3. Log in to PTO manually
4. Test profile functionality
```

#### **Cloudflare Blocking**
```
Problem: "Failed to pass Cloudflare challenge"
Solutions:
1. Wait longer (30-60 seconds)
2. Use VPN for different IP
3. Try manual login process
4. Clear profile and start fresh
```

### **Debug Mode**
```bash
# Enable detailed logging
cd backend
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from pto_scraper import PTOScraper
import json
with open('config.json') as f:
    config = json.load(f)
scraper = PTOScraper(config['pto'])
scraper.start_scraping()
"
```

---

## 🎉 **Summary**

**You now have a complete unified betting system that:**

1. **Launches with one click** - `launch.bat`
2. **Handles PTO login automatically** - Chrome profile system
3. **Opens Pinnacle Odds Dropper** - for POD alerts
4. **Runs PTO scraper** - real-time prop data
5. **Shows everything in one interface** - unified frontend
6. **Works on any PC** - portable profile system
7. **Never asks for login again** - persistent sessions

**The Chrome profile system is completely safe and isolated from your main browser. You log in once to PTO, and the system remembers your session forever (until it expires naturally).**

**Everything is integrated into your existing workflow - no separate launchers, no manual setup, just one unified system that does it all.** 