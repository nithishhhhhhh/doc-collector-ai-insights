import requests
from bs4 import BeautifulSoup

# URL of the GitHub Wiki page
url = "https://github.com/juliangarnier/anime/wiki/Migrating-from-v3-to-v4"

# Fetch the page content
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Locate the main content container
content_div = soup.find("div", {"id": "wiki-content"})

# Extract all text content
text = content_div.get_text(separator="\n", strip=True)

with open("pages/anime_migration_v3_to_v4.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("Content extracted and saved to anime_migration_v3_to_v4.txt")
