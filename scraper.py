# scraper.py - replace with your real scraping logic
import requests
from bs4 import BeautifulSoup

def scrape_data():
    url = "https://example.com"  # replace with real source
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    # Example: extract page title
    title = soup.title.string if soup.title else "No title"
    return {"url": url, "title": title}

