import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://animejs.com/documentation"
OUTPUT_DIR = "animejs/pages"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def normalize(url):
    """
    Strip fragment and trailing slash, so that
    https://animejs.com/documentation/#foo  → https://animejs.com/documentation
    https://animejs.com/documentation/       → https://animejs.com/documentation
    """
    parsed = urlparse(url)
    # rebuild without fragment, then rstrip slash
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return clean.rstrip('/')

visited = set()

def save_page_content(url, idx):
    print(f"[{idx:03d}] Fetching {url}")
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    main = soup.find("main") or soup.body
    text = main.get_text(separator="\n") if main else soup.get_text()

    with open(f"{OUTPUT_DIR}/{idx:03d}.txt", "w", encoding="utf-8") as f:
        f.write(text)

def crawl(start_url):
    start = normalize(start_url)
    queue = [start]
    visited.add(start)
    idx = 1

    while queue:
        url = queue.pop(0)
        try:
            save_page_content(url, idx)
            idx += 1

            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()

                # skip pure fragments, external links, mailto, javascript:
                if href.startswith("#") \
                   or href.startswith("mailto:") \
                   or href.startswith("javascript:"):
                    continue

                full = urljoin(BASE_URL, href)
                norm = normalize(full)

                # only docs pages under BASE_URL, and not yet visited
                if norm.startswith(BASE_URL) and norm not in visited:
                    visited.add(norm)
                    queue.append(norm)

        except Exception as e:
            print(f"  ❌ Error on {url}: {e}")

if __name__ == "__main__":
    crawl(BASE_URL)
