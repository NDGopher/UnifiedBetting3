# Portable PTO Scraper Setup Guide

This guide will help you set up the PTO scraper on any PC, handling Cloudflare challenges and Chrome profile management automatically.

## 🚀 Quick Start (Windows)

### Option 1: Automated Setup (Recommended)

1. **Download the project** to your PC
2. **Double-click `launch_pto.bat`**
3. **Choose option 1** - "Setup PTO Chrome Profile (First Time)"
4. **Follow the on-screen instructions** to log in to PTO
5. **Choose option 8** - "Launch Full App" to start everything

That's it! The scraper will work on any PC.

---

## 📋 Detailed Setup Instructions

### Prerequisites

- **Google Chrome** installed
- **Python 3.8+** installed
- **Node.js** installed (for frontend)

### Step 1: Install Dependencies

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies  
cd ../frontend
npm install
```

### Step 2: Setup Chrome Profile

#### Automated Setup (Recommended)
```bash
cd backend
python setup_pto_profile.py
```

**What this does:**
- Creates a new Chrome profile specifically for PTO
- Opens Chrome and navigates to PTO
- Waits for you to log in manually
- Saves the profile for future use
- Updates configuration automatically

#### Manual Setup (Alternative)
If automated setup doesn't work:

1. **Create Chrome profile directory:**
   ```bash
   # Windows
   mkdir "%USERPROFILE%\AppData\Local\PTO_Chrome_Profile"
   
   # macOS
   mkdir -p ~/Library/Application\ Support/PTO_Chrome_Profile
   
   # Linux
   mkdir -p ~/.config/PTO_Chrome_Profile
   ```

2. **Update config.json:**
   ```json
   {
     "pto": {
       "chrome_user_data_dir": "PATH_TO_YOUR_PROFILE_DIR",
       "chrome_profile_dir": "PTO_Profile",
       "pto_url": "https://picktheodds.app/en/expectedvalue",
       "enable_auto_scraping": true
     }
   }
   ```

### Step 3: Test the Setup

```bash
cd backend
python test_pto_scraper.py
```

This will verify that:
- Chrome profile is working
- PTO login is successful
- Data parsing functions correctly

### Step 4: Launch the Application

#### Option A: Full Application
```bash
# Start backend
cd backend
python main.py

# In another terminal, start frontend
cd frontend
npm start
```

#### Option B: Backend Only
```bash
cd backend
python main.py
```

Then access API endpoints at `http://localhost:5001`

---

## 🔄 Profile Management

### Backup Your Profile

Before moving to a new PC, backup your working profile:

```bash
cd backend
python profile_manager.py
# Choose option 1: Create backup
```

### Transfer to New PC

1. **Copy the backup file** to the new PC
2. **Run profile manager:**
   ```bash
   cd backend
   python profile_manager.py
   # Choose option 5: Import profile from file
   ```

### Export/Import Profile

```bash
# Export current profile
python profile_manager.py
# Choose option 4: Export profile to file

# Import profile on new PC
python profile_manager.py  
# Choose option 5: Import profile from file
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Chrome Profile Not Found
**Symptoms:** "Profile directory not found" error

**Solution:**
```bash
cd backend
python setup_pto_profile.py
# Choose option 1 to create new profile
```

#### 2. Cloudflare Blocking
**Symptoms:** "Failed to pass Cloudflare challenge" error

**Solutions:**
- **Wait longer:** Cloudflare challenges can take 30-60 seconds
- **Use VPN:** Try different IP address
- **Manual login:** Let the scraper open Chrome, then log in manually
- **Clear cookies:** Delete the profile and create a new one

#### 3. Login Issues
**Symptoms:** "Login required but not completed" error

**Solution:**
1. Let Chrome open automatically
2. Log in to PTO manually
3. Navigate to Prop Builder tab
4. Close Chrome when done
5. The scraper will continue automatically

#### 4. No Props Found
**Symptoms:** "No prop cards found" message

**Solutions:**
- Check if PTO has active props
- Verify you're on the Prop Builder tab
- Try refreshing the page manually
- Check if login session expired

### Debug Mode

Enable detailed logging:

```bash
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

## 🔧 Advanced Configuration

### Custom Chrome Options

Edit `config.json` to customize Chrome behavior:

```json
{
  "pto": {
    "chrome_user_data_dir": "PATH_TO_PROFILE",
    "chrome_profile_dir": "PTO_Profile",
    "pto_url": "https://picktheodds.app/en/expectedvalue",
    "scraping_interval_seconds": 10,
    "page_refresh_interval_hours": 2.5,
    "enable_auto_scraping": true,
    "max_retries": 3,
    "retry_delay": 30
  }
}
```

### Environment Variables

Set these for different environments:

```bash
# Development
export PTO_ENV=dev
export PTO_DEBUG=true

# Production  
export PTO_ENV=prod
export PTO_DEBUG=false
```

---

## 📱 Cross-Platform Support

### Windows
- Uses `%USERPROFILE%\AppData\Local\PTO_Chrome_Profile`
- Run `launch_pto.bat` for easy setup

### macOS
- Uses `~/Library/Application Support/PTO_Chrome_Profile`
- Run `python setup_pto_profile.py` directly

### Linux
- Uses `~/.config/PTO_Chrome_Profile`
- May need additional Chrome dependencies

---

## 🔒 Security Considerations

### Profile Security
- **Keep profiles secure:** Don't share Chrome profile files
- **Regular backups:** Backup working profiles regularly
- **Clean profiles:** Delete old profiles when no longer needed

### Network Security
- **Use VPN:** Consider using VPN for additional protection
- **Firewall:** Ensure ports 5001 (backend) and 3000 (frontend) are open
- **HTTPS:** Use HTTPS in production environments

---

## 📊 Monitoring and Maintenance

### Check Scraper Status

```bash
curl http://localhost:5001/pto/scraper/status
```

### View Live Props

```bash
curl http://localhost:5001/pto/props
```

### Filter by EV

```bash
curl http://localhost:5001/pto/props/ev/5.0
```

### Log Files

Check logs in the backend directory:
- `main.py` logs to console
- Chrome logs in profile directory

---

## 🆘 Getting Help

### Self-Diagnosis

1. **Check logs:** Look for error messages in console
2. **Test profile:** Run `python setup_pto_profile.py` option 2
3. **Verify config:** Check `config.json` settings
4. **Test API:** Try `curl http://localhost:5001/test`

### Common Solutions

| Problem | Solution |
|---------|----------|
| Chrome not found | Install Google Chrome |
| Profile not working | Run setup script again |
| Cloudflare blocking | Wait longer, use VPN, or manual login |
| No props showing | Check PTO site, verify login |
| API not responding | Check if backend is running |

### Support

If you're still having issues:

1. **Check the troubleshooting section above**
2. **Run the test script:** `python test_pto_scraper.py`
3. **Enable debug logging** and check console output
4. **Try creating a fresh profile** using the setup script

---

## 🎯 Quick Reference

### Essential Commands

```bash
# Setup (first time)
python setup_pto_profile.py

# Test profile
python setup_pto_profile.py

# Backup profile
python profile_manager.py

# Launch backend
python main.py

# Launch frontend
npm start

# Test scraper
python test_pto_scraper.py
```

### Key URLs

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5001
- **PTO Site:** https://picktheodds.app/en/expectedvalue

### Important Files

- `config.json` - Configuration settings
- `setup_pto_profile.py` - Profile setup script
- `profile_manager.py` - Profile backup/restore
- `pto_scraper.py` - Main scraper logic
- `launch_pto.bat` - Windows launcher

---

**🎉 You're all set!** The PTO scraper should now work on any PC with minimal setup required. 