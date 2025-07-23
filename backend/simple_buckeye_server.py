from flask import Flask, jsonify, request
import json
import os
import time
from datetime import datetime
from buckeye_scraper import BuckeyeScraper
from betbck_async_scraper import get_all_betbck_games
from match_games import match_pinnacle_to_betbck
from calculate_ev_table import calculate_ev_table, format_ev_table_for_display

app = Flask(__name__)

# Global state
buckeye_scraper = None
current_results = None
last_run_time = None

BUCKEYE_RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'buckeye_results.json')

def get_buckeye_scraper():
    global buckeye_scraper
    if buckeye_scraper is None:
        config = {"debug": True}
        buckeye_scraper = BuckeyeScraper(config)
    return buckeye_scraper

@app.route('/')
def index():
    """Serve the simple frontend"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BuckeyeScraper EV</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .button { 
                background: #007bff; color: white; border: none; padding: 12px 24px; 
                margin: 10px; border-radius: 5px; cursor: pointer; font-size: 16px;
            }
            .button:hover { background: #0056b3; }
            .button:disabled { background: #6c757d; cursor: not-allowed; }
            .status { margin: 20px 0; padding: 15px; border-radius: 5px; }
            .success { background: #28a745; }
            .error { background: #dc3545; }
            .info { background: #17a2b8; }
            .results { margin-top: 30px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
            th { background: #333; }
            .loading { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 BuckeyeScraper EV</h1>
                <p>Simple EV calculation for Pinnacle vs BetBCK odds</p>
            </div>
            
            <div style="text-align: center;">
                <button class="button" onclick="getEventIds()" id="eventIdsBtn">GET EVENT IDS</button>
                <button class="button" onclick="runCalculations()" id="calcBtn">RUN CALCULATIONS</button>
                <button class="button" onclick="refreshResults()" id="refreshBtn">REFRESH RESULTS</button>
            </div>
            
            <div id="status"></div>
            <div id="loading" class="loading">🔄 Processing...</div>
            <div id="results" class="results"></div>
        </div>

        <script>
            function showStatus(message, type = 'info') {
                const status = document.getElementById('status');
                status.innerHTML = `<div class="status ${type}">${message}</div>`;
            }

            function setLoading(loading) {
                document.getElementById('loading').style.display = loading ? 'block' : 'none';
                document.getElementById('eventIdsBtn').disabled = loading;
                document.getElementById('calcBtn').disabled = loading;
                document.getElementById('refreshBtn').disabled = loading;
            }

            async function getEventIds() {
                setLoading(true);
                showStatus('🔄 Fetching event IDs from Pinnacle...', 'info');
                
                try {
                    const response = await fetch('/api/get-event-ids', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showStatus(`✅ Successfully fetched ${data.data.event_count} event IDs`, 'success');
                    } else {
                        showStatus(`❌ Error: ${data.message}`, 'error');
                    }
                } catch (error) {
                    showStatus(`❌ Network error: ${error.message}`, 'error');
                } finally {
                    setLoading(false);
                }
            }

            async function runCalculations() {
                setLoading(true);
                showStatus('🔄 Running EV calculations...', 'info');
                
                try {
                    const response = await fetch('/api/run-calculations', { method: 'POST' });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showStatus(`✅ Calculations completed! Found ${data.data.total_events} events with EV opportunities`, 'success');
                        displayResults(data.data.events);
                    } else {
                        showStatus(`❌ Error: ${data.message}`, 'error');
                    }
                } catch (error) {
                    showStatus(`❌ Network error: ${error.message}`, 'error');
                } finally {
                    setLoading(false);
                }
            }

            async function refreshResults() {
                setLoading(true);
                showStatus('🔄 Refreshing results...', 'info');
                
                try {
                    const response = await fetch('/api/get-results');
                    const data = await response.json();
                    
                    if (data.status === 'success' && data.data.events) {
                        showStatus(`✅ Loaded ${data.data.events.length} events`, 'success');
                        displayResults(data.data.events);
                    } else {
                        showStatus('ℹ️ No results available. Run calculations first.', 'info');
                    }
                } catch (error) {
                    showStatus(`❌ Network error: ${error.message}`, 'error');
                } finally {
                    setLoading(false);
                }
            }

            function displayResults(events) {
                const resultsDiv = document.getElementById('results');
                
                if (!events || events.length === 0) {
                    resultsDiv.innerHTML = '<p>No EV opportunities found.</p>';
                    return;
                }

                let html = '<h2>📊 EV Opportunities</h2>';
                html += '<table><thead><tr><th>Matchup</th><th>League</th><th>Market</th><th>BetBCK Odds</th><th>Pinnacle NVP</th><th>EV</th></tr></thead><tbody>';
                
                events.forEach(event => {
                    event.markets.forEach(market => {
                        html += `<tr>
                            <td>${event.home_team} vs ${event.away_team}</td>
                            <td>${event.league || 'N/A'}</td>
                            <td>${market.market} - ${market.selection} ${market.line}</td>
                            <td>${market.betbck_odds}</td>
                            <td>${market.pinnacle_nvp}</td>
                            <td style="font-weight: bold; color: #28a745;">${market.ev}</td>
                        </tr>`;
                    });
                });
                
                html += '</tbody></table>';
                resultsDiv.innerHTML = html;
            }

            // Auto-refresh results every 30 seconds if we have results
            setInterval(() => {
                if (document.getElementById('results').innerHTML.includes('EV Opportunities')) {
                    refreshResults();
                }
            }, 30000);
        </script>
    </body>
    </html>
    '''

@app.route('/api/get-event-ids', methods=['POST'])
def get_event_ids():
    """Get event IDs from Pinnacle (Step 1)"""
    try:
        scraper = get_buckeye_scraper()
        
        # Check if we have recent event IDs
        cached_ids = scraper.load_event_ids()
        if cached_ids:
            return jsonify({
                "status": "success",
                "message": f"Loaded {len(cached_ids)} cached event IDs",
                "data": {"event_count": len(cached_ids), "event_ids": cached_ids}
            })
        
        # Fetch new event IDs
        event_dicts = scraper.get_todays_event_ids()
        
        if not event_dicts:
            return jsonify({
                "status": "error",
                "message": "No event IDs returned from Pinnacle API",
                "data": {"event_count": 0, "event_ids": []}
            })
        
        # Save event IDs
        event_ids = [str(event.get("event_id")) for event in event_dicts if event.get("event_id")]
        scraper.save_event_ids(event_ids)
        
        return jsonify({
            "status": "success",
            "message": f"Successfully fetched {len(event_ids)} event IDs",
            "data": {"event_count": len(event_ids), "event_ids": event_ids}
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error fetching event IDs: {str(e)}",
            "data": {"event_count": 0, "event_ids": []}
        })

@app.route('/api/run-calculations', methods=['POST'])
def run_calculations():
    """Run the complete EV calculation pipeline (Steps 2-4)"""
    global current_results, last_run_time
    try:
        scraper = get_buckeye_scraper()
        print("[BuckeyeServer] Starting calculation pipeline...")
        # Step 1: Get event IDs
        event_dicts = scraper.get_todays_event_ids()
        if not event_dicts:
            print("[BuckeyeServer] No event IDs available.")
            return jsonify({
                "status": "error",
                "message": "No event IDs available. Run GET EVENT IDS first.",
                "data": {"events": [], "total_events": 0}
            })
        # Step 2: Get BetBCK data
        betbck_games = get_all_betbck_games()
        if not betbck_games:
            print("[BuckeyeServer] Failed to scrape BetBCK data.")
            return jsonify({
                "status": "error",
                "message": "Failed to scrape BetBCK data",
                "data": {"events": [], "total_events": 0}
            })
        # Step 3: Match games
        matched_games = match_pinnacle_to_betbck(event_dicts, {"games": betbck_games})
        if not matched_games:
            print("[BuckeyeServer] No games matched successfully.")
            return jsonify({
                "status": "error",
                "message": "No games matched successfully",
                "data": {"events": [], "total_events": 0}
            })
        # Step 4: Calculate EV
        ev_table = calculate_ev_table(matched_games)
        if not ev_table:
            print("[BuckeyeServer] No EV opportunities found.")
            return jsonify({
                "status": "error",
                "message": "No EV opportunities found",
                "data": {"events": [], "total_events": 0}
            })
        # Format for display
        formatted_events = format_ev_table_for_display(ev_table)
        # Store results in memory and on disk
        current_results = formatted_events
        last_run_time = datetime.now().isoformat()
        try:
            with open(BUCKEYE_RESULTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "events": formatted_events,
                    "total_events": len(formatted_events),
                    "last_run": last_run_time
                }, f, indent=2)
            print(f"[BuckeyeServer] Results written to {BUCKEYE_RESULTS_FILE} ({len(formatted_events)} events)")
        except Exception as e:
            print(f"[BuckeyeServer] ERROR writing results to {BUCKEYE_RESULTS_FILE}: {e}")
        return jsonify({
            "status": "success",
            "message": f"Successfully calculated EV for {len(formatted_events)} events",
            "data": {
                "events": formatted_events,
                "total_events": len(formatted_events),
                "last_run": last_run_time
            }
        })
    except Exception as e:
        print(f"[BuckeyeServer] ERROR in calculation pipeline: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error running calculations: {str(e)}",
            "data": {"events": [], "total_events": 0}
        })

@app.route('/api/get-results')
def get_results():
    """Get current results"""
    global current_results, last_run_time
    if current_results is None:
        # Try to load from file
        try:
            if os.path.exists(BUCKEYE_RESULTS_FILE):
                with open(BUCKEYE_RESULTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                current_results = data.get("events", [])
                last_run_time = data.get("last_run", None)
                print(f"[BuckeyeServer] Loaded results from {BUCKEYE_RESULTS_FILE} ({len(current_results)} events)")
            else:
                print(f"[BuckeyeServer] No results file found at {BUCKEYE_RESULTS_FILE}")
        except Exception as e:
            print(f"[BuckeyeServer] ERROR loading results from {BUCKEYE_RESULTS_FILE}: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error loading results: {e}",
                "data": {"events": [], "total_events": 0}
            })
    if not current_results:
        return jsonify({
            "status": "error",
            "message": "No results available. Run calculations first.",
            "data": {"events": [], "total_events": 0}
        })
    return jsonify({
        "status": "success",
        "message": f"Loaded {len(current_results)} events",
        "data": {
            "events": current_results,
            "total_events": len(current_results),
            "last_run": last_run_time
        }
    })

if __name__ == '__main__':
    print("🎯 Starting BuckeyeScraper EV Server...")
    print("📊 Server will be available at: http://localhost:5000")
    print("💡 Click GET EVENT IDS to fetch Pinnacle events")
    print("💡 Click RUN CALCULATIONS to find EV opportunities")
    app.run(host='0.0.0.0', port=5000, debug=True) 