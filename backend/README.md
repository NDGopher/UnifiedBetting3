# Backend Pipeline Documentation

## Overview

The backend implements a robust, 4-step pipeline for unified betting analysis:

1. **Fetch Pinnacle Event IDs** - Get current events from Pinnacle
2. **Scrape BetBCK Data** - Scrape all available games from BetBCK
3. **Match Games** - Use fuzzy matching to pair Pinnacle events with BetBCK games
4. **Calculate EV** - Calculate expected value opportunities

## Key Features

### 🔍 Deep Logging
- Every step logs detailed information for debugging
- Normalization steps show before/after team names
- Matching shows similarity scores and decisions
- Unmatched events are logged with reasons

### 🎯 Robust Matching
- Uses `rapidfuzz` for fuzzy string matching
- Aggressive normalization removes props, pitcher info, and market text
- Bidirectional matching (direct and flipped orientations)
- Configurable thresholds and manual overrides

### 🛡️ Error Handling
- Each step has comprehensive error handling
- Pipeline continues even if some steps fail
- Detailed error messages with tracebacks
- Graceful degradation when data is missing

## Pipeline Steps

### Step 1: Fetch Pinnacle Event IDs
```python
# Uses buckeye_scraper to fetch current events
event_ids = fetch_buckeye_event_ids()
```

### Step 2: Scrape BetBCK Data
```python
# Uses betbck_async_scraper for robust HTML scraping
games = get_all_betbck_games()
```

### Step 3: Match Games
```python
# Uses match_games.py with fuzzy matching
matched_games = match_pinnacle_to_betbck(pinnacle_events, betbck_data)
```

### Step 4: Calculate EV
```python
# Uses calculate_ev_table.py for EV calculations
ev_table = calculate_ev_table(matched_games)
```

## API Endpoints

### Run Full Pipeline
```http
POST /api/run-pipeline
```
Runs the complete 4-step pipeline with detailed logging.

### Debug Matching
```http
GET /api/debug/matching
```
Analyzes matching issues and provides statistics.

## Logging

### Log Levels
- **INFO**: Pipeline progress and results
- **DEBUG**: Detailed matching and normalization steps
- **WARNING**: Non-critical issues (unmatched events, etc.)
- **ERROR**: Critical failures with tracebacks

### Key Log Messages
- `[MATCH]` - Matching process details
- `[NORMALIZE]` - Team name normalization steps
- `[MATCHED]` - Successful matches
- `[NO MATCH]` - Failed matches with reasons
- `[SKIP]` - Skipped events (props, etc.)

## Debugging

### Check Unmatched Events
1. Run the pipeline: `POST /api/run-pipeline`
2. Check logs for `[NO MATCH]` entries
3. Use debug endpoint: `GET /api/debug/matching`

### Improve Matching
1. Add team aliases to `TEAM_NAME_MAP` in `match_games.py`
2. Adjust `FUZZY_MATCH_THRESHOLD` (default: 82)
3. Add manual overrides to `MANUAL_EVENT_OVERRIDES`

### Common Issues

#### Low Match Rate
- Check normalization logs for team name issues
- Verify BetBCK scraping is working
- Review prop filtering logic

#### Pipeline Failures
- Check individual step logs
- Verify data files exist in `data/` directory
- Ensure all dependencies are installed

## Configuration

### Matching Thresholds
```python
FUZZY_MATCH_THRESHOLD = 82  # Minimum similarity score
MIN_COMPONENT_MATCH_SCORE = 78  # Component-level threshold
ORIENTATION_CONFIDENCE_MARGIN = 15  # Confidence margin
```

### Team Name Mapping
```python
TEAM_NAME_MAP = {
    "internazionale": "inter milan",
    "manchester united": "man united",
    # Add more as needed
}
```

### Prop Filtering
```python
PROP_INDICATORS = [
    "to lift the trophy", "mvp", "futures",
    # Add more prop indicators
]
```

## File Structure

```
backend/
├── main_runner.py          # Main pipeline orchestration
├── match_games.py          # Fuzzy matching logic
├── calculate_ev_table.py   # EV calculations
├── buckeye_scraper.py      # Pinnacle event fetching
├── betbck_async_scraper.py # BetBCK HTML scraping
├── main.py                 # FastAPI endpoints
└── data/                   # Generated data files
    ├── buckeye_event_ids.json
    ├── betbck_games.json
    ├── matched_games.json
    └── ev_table.json
```

## Running the Pipeline

### Via API
```bash
curl -X POST http://localhost:8000/api/run-pipeline
```

### Via Script
```bash
cd backend
python test_pipeline.py
```

### Via Python
```python
from main_runner import get_buckeye_pipeline
import asyncio

pipeline = get_buckeye_pipeline()
result = asyncio.run(pipeline.run_full_pipeline())
```

## Dependencies

- `rapidfuzz` - Fuzzy string matching
- `aiohttp` - Async HTTP requests
- `beautifulsoup4` - HTML parsing
- `fastapi` - API framework

## Troubleshooting

### Event Loop Issues
- Never call `asyncio.run()` from within FastAPI endpoints
- Use `get_all_betbck_games()` only in scripts, not endpoints
- Use `_get_all_betbck_games_async()` in async contexts

### Memory Issues
- Large datasets may require memory optimization
- Consider chunking for very large event lists
- Monitor memory usage in logs

### Performance
- Pipeline typically takes 30-60 seconds
- BetBCK scraping is the slowest step
- Consider caching for repeated runs 