# docs_scraper.py

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://animejs.com/documentation/"
OUTPUT_DIR = "animejs/pages"
os.makedirs(OUTPUT_DIR, exist_ok=True)

visited = set()

def save_page_content(url, idx):
    print(f"Fetching: {url}")
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    # Get main content from <main> or fallback to body
    main = soup.find("main") or soup.body
    text = main.get_text(separator="\n") if main else soup.get_text()

    with open(f"{OUTPUT_DIR}/{str(idx).zfill(3)}.txt", "w", encoding="utf-8") as f:
        f.write(text)

def crawl(start_url):
    queue = [start_url]
    idx = 1

    while queue:
        url = queue.pop()
        if url in visited:
            continue
        visited.add(url)
        try:
            save_page_content(url, idx)
            idx += 1
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a['href']
                full_url = urljoin(BASE_URL, href)
                if full_url.startswith(BASE_URL) and full_url not in visited:
                    queue.append(full_url)
        except Exception as e:
            print(f"Error on {url}: {e}")

crawl(BASE_URL)
