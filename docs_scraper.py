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

# React has two main sections we need to scrape
REACT_SECTIONS = {
    "learn": "https://react.dev/learn",
    "reference": "https://react.dev/reference/react"
}

OUT_DIR = "react/pages"
os.makedirs(OUT_DIR, exist_ok=True)

def setup_driver():
    """Setup headless Chrome with automatic driver management"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

visited_urls = set()
seen_text_hash = set()

def wait_for_react_content(driver, timeout=15):
    """Wait for React docs content to load - they use client-side rendering"""
    try:
        # Wait for main content
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "main, article, .content"))
        )
        
        # Wait for navigation to be populated
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "nav a, .sidebar a"))
        )
        
        # Extra wait for dynamic content and code examples
        time.sleep(3)
        return True
    except Exception as e:
        print(f"    ⚠️  Timeout waiting for content: {e}")
        return False

def extract_react_navigation_links(driver, base_url):
    """Extract all React documentation links from navigation"""
    links = set()
    
    try:
        # React docs use specific navigation patterns
        nav_selectors = [
            "nav a[href*='/learn']",
            "nav a[href*='/reference']", 
            ".sidebar a",
            "aside a",
            ".navigation a",
            "[data-testid='sidebar'] a",
            ".docs-nav a"
        ]
        
        for selector in nav_selectors:
            try:
                nav_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in nav_elements:
                    href = element.get_attribute("href")
                    if href and ("react.dev" in href or href.startswith("/")):
                        # Convert relative URLs to absolute
                        if href.startswith("/"):
                            href = f"https://react.dev{href}"
                        
                        # Only include learn and reference sections
                        if "/learn" in href or "/reference" in href:
                            links.add(href)
            except:
                continue
        
        # Also look for in-page navigation (table of contents)
        toc_links = driver.find_elements(By.CSS_SELECTOR, ".table-of-contents a, .toc a")
        for element in toc_links:
            href = element.get_attribute("href")
            if href and ("react.dev" in href or href.startswith("/")):
                if href.startswith("/"):
                    href = f"https://react.dev{href}"
                if "/learn" in href or "/reference" in href:
                    links.add(href)
                    
    except Exception as e:
        print(f"    ⚠️  Error extracting navigation: {e}")
    
    return list(links)

def get_react_page_content(driver):
    """Extract content from React documentation pages"""
    try:
        if not wait_for_react_content(driver):
            return ""
            
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", 
                           ".sidebar", ".navigation", ".breadcrumb"]):
            element.decompose()
        
        # React docs structure - try multiple content selectors
        content_selectors = [
            "main article",
            "main .content", 
            "main",
            "article",
            ".docs-content",
            ".markdown-body"
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
        
        if main_content:
            # Extract text while preserving code blocks
            text_parts = []
            
            # Get title
            title = soup.find("h1")
            if title:
                text_parts.append(f"# {title.get_text().strip()}\n")
            
            # Process content preserving structure
            for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre', 'code', 'ul', 'ol', 'li']):
                if element.name.startswith('h'):
                    level = int(element.name[1])
                    text_parts.append(f"{'#' * level} {element.get_text().strip()}\n")
                elif element.name == 'pre':
                    # Preserve code blocks
                    code_text = element.get_text().strip()
                    text_parts.append(f"``````\n")
                elif element.name == 'p':
                    text_parts.append(f"{element.get_text().strip()}\n")
                elif element.name in ['ul', 'ol']:
                    # Handle lists
                    for li in element.find_all('li', recursive=False):
                        text_parts.append(f"- {li.get_text().strip()}")
                    text_parts.append("")
            
            content = '\n'.join(text_parts)
        else:
            content = soup.get_text(separator="\n", strip=True)
        
        # Clean up
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('Skip to'):
                lines.append(line)
        
        return '\n'.join(lines)
        
    except Exception as e:
        print(f"    ❌ Error extracting content: {e}")
        return ""

def save_react_content(idx, content, url, section):
    """Save React content with better organization"""
    # Create section subdirectory
    section_dir = f"{OUT_DIR}/{section}"
    os.makedirs(section_dir, exist_ok=True)
    
    # Generate filename from URL
    url_path = urlparse(url).path
    path_parts = [p for p in url_path.split('/') if p and p not in ['learn', 'reference', 'react']]
    
    if path_parts:
        filename = '_'.join(path_parts)
    else:
        filename = "index"
    
    # Clean filename
    filename = re.sub(r'[^\w\-_]', '', filename)
    if not filename:
        filename = f"page_{idx}"
    
    filepath = f"{section_dir}/{idx:03d}_{filename}.txt"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Section: {section.title()}\n")
        f.write("=" * 60 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath}")
    return filepath

def scrape_react_section(driver, section_name, base_url):
    """Scrape a specific React documentation section"""
    print(f"\n🔍 Scraping React {section_name.title()} section...")
    
    # Load section page
    print(f"📄 Loading: {base_url}")
    driver.get(base_url)
    
    if not wait_for_react_content(driver):
        print(f"❌ Failed to load {section_name} section")
        return []
    
    # Extract all links in this section
    all_links = extract_react_navigation_links(driver, base_url)
    all_links.append(base_url)  # Include section index
    
    # Filter links for this section
    section_links = [link for link in all_links if f"/{section_name}" in link]
    unique_links = list(set(section_links))
    
    print(f"📋 Found {len(unique_links)} pages in {section_name} section")
    
    scraped_files = []
    idx = 1
    
    for url in unique_links:
        if url in visited_urls:
            continue
            
        visited_urls.add(url)
        print(f"  [{idx:03d}] 🌐 {url}")
        
        try:
            driver.get(url)
            content = get_react_page_content(driver)
            
            if not content or len(content.strip()) < 100:
                print("    ⚠️  No meaningful content found")
                continue
            
            # Check for duplicate content
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            if content_hash in seen_text_hash:
                print("    ⚠️  Duplicate content - skipped")
                continue
            
            seen_text_hash.add(content_hash)
            filepath = save_react_content(idx, content, url, section_name)
            scraped_files.append(filepath)
            idx += 1
            
            # Be respectful to React's servers
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ Error scraping {url}: {e}")
            continue
    
    return scraped_files

def scrape_react_docs():
    """Main React documentation scraping function"""
    driver = setup_driver()
    all_files = []
    
    try:
        print("🚀 Starting React documentation scrape...")
        print("📚 This will scrape both Learn and Reference sections")
        
        for section_name, base_url in REACT_SECTIONS.items():
            files = scrape_react_section(driver, section_name, base_url)
            all_files.extend(files)
        
        print(f"\n🎉 React scraping complete!")
        print(f"📊 Successfully scraped {len(all_files)} unique pages")
        print(f"📁 Files saved to: {OUT_DIR}/")
        
        return all_files
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scraped_files = scrape_react_docs()
    
    print(f"\n⏱️  Total time: {time.time() - start_time:.1f}s")
    print(f"📝 Next step: Run generate_llms.py to create the minified llms.txt file")
