

import os, hashlib, time, json, requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

BASE_URL = "https://modal.com/docs"
GITHUB_API_BASE = "https://api.github.com/repos/modal-labs/modal-examples"
OUT_DIR = "modal/pages"
GITHUB_DIR = "modal/github_examples"

# Add your GitHub token here to avoid rate limits
GITHUB_TOKEN = None  # Set this to your GitHub personal access token

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(GITHUB_DIR, exist_ok=True)

def setup_driver():
    """Setup Chrome with better options for Modal's React app"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

visited_urls = set()
seen_text_hash = set()

def wait_for_modal_content(driver, timeout=45):
    """Wait specifically for Modal's content structure"""
    try:
        # Try multiple strategies to detect when content is loaded
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='content']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".prose")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".markdown")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".docs-content")),
                # Look for navigation as a fallback
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label*='Sidebar']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar"))
            )
        )
        
        # Extra wait for React hydration and dynamic content
        time.sleep(8)
        
        # Check if we actually have meaningful content
        page_source = driver.page_source.lower()
        content_indicators = ["documentation", "guide", "examples", "reference", "modal"]
        has_content = any(indicator in page_source for indicator in content_indicators)
        
        return has_content
        
    except Exception as e:
        print(f"    ⚠️  Timeout waiting for content: {e}")
        return False

def extract_modal_links_aggressively(driver):
    """Extract all possible Modal documentation links"""
    links = set()
    
    # Wait a bit more for navigation to load
    time.sleep(5)
    
    try:
        # Cast a wider net for link extraction
        all_links = driver.find_elements(By.TAG_NAME, "a")
        
        for element in all_links:
            try:
                href = element.get_attribute("href")
                if href and "/docs/" in href:
                    if href.startswith("/"):
                        href = "https://modal.com" + href
                    elif href.startswith("https://modal.com/docs/"):
                        links.add(href)
            except:
                continue
                
        # Add some known important Modal documentation pages
        known_pages = [
            "https://modal.com/docs/guide",
            "https://modal.com/docs/guide/getting-started", 
            "https://modal.com/docs/guide/functions",
            "https://modal.com/docs/guide/containers",
            "https://modal.com/docs/guide/webhooks",
            "https://modal.com/docs/examples",
            "https://modal.com/docs/reference",
            "https://modal.com/docs/reference/modal.App",
            "https://modal.com/docs/reference/modal.Function",
            "https://modal.com/docs/reference/modal.Image",
        ]
        
        links.update(known_pages)
        
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    return list(links)

def get_modal_content(driver):
    """Extract content with multiple fallback strategies"""
    try:
        if not wait_for_modal_content(driver):
            print("    ⚠️  Content didn't load properly, trying anyway...")
            
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
        
        # Try multiple content selectors in order of preference
        content_selectors = [
            "main",
            "[data-testid='content']", 
            ".prose",
            "article",
            ".markdown-body",
            ".docs-content",
            ".content",
            "body"  # Last resort
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content and len(main_content.get_text(strip=True)) > 200:
                break
        
        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)
            
        # Clean and filter the text
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 3 and not line.startswith(('©', 'Cookie', 'Privacy')):
                lines.append(line)
                
        return '\n'.join(lines)
        
    except Exception as e:
        print(f"Error extracting content: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with better naming"""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p and p != 'docs']
    
    if path_parts:
        filename = '_'.join(path_parts)
    else:
        filename = "index"
    
    filename = re.sub(r'[^\w\-_]', '_', filename)
    filename = re.sub(r'_+', '_', filename).strip('_')
    
    if not filename:
        filename = f"page_{idx}"
    
    filepath = f"{OUT_DIR}/{idx:03d}_{filename}.txt"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 50 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath}")

def scrape_github_with_retry():
    """Scrape GitHub with better rate limit handling"""
    print("\n🐙 Scraping Modal GitHub examples with retry logic...")
    
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
        print("    🔑 Using GitHub token for higher rate limits")
    else:
        print("    ⚠️  No GitHub token - you'll hit rate limits faster")
    
    def get_repo_contents(path="", retries=3):
        url = f"{GITHUB_API_BASE}/contents/{path}"
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    print(f"    ⏳ Rate limit hit for {path}, waiting 60s...")
                    time.sleep(60)
                else:
                    print(f"    ❌ Error {response.status_code} for {path}")
                    break
            except Exception as e:
                print(f"    ❌ Exception for {path}: {e}")
                break
        return []
    
    def download_file(file_info, local_path):
        try:
            response = requests.get(file_info['download_url'])
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
        except Exception as e:
            print(f"    ❌ Error downloading {file_info['name']}: {e}")
            return False
    
    def process_directory(path="", local_base=""):
        contents = get_repo_contents(path)
        
        for item in contents:
            if item['type'] == 'file' and item['name'].endswith(('.py', '.md', '.txt', '.yml', '.yaml')):
                local_path = os.path.join(GITHUB_DIR, local_base, item['name'])
                if download_file(item, local_path):
                    print(f"    📥 Downloaded: {item['path']}")
                    
            elif item['type'] == 'dir' and not item['name'].startswith('.'):
                new_local_base = os.path.join(local_base, item['name'])
                process_directory(item['path'], new_local_base)
    
    process_directory()

def scrape_modal_docs():
    """Main scraping function with better error handling"""
    driver = setup_driver()
    
    try:
        print("🚀 Starting Modal documentation scrape...")
        print(f"📄 Loading main page: {BASE_URL}")
        
        driver.get(BASE_URL)
        
        # Try to get content from main page first
        main_content = get_modal_content(driver)
        if main_content and len(main_content.strip()) > 100:
            print("✅ Successfully loaded main page content!")
            save_content(1, main_content, BASE_URL)
        else:
            print("❌ Failed to load meaningful main page content")
        
        # Extract links
        print("🔍 Extracting navigation links...")
        all_links = extract_modal_links_aggressively(driver)
        
        print(f"📋 Found {len(all_links)} documentation pages to scrape")
        
        idx = 2  # Start from 2 since we used 1 for main page
        successful_scrapes = 1 if main_content else 0
        
        for url in all_links:
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            print(f"\n[{idx:03d}] 🌐 {url}")
            
            try:
                driver.get(url)
                content = get_modal_content(driver)
                
                if not content or len(content.strip()) < 100:
                    print("    ⚠️  No meaningful content found")
                    continue
                
                # Check for duplicate content
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if content_hash in seen_text_hash:
                    print("    ⚠️  Duplicate content - skipped")
                    continue
                
                seen_text_hash.add(content_hash)
                save_content(idx, content, url)
                successful_scrapes += 1
                idx += 1
                
                # Be respectful - Modal's servers deserve love too
                time.sleep(3)
                
            except Exception as e:
                print(f"    ❌ Error scraping {url}: {e}")
                continue
        
        print(f"\n🎉 Documentation scraping complete!")
        print(f"📊 Successfully scraped {successful_scrapes} unique pages")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    
    # Scrape documentation first
    scrape_modal_docs()
    
    # Then scrape GitHub examples
    scrape_github_with_retry()
    
    print(f"\n⏱️  Total time: {time.time() - start_time:.1f}s")
    print("🎯 Ready to generate llms.txt!")

