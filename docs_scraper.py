import os, hashlib, time, json, re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://nextjs.org/docs"
EXAMPLES_URL = "https://nextjs.org/examples"
OUT_DIR = "nextjs/pages"
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
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

visited_urls = set()
seen_text_hash = set()

def wait_for_content(driver, timeout=20):
    """Wait for Next.js docs content to load"""
    try:
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-docs-content]")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".nextra-content")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, ".docs-content"))
            )
        )
        time.sleep(4)
        return True
    except:
        return False

def extract_nextjs_hydration_data(driver):
    """Extract data from Next.js hydration scripts"""
    hydration_data = {}
    
    try:
        next_data_script = driver.find_element(By.ID, "__NEXT_DATA__")
        if next_data_script:
            try:
                data = json.loads(next_data_script.get_attribute("innerHTML"))
                hydration_data['next_data'] = data
            except:
                pass
    except:
        pass
    
    try:
        script_elements = driver.find_elements(By.TAG_NAME, "script")
        for script in script_elements:
            content = script.get_attribute("innerHTML")
            if content and "self.__next_f.push" in content:
                hydration_data['next_f_push'] = content
                break
    except:
        pass
    
    return hydration_data

def extract_nextjs_links(driver, base_url):
    """Extract all Next.js documentation and example links"""
    links = set()
    
    try:
        nav_selectors = [
            "nav a", ".sidebar a", ".navigation a", ".menu a", 
            "aside a", ".toc a", "[data-sidebar] a", ".nextra-sidebar a",
            ".docs-sidebar a", "[data-docs-sidebar] a"
        ]
        
        for selector in nav_selectors:
            nav_elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in nav_elements:
                href = element.get_attribute("href")
                if href and ("nextjs.org/docs" in href or "nextjs.org/examples" in href):
                    links.add(href)
        
        content_links = driver.find_elements(By.CSS_SELECTOR,
            "main a, article a, .content a, .nextra-content a, [data-docs-content] a")
        
        for element in content_links:
            href = element.get_attribute("href")
            if href and ("nextjs.org/docs" in href or "nextjs.org/examples" in href):
                links.add(href)
        
        router_links = driver.find_elements(By.CSS_SELECTOR,
            "a[href*='app'], a[href*='pages'], .router-toggle a, [data-router] a")
        
        for element in router_links:
            href = element.get_attribute("href")
            if href and "nextjs.org/docs" in href:
                links.add(href)
                
    except Exception as e:
        print(f"Error extracting links: {e}")
    
    return list(links)

def discover_all_docs_sections(driver):
    """Discover all documentation sections including both routers"""
    all_sections = set()
    
    main_sections = [
        "https://nextjs.org/docs",
        "https://nextjs.org/docs/app",
        "https://nextjs.org/docs/pages", 
        "https://nextjs.org/examples"
    ]
    
    for section_url in main_sections:
        try:
            print(f"  🔍 Discovering from: {section_url}")
            driver.get(section_url)
            
            if not wait_for_content(driver):
                continue
            
            section_links = extract_nextjs_links(driver, section_url)
            all_sections.update(section_links)
            
            try:
                show_more_buttons = driver.find_elements(By.CSS_SELECTOR,
                    "button[aria-label*='more'], .show-more, .load-more, .pagination a")
                
                for button in show_more_buttons:
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)
                        more_links = extract_nextjs_links(driver, section_url)
                        all_sections.update(more_links)
                    except:
                        pass
            except:
                pass
                
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ Error discovering section {section_url}: {e}")
    
    return list(all_sections)

def get_page_content(driver):
    """Extract meaningful content from Next.js pages"""
    try:
        if not wait_for_content(driver):
            return ""
        
        hydration_data = extract_nextjs_hydration_data(driver)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        
        for element in soup(["script", "style", "nav", "header", "footer", 
                           ".sidebar", ".navigation", ".nextra-sidebar", 
                           ".docs-sidebar", ".breadcrumbs", ".toc"]):
            element.decompose()
        
        main_content = (
            soup.find("main") or
            soup.find(attrs={"data-docs-content": True}) or
            soup.find(class_="nextra-content") or
            soup.find(class_="docs-content") or
            soup.find("article") or
            soup.find(class_="content")
        )
        
        if main_content:
            title_elem = (
                soup.find("h1") or 
                soup.find(class_="docs-title") or
                soup.find(attrs={"data-docs-title": True})
            )
            
            title = title_elem.get_text(strip=True) if title_elem else ""
            content = main_content.get_text(separator="\n", strip=True)
            
            if title and title not in content:
                content = f"{title}\n{'=' * len(title)}\n\n{content}"
        else:
            content = soup.get_text(separator="\n", strip=True)
        
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and len(line) > 2:
                if not any(nav_text in line.lower() for nav_text in 
                          ['edit on github', 'feedback', 'was this helpful', 
                           'next.js', 'vercel', 'deploy']):
                    lines.append(line)
        
        clean_content = '\n'.join(lines)
        
        if hydration_:
            clean_content += "\n\n--- HYDRATION DATA ---\n"
            if 'next_data' in hydration_:
                clean_content += f"\n__NEXT_DATA__:\n{json.dumps(hydration_data['next_data'], indent=2)}"
            if 'next_f_push' in hydration_:
                clean_content += f"\n\nself.__next_f.push data found in scripts"
        
        return clean_content
        
    except Exception as e:
        print(f"Error extracting content: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with better naming for Next.js structure"""
    url_parts = url.split('/')
    
    if '#' in url:
        base_url, anchor = url.split('#', 1)
        url_parts = base_url.split('/')
        anchor_clean = re.sub(r'[^a-zA-Z0-9_-]', '_', anchor)
        filename_suffix = f"_{anchor_clean}"
    else:
        filename_suffix = ""
    
    if '/examples/' in url:
        example_name = url_parts[-1] if url_parts[-1] else url_parts[-2]
        filename = f"example_{example_name}"
    elif '/docs/app/' in url:
        doc_path = '/'.join(url_parts[url_parts.index('app')+1:])
        filename = f"app_{doc_path.replace('/', '_')}" if doc_path else "app_index"
    elif '/docs/pages/' in url:
        doc_path = '/'.join(url_parts[url_parts.index('pages')+1:])
        filename = f"pages_{doc_path.replace('/', '_')}" if doc_path else "pages_index"
    elif '/docs/' in url:
        doc_path = '/'.join(url_parts[url_parts.index('docs')+1:])
        filename = f"docs_{doc_path.replace('/', '_')}" if doc_path else "docs_index"
    else:
        filename = url_parts[-1] if url_parts[-1] else "index"
    
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

def scrape_nextjs():
    """Main scraping function for Next.js documentation"""
    driver = setup_driver()
    
    try:
        print("🚀 Starting Next.js documentation scrape...")
        
        print("🔍 Discovering all documentation sections...")
        all_links = discover_all_docs_sections(driver)
        
        important_links = [
            "https://nextjs.org/docs",
            "https://nextjs.org/docs/getting-started/installation",
            "https://nextjs.org/docs/app/getting-started",
            "https://nextjs.org/docs/pages/getting-started",
            "https://nextjs.org/docs/app/building-your-application/routing",
            "https://nextjs.org/docs/pages/building-your-application/routing",
            "https://nextjs.org/docs/app/api-reference",
            "https://nextjs.org/docs/pages/api-reference",
            "https://nextjs.org/examples"
        ]
        
        all_links.extend(important_links)
        
        unique_links = []
        for link in set(all_links):
            if ("nextjs.org/docs" in link or "nextjs.org/examples" in link):
                if not any(skip in link for skip in ['github.com', 'twitter.com', 'discord.com']):
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
                
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if content_hash in seen_text_hash:
                    print("    ⚠️  Duplicate content - skipped")
                    continue
                
                seen_text_hash.add(content_hash)
                save_content(idx, content, url)
                successful_scrapes += 1
                idx += 1
                
                time.sleep(3)
                
            except Exception as e:
                print(f"    ❌ Error scraping {url}: {e}")
                continue
        
        print(f"\n🎉 Next.js scraping complete!")
        print(f"📊 Successfully scraped {successful_scrapes} unique pages")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    start_time = time.time()
    scrape_nextjs()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
