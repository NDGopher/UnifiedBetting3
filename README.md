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

## Usage
- Access the frontend at [http://localhost:3000](http://localhost:3000)
- Backend API at [http://localhost:5001](http://localhost:5001)
- PTO scraper runs in the background and updates props in real time

## Credits
- Developed by NDGopher and contributors
- Special thanks to the open-source community

## License
MIT License (see LICENSE) 