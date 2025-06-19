
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

BASE_URL = "https://help.figma.com/hc/en-us/categories/360002042553-Figma-Design"
OUT_DIR = "figma/pages"
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
    """Wait for the main content to load - Figma help center can be slow"""
    try:
        # Wait for either article content or section list
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".section-list")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".article-list")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='article-content']"))
            )
        )
        time.sleep(3)  # Extra wait for dynamic content
        return True
    except:
        return False

def extract_figma_links(driver, base_url):
    """Extract all Figma documentation links from categories and sections"""
    links = set()
    
    try:
        # Look for section links (categories and subcategories)
        section_links = driver.find_elements(By.CSS_SELECTOR, 
            "a[href*='/hc/en-us/sections/'], .section-list a, .category-list a")
        
        for element in section_links:
            href = element.get_attribute("href")
            if href and "figma" in href.lower():
                links.add(href)
        
        # Look for article links
        article_links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/hc/en-us/articles/'], .article-list a, .article-title a")
        
        for element in article_links:
            href = element.get_attribute("href")
            if href and "figma" in href.lower():
                links.add(href)
        
        # Look for "See all X articles" links
        see_all_links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='articles'], a[href*='section']")
        
        for element in see_all_links:
            href = element.get_attribute("href")
            text = element.text.lower()
            if href and ("see all" in text or "articles" in text) and "figma" in href.lower():
                links.add(href)
                
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    return list(links)

def crawl_section_page(driver, section_url):
    """Crawl a section page to get all article links"""
    article_links = set()
    
    try:
        print(f"  🔍 Crawling section: {section_url}")
        driver.get(section_url)
        
        if not wait_for_content(driver):
            return list(article_links)
        
        # Look for article links in this section
        articles = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='/hc/en-us/articles/'], .article-list a, .article-title a, .article-link")
        
        for article in articles:
            href = article.get_attribute("href")
            if href and "/articles/" in href:
                article_links.add(href)
        
        # Check for pagination
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, 
                "a[rel='next'], .pagination-next, .next")
            if next_button and next_button.is_enabled():
                next_url = next_button.get_attribute("href")
                if next_url:
                    time.sleep(2)
                    more_articles = crawl_section_page(driver, next_url)
                    article_links.update(more_articles)
        except:
            pass  # No pagination
            
    except Exception as e:
        print(f"    ❌ Error crawling section {section_url}: {e}")
    
    return list(article_links)

def get_page_content(driver):
    """Extract meaningful content from Figma help pages"""
    try:
        if not wait_for_content(driver):
            return ""
            
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", 
                           ".sidebar", ".navigation", ".breadcrumbs"]):
            element.decompose()
        
        # Try to find main content - Figma uses various containers
        main_content = (
            soup.find("article") or
            soup.find(attrs={"data-testid": "article-content"}) or
            soup.find(class_="article-body") or
            soup.find(class_="article-content") or
            soup.find("main") or
            soup.find(class_="section-list") or
            soup.find(class_="article-list")
        )
        
        if main_content:
            # Get title if available
            title_elem = (
                soup.find("h1") or 
                soup.find(class_="article-title") or
                soup.find(attrs={"data-testid": "article-title"})
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
                lines.append(line)
        
        return '\n'.join(lines)
        
    except Exception as e:
        print(f"Error extracting content: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with better naming for Figma structure"""
    # Extract meaningful filename from URL
    url_parts = url.split('/')
    
    # For articles, try to get article ID and title
    if '/articles/' in url:
        article_part = None
        for i, part in enumerate(url_parts):
            if part == 'articles' and i + 1 < len(url_parts):
                article_part = url_parts[i + 1]
                break
        
        if article_part:
            # Clean up article ID/title
            filename = re.sub(r'^\d+-', '', article_part)  # Remove leading numbers
            filename = filename.replace('-', '_')
        else:
            filename = "article"
    
    # For sections
    elif '/sections/' in url:
        section_part = None
        for i, part in enumerate(url_parts):
            if part == 'sections' and i + 1 < len(url_parts):
                section_part = url_parts[i + 1]
                break
        
        if section_part:
            filename = f"section_{section_part.replace('-', '_')}"
        else:
            filename = "section"
    
    # For categories
    elif '/categories/' in url:
        filename = "category_figma_design"
    
    else:
        filename = f"page_{idx}"
    
    # Clean filename
    filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()
    if not filename:
        filename = f"page_{idx}"
    
    filepath = f"{OUT_DIR}/{idx:03d}_{filename}.txt"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 50 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath}")

def scrape_figma():
    """Main scraping function for Figma documentation"""
    driver = setup_driver()
    
    try:
        print("🚀 Starting Figma documentation scrape...")
        
        # Load main category page
        print(f"📄 Loading main category: {BASE_URL}")
        driver.get(BASE_URL)
        
        if not wait_for_content(driver):
            print("❌ Failed to load main page content")
            return
        
        # Get initial links from main category
        print("🔍 Extracting initial links...")
        all_links = extract_figma_links(driver, BASE_URL)
        all_links.append(BASE_URL)  # Include main category page
        
        # Separate sections from articles
        section_links = [link for link in all_links if '/sections/' in link]
        article_links = [link for link in all_links if '/articles/' in link]
        
        print(f"📋 Found {len(section_links)} sections and {len(article_links)} articles")
        
        # Crawl each section to get more articles
        print("🕷️  Crawling sections for articles...")
        for section_url in section_links:
            if section_url not in visited_urls:
                section_articles = crawl_section_page(driver, section_url)
                article_links.extend(section_articles)
                visited_urls.add(section_url)
                time.sleep(2)  # Be nice to Figma's servers
        
        # Remove duplicates
        unique_articles = list(set(article_links))
        all_pages = section_links + unique_articles + [BASE_URL]
        unique_pages = list(set(all_pages))
        
        print(f"📊 Total unique pages to scrape: {len(unique_pages)}")
        
        idx = 1
        successful_scrapes = 0
        
        for url in unique_pages:
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
                
                # Be extra nice to Figma's servers
                time.sleep(2)
                
            except Exception as e:
                print(f"    ❌ Error scraping {url}: {e}")
                continue
        
        print(f"\n🎉 Figma scraping complete!")
        print(f"📊 Successfully scraped {successful_scrapes} unique pages")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scrape_figma()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
