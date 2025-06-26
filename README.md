# UnifiedBetting2

UnifiedBetting2 is a robust, full-stack betting analytics and automation platform. It integrates real-time scraping, EV (expected value) calculations, Telegram alerts, and a modern React frontend for sports betting professionals and enthusiasts.

## Features
- **PTO (PickTheOdds) Scraper**: Stealthy Selenium-based scraper with persistent Chrome profile
- **PropBuilderEV Workflow**: Real-time prop monitoring, robust anti-bot, and session management
- **Telegram Alerts**: Instant notifications for high-EV props
- **Modern Frontend**: React UI with real-time updates, filtering, and status indicators
- **Single-Command Launch**: One BAT/script launches everything (backend, frontend, scraper)
- **Portable & User-Friendly**: Easy setup, robust error handling, and clear workflow

## Setup
1. **Clone the repo:**
   ```sh
   git clone https://github.com/NDGopher/UnifiedBetting2.git
   cd UnifiedBetting2
   ```
2. **Install backend dependencies:**
   ```sh
   cd backend
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```
3. **Install frontend dependencies:**
   ```sh
   cd ../frontend
   npm install
   ```
4. **Run the setup script for PTO profile:**
   ```sh
   cd ../backend
   python setup_pto_profile.py
   ```
5. **Launch the app:**
   ```sh
   cd ..
   python launch.py
   ```

## ⚠️ Important: Missing Files
After cloning the repository, you need to manually add the following files that are not included in the repo for security/privacy reasons:

### Required Files to Add:
1. **`backend/config.json`** - Configuration file containing:
   - BetBCK credentials and URLs
   - Pinnacle API settings
   - Telegram bot configuration
   - PTO scraper settings

2. **`backend/utils/pod_utils.py`** - Utility functions containing:
   - `skip_indicators()` function
   - `is_prop_or_corner_alert()` function  
   - `fuzzy_team_match()` function
   - `determine_betbck_search_term()` function
   - Team name normalization and EV calculation utilities

3. **`backend/utils/__init__.py`** - Module initialization file with proper imports

### How to Add These Files:
- Copy these files from your existing working installation
- Place them in the correct locations as shown above
- Ensure `config.json` contains your actual API keys and credentials
- The backend will not start without these files

## Usage
- Access the frontend at [http://localhost:3000](http://localhost:3000)
- Backend API at [http://localhost:5001](http://localhost:5001)
- PTO scraper runs in the background and updates props in real time

## Credits
- Developed by NDGopher and contributors
- Special thanks to the open-source community

## License
MIT License (see LICENSE) 