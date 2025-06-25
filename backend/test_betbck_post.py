import requests
from bs4 import BeautifulSoup
from betbck_scraper import login_to_betbck, BASE_HEADERS, SEARCH_ACTION_URL, get_search_prerequisites

# --- Start session and login ---
session = requests.Session()
if not login_to_betbck(session):
    print("Login failed. Exiting.")
    exit(1)

# --- POST to search page to get the game page and scrape inetWagerNumber ---
team_name = input("Enter team name to search for: ").strip()
search_payload = {
    "action": "Search",
    "keyword_search": team_name,
}
# Get prerequisites from the main page (or wherever you normally get them)
main_page_url = "https://betbck.com/Qubic/StraightSportSelection.php"
inetWagerNumber, inetSportSelection = get_search_prerequisites(session, main_page_url)
search_payload["inetWagerNumber"] = inetWagerNumber
search_payload["inetSportSelection"] = inetSportSelection

# POST to search for the game (mimic browser search exactly)
response = session.post(SEARCH_ACTION_URL, data=search_payload, headers=BASE_HEADERS)
print("Status code:", response.status_code)
print("First 500 chars of response:\n", response.text[:500])

with open("betbck_test_response.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Done! Check betbck_test_response.html for the result.") 