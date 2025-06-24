import os, hashlib, time, json, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests

BASE_URL = "https://dribbble.com/search/ui"
OUT_DIR = "dribbble/pages"
PROFILES_DIR = "dribbble/profiles"
SHOTS_DIR = "dribbble/shots"

# Create all necessary directories
for directory in [OUT_DIR, PROFILES_DIR, SHOTS_DIR]:
    os.makedirs(directory, exist_ok=True)

def setup_driver():
    """Setup Chrome with stealth mode - because we're sneaky like that"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Execute script to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

visited_urls = set()
seen_content_hashes = set()

def scroll_and_load_more(driver, max_scrolls=10):
    """Scroll down to load more content - Dribbble loves its infinite scroll"""
    print("📜 Scrolling to load more content...")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scrolls = 0
    
    while scrolls < max_scrolls:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for new content to load
        time.sleep(3)
        
        # Calculate new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            print(f"    🛑 No more content to load after {scrolls} scrolls")
            break
            
        last_height = new_height
        scrolls += 1
        print(f"    📜 Scroll {scrolls}/{max_scrolls}")
    
    return scrolls

def extract_shot_links(driver):
    """Extract all shot/design links from the current page"""
    links = set()
    
    try:
        # Look for shot links - Dribbble uses various selectors
        shot_selectors = [
            "a[href*='/shots/']",
            ".shot-thumbnail a",
            ".dribbble-shot a",
            "[data-shot-id] a",
            ".shot-link"
        ]
        
        for selector in shot_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                href = element.get_attribute("href")
                if href and "/shots/" in href:
                    links.add(href)
        
        print(f"    🎯 Found {len(links)} shot links")
        
    except Exception as e:
        print(f"    ❌ Error extracting shot links: {e}")
    
    return list(links)

def extract_designer_links(driver):
    """Extract designer profile links"""
    links = set()
    
    try:
        # Look for designer profile links
        designer_selectors = [
            "a[href^='https://dribbble.com/'][href*='/']:not([href*='/shots/'])",
            ".user-link",
            ".designer-link",
            ".profile-link"
        ]
        
        for selector in designer_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                href = element.get_attribute("href")
                if href and "dribbble.com/" in href and "/shots/" not in href:
                    # Clean up the URL to get just the profile
                    if href.count('/') >= 4:  # https://dribbble.com/username
                        profile_url = '/'.join(href.split('/')[:4])
                        links.add(profile_url)
        
        print(f"    👤 Found {len(links)} designer profile links")
        
    except Exception as e:
        print(f"    ❌ Error extracting designer links: {e}")
    
    return list(links)

def get_page_content(driver, page_type="general"):
    """Extract content based on page type"""
    try:
        time.sleep(2)  # Let the page settle
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        content_parts = []
        
        if page_type == "shot":
            # Extract shot-specific content
            title = soup.find("h1") or soup.find(".shot-title")
            if title:
                content_parts.append(f"TITLE: {title.get_text(strip=True)}")
            
            description = soup.find(".shot-description") or soup.find(".description")
            if description:
                content_parts.append(f"DESCRIPTION: {description.get_text(strip=True)}")
            
            tags = soup.find_all(".tag") or soup.find_all("[data-tag]")
            if tags:
                tag_text = ", ".join([tag.get_text(strip=True) for tag in tags])
                content_parts.append(f"TAGS: {tag_text}")
                
        elif page_type == "profile":
            # Extract profile-specific content
            name = soup.find("h1") or soup.find(".profile-name")
            if name:
                content_parts.append(f"DESIGNER: {name.get_text(strip=True)}")
            
            bio = soup.find(".bio") or soup.find(".profile-bio")
            if bio:
                content_parts.append(f"BIO: {bio.get_text(strip=True)}")
            
            location = soup.find(".location")
            if location:
                content_parts.append(f"LOCATION: {location.get_text(strip=True)}")
            
            skills = soup.find_all(".skill") or soup.find_all(".tag")
            if skills:
                skills_text = ", ".join([skill.get_text(strip=True) for skill in skills])
                content_parts.append(f"SKILLS: {skills_text}")
        
        # Get general content
        main_content = (
            soup.find("main") or 
            soup.find(class_="content") or 
            soup.find("article") or 
            soup.body
        )
        
        if main_content:
            general_text = main_content.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in general_text.split('\n') if line.strip()]
            content_parts.extend(lines)
        
        return '\n'.join(content_parts)
        
    except Exception as e:
        print(f"    ❌ Error extracting content: {e}")
        return ""

def save_content(content, url, directory, prefix="page"):
    """Save content with smart naming"""
    if not content or len(content.strip()) < 50:
        return False
    
    # Check for duplicate content
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    if content_hash in seen_content_hashes:
        return False
    
    seen_content_hashes.add(content_hash)
    
    # Create filename from URL
    url_parts = url.split('/')
    if url_parts[-1] and url_parts[-1] != '':
        filename = url_parts[-1]
    elif len(url_parts) > 1:
        filename = url_parts[-2]
    else:
        filename = "index"
    
    # Clean filename
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    if not filename:
        filename = f"{prefix}_{int(time.time())}"
    
    filepath = f"{directory}/{prefix}_{filename}.txt"
    
    # Ensure unique filename
    counter = 1
    while os.path.exists(filepath):
        base, ext = os.path.splitext(filepath)
        filepath = f"{base}_{counter}{ext}"
        counter += 1
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write("=" * 50 + "\n\n")
        f.write(content)
    
    print(f"    ✅ Saved: {filepath}")
    return True

def scrape_search_results(driver, search_terms=["ui", "ux", "web design", "mobile app"]):
    """Scrape search results for different terms"""
    all_shot_links = set()
    all_designer_links = set()
    
    for term in search_terms:
        print(f"\n🔍 Searching for: '{term}'")
        search_url = f"https://dribbble.com/search/{term.replace(' ', '%20')}"
        
        try:
            driver.get(search_url)
            time.sleep(3)
            
            # Scroll to load more results
            scroll_and_load_more(driver, max_scrolls=5)
            
            # Extract links
            shot_links = extract_shot_links(driver)
            designer_links = extract_designer_links(driver)
            
            all_shot_links.update(shot_links)
            all_designer_links.update(designer_links)
            
            print(f"    📊 Total shots so far: {len(all_shot_links)}")
            print(f"    👥 Total designers so far: {len(all_designer_links)}")
            
        except Exception as e:
            print(f"    ❌ Error searching for '{term}': {e}")
    
    return list(all_shot_links), list(all_designer_links)

def scrape_dribbble():
    """Main scraping function - let's raid Dribbble's treasure trove"""
    driver = setup_driver()
    
    try:
        print("🎨 Starting Dribbble scrape - time to collect some design inspiration!")
        
        # First, scrape search results
        shot_links, designer_links = scrape_search_results(driver)
        
        print(f"\n📊 SUMMARY:")
        print(f"🎯 Found {len(shot_links)} unique shots")
        print(f"👤 Found {len(designer_links)} unique designers")
        
        # Scrape individual shots
        print(f"\n🎯 Scraping individual shots...")
        successful_shots = 0
        
        for i, url in enumerate(shot_links[:100], 1):  # Limit to first 100 shots
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            print(f"[{i:03d}] 🎨 {url}")
            
            try:
                driver.get(url)
                content = get_page_content(driver, "shot")
                
                if save_content(content, url, SHOTS_DIR, "shot"):
                    successful_shots += 1
                
                time.sleep(2)  # Be respectful
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        # Scrape designer profiles
        print(f"\n👤 Scraping designer profiles...")
        successful_profiles = 0
        
        for i, url in enumerate(designer_links[:50], 1):  # Limit to first 50 profiles
            if url in visited_urls:
                continue
                
            visited_urls.add(url)
            print(f"[{i:03d}] 👤 {url}")
            
            try:
                driver.get(url)
                content = get_page_content(driver, "profile")
                
                if save_content(content, url, PROFILES_DIR, "profile"):
                    successful_profiles += 1
                
                time.sleep(2)  # Be respectful
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        print(f"\n🎉 Dribbble scraping complete!")
        print(f"🎯 Successfully scraped {successful_shots} shots")
        print(f"👤 Successfully scraped {successful_profiles} profiles")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scrape_dribbble()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
