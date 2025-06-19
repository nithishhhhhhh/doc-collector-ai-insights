import os, hashlib, time, json, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://docs.pydantic.dev/2.11/api/base_model/"
OUT_DIR = "pydantic/pages"
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
    """Wait for the main content to load - Pydantic docs can be slow"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".content")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".md-content"))
            )
        )
        time.sleep(3)  # Extra wait for dynamic content
        return True
    except:
        return False

def extract_pydantic_links(driver, base_url):
    """Extract all Pydantic documentation links"""
    links = set()
    
    try:
        # Look for navigation links in sidebar and main content
        nav_selectors = [
            "nav a", ".md-nav a", ".sidebar a", ".navigation a", 
            ".menu a", "aside a", ".toc a", ".md-nav__link"
        ]
        
        for selector in nav_selectors:
            nav_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in nav_elements:
                href = element.get_attribute("href")
                if href and "docs.pydantic.dev" in href:
                    # Only include API documentation links
                    if "/api/" in href or href.startswith(base_url):
                        links.add(href)
        
        # Look for content area links
        content_links = driver.find_elements(By.CSS_SELECTOR,
            "main a, article a, .content a, .md-content a")
        
        for element in content_links:
            href = element.get_attribute("href")
            if href and "docs.pydantic.dev" in href and "/api/" in href:
                links.add(href)
        
        # Look for method/class anchor links on the same page
        anchor_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='#']")
        current_url = driver.current_url
        
        for element in anchor_links:
            href = element.get_attribute("href")
            if href and href.startswith('#'):
                full_url = current_url + href
                links.add(full_url)
                
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    return list(links)

def discover_api_sections(driver, base_url):
    """Discover all API sections from the main API page"""
    api_sections = set()
    
    try:
        # Navigate to main API page
        api_base = "https://docs.pydantic.dev/2.11/api/"
        print(f"  🔍 Discovering API sections from: {api_base}")
        driver.get(api_base)
        
        if not wait_for_content(driver):
            return list(api_sections)
        
        # Look for API section links
        section_links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/api/'], .md-nav a, nav a")
        
        for link in section_links:
            href = link.get_attribute("href")
            if href and "/api/" in href and "docs.pydantic.dev" in href:
                api_sections.add(href)
        
        # Also check for any table of contents or index pages
        toc_links = driver.find_elements(By.CSS_SELECTOR,
            ".toc a, .md-nav__item a, .navigation a")
        
        for link in toc_links:
            href = link.get_attribute("href")
            if href and "/api/" in href and "docs.pydantic.dev" in href:
                api_sections.add(href)
                
    except Exception as e:
        print(f"    ❌ Error discovering API sections: {e}")
    
    return list(api_sections)

def get_page_content(driver):
    """Extract meaningful content from Pydantic docs pages"""
    try:
        if not wait_for_content(driver):
            return ""
            
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", 
                           ".md-nav", ".md-header", ".md-footer", ".sidebar"]):
            element.decompose()
        
        # Try to find main content - Pydantic uses various containers
        main_content = (
            soup.find("main") or
            soup.find(class_="md-content") or
            soup.find(class_="content") or
            soup.find("article") or
            soup.find(class_="md-content__inner")
        )
        
        if main_content:
            # Get title if available
            title_elem = (
                soup.find("h1") or 
                soup.find(class_="md-content__title") or
                soup.find(attrs={"data-md-component": "title"})
            )
            
            title = title_elem.get_text(strip=True) if title_elem else ""
            content = main_content.get_text(separator="\n", strip=True)
            
            if title and title not in content:
                content = f"{title}\n{'=' * len(title)}\n\n{content}"
        else:
            content = soup.get_text(separator="\n", strip=True)
        
        # Clean up the text
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and len(line) > 2:  # Filter out very short lines
                # Remove common navigation text
                if not any(nav_text in line.lower() for nav_text in 
                          ['edit this page', 'last update', 'created', 'back to top']):
                    lines.append(line)
        
        return '\n'.join(lines)
        
    except Exception as e:
        print(f"Error extracting content: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with better naming for Pydantic structure"""
    # Extract meaningful filename from URL
    url_parts = url.split('/')
    
    # Handle anchor links
    if '#' in url:
        base_url, anchor = url.split('#', 1)
        url_parts = base_url.split('/')
        anchor_clean = re.sub(r'[^a-zA-Z0-9_-]', '_', anchor)
        filename_suffix = f"_{anchor_clean}"
    else:
        filename_suffix = ""
    
    # Get the last meaningful part of the URL
    if url_parts[-1] and url_parts[-1] != '/':
        filename = url_parts[-1]
    elif len(url_parts) > 1:
        filename = url_parts[-2]
    else:
        filename = "index"
    
    # Clean filename
    filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
    filename = f"{filename}{filename_suffix}"
    
    if not filename or filename == '_':
        filename = f"page_{idx}"
    
    filepath = f"{OUT_DIR}/{idx:03d}_{filename}.txt"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 50 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath}")

def scrape_pydantic():
    """Main scraping function for Pydantic documentation"""
    driver = setup_driver()
    
    try:
        print("🚀 Starting Pydantic documentation scrape...")
        
        # First, discover all API sections
        print("🔍 Discovering API sections...")
        api_sections = discover_api_sections(driver, BASE_URL)
        
        # Load main BaseModel page
        print(f"📄 Loading main BaseModel page: {BASE_URL}")
        driver.get(BASE_URL)
        
        if not wait_for_content(driver):
            print("❌ Failed to load main page content")
            return
        
        # Get initial links from BaseModel page
        print("🔍 Extracting BaseModel page links...")
        basemodel_links = extract_pydantic_links(driver, BASE_URL)
        
        # Combine all discovered links
        all_links = list(set(api_sections + basemodel_links + [BASE_URL]))
        
        # For each API section, extract more links
        print("🕷️  Crawling API sections for more links...")
        for section_url in api_sections[:10]:  # Limit to prevent infinite crawling
            if section_url not in visited_urls:
                try:
                    print(f"  📖 Crawling section: {section_url}")
                    driver.get(section_url)
                    if wait_for_content(driver):
                        section_links = extract_pydantic_links(driver, section_url)
                        all_links.extend(section_links)
                    visited_urls.add(section_url)
                    time.sleep(2)
                except Exception as e:
                    print(f"    ❌ Error crawling section {section_url}: {e}")
        
        # Remove duplicates and filter
        unique_links = []
        for link in set(all_links):
            # Only include Pydantic docs links
            if "docs.pydantic.dev" in link and ("/api/" in link or link == BASE_URL):
                unique_links.append(link)
        
        print(f"📊 Total unique pages to scrape: {len(unique_links)}")
        
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
                
                # Be respectful to Pydantic's servers
                time.sleep(2)
                
            except Exception as e:
                print(f"    ❌ Error scraping {url}: {e}")
                continue
        
        print(f"\n🎉 Pydantic scraping complete!")
        print(f"📊 Successfully scraped {successful_scrapes} unique pages")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scrape_pydantic()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
