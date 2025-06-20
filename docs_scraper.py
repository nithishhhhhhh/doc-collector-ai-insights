import os, hashlib, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests

BASE_URL = "https://tframex.tesslate.com/"
OUT_DIR = "tframex/pages"
os.makedirs(OUT_DIR, exist_ok=True)

def setup_driver():
    """Setup headless Chrome with automatic driver management"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

visited_urls = set()
seen_text_hash = set()

def wait_for_content(driver, timeout=15):
    """Wait for the main content to load - TFrameX might be React-based"""
    try:
        # Wait for common content selectors
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".content")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='doc']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='page']")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".markdown")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".prose"))
            )
        )
        time.sleep(3)  # Extra wait for React/dynamic content
        return True
    except:
        print("    ⚠️  Timeout waiting for content")
        return False

def extract_navigation_links(driver):
    """Extract all TFrameX documentation links"""
    links = set()
    
    try:
        # Wait a bit more for navigation to load
        time.sleep(2)
        
        # Common documentation navigation selectors
        nav_selectors = [
            "nav a", ".sidebar a", ".navigation a", ".menu a", "aside a",
            "[class*='nav'] a", "[class*='sidebar'] a", "[class*='menu'] a",
            ".docs-nav a", ".doc-nav a", "[data-testid*='nav'] a",
            ".toc a", ".table-of-contents a", "[class*='toc'] a"
        ]
        
        for selector in nav_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    if href and is_valid_doc_link(href):
                        links.add(href)
            except:
                continue
        
        # Also check for hash-based navigation and anchor links
        hash_selectors = ["a[href*='#']", "a[href^='/']", "a[href*='tframex']"]
        for selector in hash_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    if href and is_valid_doc_link(href):
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            href = urljoin(BASE_URL, href)
                        links.add(href)
            except:
                continue
                
        # Look for any buttons or clickable elements that might reveal more content
        clickable_selectors = [
            "button[class*='expand']", "button[class*='toggle']", 
            "[class*='accordion']", "[class*='collaps']",
            ".expandable", "[data-toggle]"
        ]
        
        for selector in clickable_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(1)
                    except:
                        continue
            except:
                continue
                
    except Exception as e:
        print(f"    ❌ Error extracting navigation: {e}")
    
    return list(links)

def is_valid_doc_link(href):
    """Check if link is valid documentation link"""
    if not href:
        return False
    
    # Skip external links, images, downloads
    skip_patterns = [
        'mailto:', 'tel:', 'javascript:', '#top', '#bottom',
        '.pdf', '.zip', '.tar', '.gz', '.jpg', '.png', '.gif',
        'github.com', 'twitter.com', 'linkedin.com', 'youtube.com'
    ]
    
    for pattern in skip_patterns:
        if pattern in href.lower():
            return False
    
    # Include TFrameX related links
    include_patterns = ['tframex', 'tesslate', 'documentation', 'docs', 'guide', 'tutorial', 'api']
    
    # If it's a relative link or contains our keywords, include it
    if href.startswith('/') or href.startswith('#'):
        return True
        
    for pattern in include_patterns:
        if pattern in href.lower():
            return True
    
    return False

def get_page_content(driver):
    """Extract meaningful content from TFrameX pages"""
    try:
        if not wait_for_content(driver):
            return ""
            
        # Get page source and parse
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove noise elements
        for element in soup(["script", "style", "nav", "header", "footer", "noscript"]):
            element.decompose()
        
        # Remove common UI elements that aren't content
        noise_selectors = [
            "[class*='cookie']", "[class*='banner']", "[class*='popup']",
            "[class*='modal']", "[class*='overlay']", ".advertisement",
            "[class*='social']", "[class*='share']"
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Try to find main content in order of preference
        content_selectors = [
            "main", "[role='main']", ".main-content", "#main-content",
            ".content", "#content", ".page-content", ".doc-content",
            "article", ".article", ".documentation", ".docs",
            ".markdown", ".prose", ".md-content",
            "[class*='doc']", "[class*='page']"
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body or soup
        
        # Extract text with better formatting
        text = main_content.get_text(separator="\n", strip=True)
        
        # Clean up the text
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 2:  # Skip very short lines
                lines.append(line)
        
        # Remove excessive whitespace
        cleaned_text = '\n'.join(lines)
        
        # Try to extract code blocks separately for better formatting
        code_blocks = soup.find_all(['pre', 'code'])
        if code_blocks:
            cleaned_text += "\n\n=== CODE EXAMPLES ===\n"
            for i, block in enumerate(code_blocks):
                code_text = block.get_text(strip=True)
                if len(code_text) > 10:  # Only include substantial code blocks
                    cleaned_text += f"\n--- Code Block {i+1} ---\n{code_text}\n"
        
        return cleaned_text
        
    except Exception as e:
        print(f"    ❌ Error extracting content: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with TFrameX-specific naming"""
    # Create filename from URL
    parsed_url = urlparse(url)
    path_parts = [p for p in parsed_url.path.split('/') if p]
    
    if path_parts:
        filename = '_'.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[-1]
    else:
        filename = "index"
    
    # Include fragment (hash) in filename if present
    if parsed_url.fragment:
        filename += f"_{parsed_url.fragment}"
    
    # Clean filename
    filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()
    if not filename:
        filename = f"page_{idx}"
    
    # Limit filename length
    if len(filename) > 50:
        filename = filename[:50]
    
    filepath = f"{OUT_DIR}/{idx:03d}_{filename}.txt"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"SCRAPED: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath} ({len(content)} chars)")

def try_api_endpoints(base_url):
    """Try to find API documentation or additional endpoints"""
    api_paths = [
        '/api', '/docs', '/documentation', '/guide', '/tutorial',
        '/reference', '/examples', '/getting-started', '/quickstart'
    ]
    
    found_urls = []
    
    for path in api_paths:
        try:
            test_url = urljoin(base_url, path)
            response = requests.head(test_url, timeout=5)
            if response.status_code == 200:
                found_urls.append(test_url)
                print(f"    📋 Found endpoint: {test_url}")
        except:
            continue
    
    return found_urls

def scrape_tframex():
    """Main TFrameX scraping function"""
    driver = setup_driver()
    
    try:
        print("🚀 Starting TFrameX documentation scrape...")
        print(f"🎯 Target: {BASE_URL}")
        
        # Try to find additional API endpoints first
        print("🔍 Checking for additional endpoints...")
        api_urls = try_api_endpoints(BASE_URL)
        
        # Load main page
        print(f"📄 Loading main page: {BASE_URL}")
        driver.get(BASE_URL)
        
        # Wait and extract navigation
        if not wait_for_content(driver):
            print("❌ Failed to load main page content - trying anyway...")
        
        # Get all documentation links
        print("🔍 Extracting navigation links...")
        all_links = extract_navigation_links(driver)
        all_links.extend(api_urls)
        all_links.append(BASE_URL)  # Include main page
        
        # Remove duplicates and sort
        unique_links = list(set(all_links))
        print(f"📋 Found {len(unique_links)} unique pages to scrape")
        
        # Show what we found
        for i, link in enumerate(unique_links[:10]):  # Show first 10
            print(f"    {i+1}. {link}")
        if len(unique_links) > 10:
            print(f"    ... and {len(unique_links) - 10} more")
        
        idx = 1
        successful_scrapes = 0
        
        for url in unique_links:
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            print(f"\n[{idx:03d}] 🌐 {url}")
            
            try:
                driver.get(url)
                content = get_page_content(driver)
                
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
                
                # Be respectful to the server
                time.sleep(2)
                
            except Exception as e:
                print(f"    ❌ Error scraping {url}: {e}")
                continue
        
        print(f"\n🎉 TFrameX scraping complete!")
        print(f"📊 Successfully scraped {successful_scrapes} unique pages")
        print(f"💾 Files saved to: {OUT_DIR}/")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scrape_tframex()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
