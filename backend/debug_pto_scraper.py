import logging
from config import settings  # Correct import
from pto_scraper import PTOScraper

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    scraper = PTOScraper(settings.__dict__)  # Pass as dict for config
    scraper.start_scraping()
    input("Press Enter to stop...\n")
    scraper.stop_scraping() 