import json
import logging
from pto_scraper import PTOScraper

logging.basicConfig(level=logging.INFO)

with open('config.json') as f:
    config = json.load(f)

scraper = PTOScraper(config.get('pto', {}))
scraper.is_running = True  # Ensure the loop runs
scraper._scraping_loop()  # Run directly for debugging 