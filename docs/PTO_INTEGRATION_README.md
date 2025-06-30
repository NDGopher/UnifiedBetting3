# PTO (PickTheOdds) Integration for Unified Betting App

This document describes the integration of PTO (PickTheOdds) prop scraping functionality into the Unified Betting App.

## Overview

The PTO integration adds real-time prop betting data from PickTheOdds.app to the unified betting interface. It scrapes the PTO Prop Builder tab using a logged-in Chrome profile and provides the data through a modern React frontend.

## Features

- **Real-time PTO Scraping**: Automatically scrapes PTO Prop Builder tab every 10 seconds
- **Chrome Profile Integration**: Uses existing logged-in Chrome profile for authentication
- **EV Filtering**: Filter props by minimum EV threshold
- **Sport Filtering**: Filter by specific sports
- **Auto-refresh**: Configurable automatic data refresh
- **Visual Indicators**: Color-coded EV values and trend indicators
- **Scraper Control**: Start/stop scraper from the frontend
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

### Backend Components

1. **`pto_scraper.py`**: Main scraper class that handles:
   - Chrome driver initialization with PTO profile
   - PTO page navigation and prop extraction
   - Data parsing and structuring
   - Background scraping loop

2. **API Endpoints** (in `main.py`):
   - `GET /pto/props`: Get all live props
   - `GET /pto/props/ev/{min_ev}`: Get props filtered by EV threshold
   - `POST /pto/scraper/start`: Start the scraper
   - `POST /pto/scraper/stop`: Stop the scraper
   - `GET /pto/scraper/status`: Get scraper status

3. **Configuration** (`config.json`):
   ```json
   {
     "pto": {
       "pto_url": "https://picktheodds.app/en/expectedvalue",
       "chrome_user_data_dir": "C:/Users/steph/OneDrive/Desktop/ProdProjects/PropBuilderEV/pto_chrome_profile",
       "chrome_profile_dir": "Profile 1",
       "scraping_interval_seconds": 10,
       "page_refresh_interval_hours": 2.5,
       "enable_auto_scraping": true
     }
   }
   ```

### Frontend Components

1. **`PropBuilder.tsx`**: Main React component featuring:
   - Real-time prop display with cards
   - Filtering controls (EV threshold, sport, +EV only)
   - Scraper control buttons
   - Auto-refresh toggle
   - Status indicators
   - Responsive grid layout

## Installation & Setup

### Prerequisites

1. **Chrome Profile**: Ensure you have a logged-in Chrome profile for PTO
2. **Dependencies**: Install selenium and other requirements

### Backend Setup

1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure PTO Settings**:
   - Update `config.json` with your Chrome profile path
   - Ensure the PTO URL is correct
   - Set `enable_auto_scraping` to `true` or `false`

3. **Test the Scraper**:
   ```bash
   python test_pto_scraper.py
   ```

### Frontend Setup

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**:
   ```bash
   npm start
   ```

## Usage

### Starting the Application

1. **Start Backend**:
   ```bash
   cd backend
   python main.py
   ```

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```

3. **Access the App**: Navigate to `http://localhost:3000`

### Using the Prop Builder Tab

1. **View Props**: The Prop Builder tab displays all live PTO props
2. **Filter by EV**: Use the "Min EV %" field to filter by minimum EV
3. **Filter by Sport**: Use the sport dropdown to filter by specific sports
4. **Toggle +EV Only**: Switch to show only positive EV props
5. **Control Scraper**: Use the play/stop buttons to control the scraper
6. **Auto-refresh**: Toggle automatic data refresh every 30 seconds

## Data Structure

### Prop Object Structure

```typescript
interface PTOProp {
  prop: {
    sport: string;           // e.g., "NBA", "MLB"
    teams: string[];         // e.g., ["Lakers", "Warriors"]
    propDesc: string;        // e.g., "Points - Over 220.5"
    betType: string;         // e.g., "Over", "Under"
    odds: string;            // e.g., "+110", "-150"
    width: string;           // e.g., "5"
    gameTime: string;        // e.g., "7:30 PM"
    fairValue: string;       // e.g., "+105"
    ev: string;              // e.g., "-2.5%"
    timestamp: string;       // ISO timestamp
  };
  created_at: string;        // ISO timestamp
  updated_at: string;        // ISO timestamp
}
```

## Configuration Options

### Backend Configuration

- **`pto_url`**: PTO expected value page URL
- **`chrome_user_data_dir`**: Path to Chrome user data directory
- **`chrome_profile_dir`**: Chrome profile directory name
- **`scraping_interval_seconds`**: How often to scrape for new props
- **`page_refresh_interval_hours`**: How often to refresh the PTO page
- **`enable_auto_scraping`**: Whether to start scraper automatically

### Frontend Configuration

- **`API_BASE`**: Backend API base URL (default: `http://localhost:5001`)
- **Auto-refresh interval**: 30 seconds (configurable in component)

## Troubleshooting

### Common Issues

1. **Chrome Profile Not Found**:
   - Verify the Chrome profile path in `config.json`
   - Ensure the profile is logged into PTO

2. **Scraper Not Starting**:
   - Check if Chrome is already running with the profile
   - Verify PTO URL is accessible
   - Check logs for authentication issues

3. **No Props Displayed**:
   - Verify scraper is running
   - Check if PTO has active props
   - Verify EV filters aren't too restrictive

4. **Frontend Connection Issues**:
   - Ensure backend is running on port 5001
   - Check CORS settings
   - Verify API endpoints are accessible

### Debugging

1. **Backend Logs**: Check console output for scraper status and errors
2. **Frontend Console**: Check browser console for API errors
3. **Test Script**: Run `test_pto_scraper.py` to verify basic functionality

## Security Considerations

- **Chrome Profile**: Keep your Chrome profile secure and don't share credentials
- **API Access**: Consider adding authentication to API endpoints in production
- **CORS**: Configure CORS properly for production deployment

## Performance Notes

- **Scraping Interval**: 10 seconds provides good balance between responsiveness and server load
- **Page Refresh**: 2.5 hours helps maintain session and avoid stale data
- **Memory Usage**: Props are stored in memory; consider database storage for large datasets
- **Chrome Resources**: Each scraper instance uses significant memory; monitor system resources

## Future Enhancements

- **Database Storage**: Store props in database for historical analysis
- **Alert System**: Send notifications for high-EV props
- **Advanced Filtering**: Add more filtering options (time, league, etc.)
- **Data Export**: Export prop data to CSV/Excel
- **Analytics**: Add prop performance tracking and analytics
- **Mobile App**: Create dedicated mobile app for prop monitoring

## Support

For issues or questions about the PTO integration:

1. Check the troubleshooting section above
2. Review backend logs for error messages
3. Test individual components using the test script
4. Verify configuration settings match your environment 