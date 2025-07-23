# 🚀 UnifiedBetting3 - Real-Time Sports Betting Alert System

A comprehensive, real-time sports betting alert system that monitors POD (Pick of the Day) alerts, compares odds across multiple sportsbooks, and provides live EV (Expected Value) calculations.

## 🎯 Key Features

### ✅ **Real-Time Alert Processing**
- **Live POD alerts** from Chrome extension
- **Real-time odds updates** every 3 seconds
- **Instant EV calculations** across multiple sportsbooks
- **WebSocket-based frontend** for live updates

### ✅ **Smart Alert Management**
- **Intelligent expiration**: Negative EV alerts expire in 60s, positive EV in 3 minutes
- **Automatic cleanup**: Expired alerts removed from UI automatically
- **Efficient API usage**: Stops updating negative EV alerts to save resources
- **Deduplication**: Prevents duplicate processing of the same alert

### ✅ **Database Integration**
- **High EV alert storage**: Alerts with >3% EV automatically saved to database
- **Historical tracking**: Query past high-value opportunities
- **Safe operations**: Database failures won't crash the system
- **Lazy initialization**: Database only loads when needed

### ✅ **Multi-Source Odds Comparison**
- **Pinnacle Sports**: Current market odds via API
- **BetBCK**: Odds scraping for comparison
- **EV calculations**: Real-time expected value analysis
- **Cross-book arbitrage**: Identify value opportunities

## 🏗️ System Architecture

### **Backend (FastAPI)**
```
backend/
├── main.py                 # Main FastAPI application
├── pod_event_manager.py    # Alert lifecycle management
├── database_models.py      # SQLite database models
├── betbck_request_manager.py # BetBCK API management
├── ace_scraper.py         # Action23.ag scraper
├── buckeye_scraper.py     # Buckeye scraper
└── websocket_manager.py   # WebSocket broadcasting
```

### **Frontend (React + TypeScript)**
```
frontend/src/
├── components/
│   ├── PODAlerts.tsx      # Main alerts display
│   ├── PropBuilder.tsx    # Prop builder interface
│   └── BuckeyeScraper.tsx # Buckeye integration
├── hooks/
│   └── useWebSocket.ts    # WebSocket connection management
└── utils/                 # Utility functions
```

### **Chrome Extension**
- **POD alert detection** from pinnacleoddsdropper.com
- **Real-time forwarding** to backend
- **Automatic event ID sniffing**
- **Duplicate prevention**

## 🚀 Quick Start

### **1. Backend Setup**
```bash
cd backend
pip install -r requirements.txt
python launch.py
```

### **2. Frontend Setup**
```bash
cd frontend
npm install
npm start
```

### **3. Chrome Extension**
1. Load the extension from `chrome-extension/` directory
2. Navigate to pinnacleoddsdropper.com
3. Extension will automatically detect and forward alerts

## 📊 System Flow

### **Alert Processing Pipeline**
1. **Chrome Extension** detects POD alert on pinnacleoddsdropper.com
2. **Backend** receives alert via `/pod_alert` endpoint
3. **Deduplication** prevents duplicate processing
4. **BetBCK Scraping** fetches comparison odds
5. **Pinnacle API** gets current market odds
6. **EV Calculation** determines expected value
7. **Real-time Broadcasting** sends updates to frontend
8. **Smart Expiration** removes alerts based on EV value

### **Real-Time Updates**
- **Background refresher** runs every 3 seconds
- **WebSocket broadcasting** to all connected clients
- **Automatic UI updates** with NVP flash effects
- **Expiration notifications** when alerts are removed

## 🔧 Configuration

### **Alert Expiration Times**
```python
# Negative EV alerts expire quickly
NEGATIVE_EV_EXPIRY = 60  # seconds

# Positive EV alerts stay longer
POSITIVE_EV_EXPIRY = 180  # seconds (3 minutes)

# Background refresh interval
REFRESH_INTERVAL = 3  # seconds
```

### **Database Settings**
```python
# High EV threshold for database storage
HIGH_EV_THRESHOLD = 3.0  # percentage

# Database operation timeout
DB_TIMEOUT = 5  # seconds
```

### **API Rate Limiting**
```python
# BetBCK rate limiting
BETBCK_RATE_LIMIT = 120  # seconds between requests

# Pinnacle API rate limiting
PINNACLE_RATE_LIMIT = 3  # seconds between requests
```

## 📡 API Endpoints

### **Alert Management**
- `POST /pod_alert` - Receive new POD alerts
- `GET /get_active_events_data` - Get current active alerts
- `POST /test/remove-alert/{event_id}` - Manually remove alert

### **System Status**
- `GET /refresher-status` - Check background refresher status
- `GET /test` - Test backend connectivity
- `GET /api/betbck/status` - Check BetBCK API status

### **Data Access**
- `GET /high-ev-alerts` - Get database history of high EV alerts
- `GET /buckeye/events` - Get Buckeye scraper results
- `GET /ace/results` - Get Ace scraper results

### **WebSocket**
- `WS /ws` - Real-time updates
  - `pod_alert` - Alert updates
  - `pod_alert_removed` - Alert expiration
  - `pto_prop_update` - Prop builder updates

## 🔍 Monitoring & Debugging

### **Console Logging**
The system provides comprehensive logging:
- **Pinnacle API calls** - Success/failure tracking
- **Odds fetching** - Detailed odds values
- **Expiration timing** - When alerts expire
- **WebSocket status** - Connection health
- **Database operations** - Storage activities

### **WebSocket Messages**
Monitor real-time activity in Chrome DevTools:
- **Network tab** → **WS** filter
- **Messages** show live data flow
- **Response** tab shows actual data

### **System Health Checks**
```bash
# Check backend status
curl http://localhost:5001/refresher-status

# Check frontend connectivity
curl http://localhost:3000

# Test WebSocket connection
# Use Chrome DevTools Network tab
```

## 🎯 Performance Features

### **Efficient Resource Usage**
- **Smart API calls**: Only fetch odds when needed
- **Memory management**: Automatic cleanup of expired alerts
- **Network optimization**: WebSocket instead of polling
- **Database efficiency**: Lazy loading and safe operations

### **Error Recovery**
- **Automatic reconnection**: WebSocket reconnects on failure
- **Fallback polling**: HTTP polling when WebSocket fails
- **Error isolation**: Database failures don't crash system
- **Global exception handling**: Prevents unexpected crashes

## 🔮 Future Enhancements

### **Planned Features**
- **Docker deployment** for easier management
- **Enhanced filtering** and sorting options
- **Additional data sources** for better odds comparison
- **Advanced analytics** and reporting dashboard
- **Mobile app** development

### **Performance Improvements**
- **Caching layer** for frequently accessed data
- **Load balancing** for high-traffic scenarios
- **Database optimization** for large datasets
- **Real-time notifications** (email, SMS, push)

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Test thoroughly**
5. **Submit a pull request**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. **Check the console logs** for error messages
2. **Review the WebSocket messages** in Chrome DevTools
3. **Test individual components** using the API endpoints
4. **Create an issue** with detailed error information

---

**UnifiedBetting3 - Making sports betting smarter, one alert at a time! 🚀** 