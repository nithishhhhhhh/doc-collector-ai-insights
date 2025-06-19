import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
import re
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

BASE_URL = "https://getbootstrap.com/docs/5.3/"
OUT_DIR = "bootstrap/pages"
os.makedirs(OUT_DIR, exist_ok=True)

visited_urls = set()
seen_content_hash = set()
url_lock = threading.Lock()
content_lock = threading.Lock()

def setup_session():
    """Setup session with aggressive headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    })
    return session

def normalize_url(url):
    """Normalize URLs to avoid duplicates"""
    if not url:
        return None
        
    # Parse URL
    parsed = urlparse(url)
    
    # Skip non-Bootstrap docs URLs
    if '/docs/5.3/' not in parsed.path:
        return None
        
    # Clean path
    path = parsed.path
    if path.endswith('/') and path != '/':
        path = path[:-1]
    path = re.sub(r'/+', '/', path)
    
    # Remove fragments and most query params (keep essential ones)
    query = parse_qs(parsed.query)
    essential_params = {}
    
    # Reconstruct clean URL
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if essential_params:
        query_string = '&'.join([f"{k}={v[0]}" for k, v in essential_params.items()])
        normalized += f"?{query_string}"
        
    return normalized

def discover_bootstrap_links():
    """Discover ALL Bootstrap documentation links using multiple strategies"""
    session = setup_session()
    all_links = set()
    
    # Strategy 1: Start from main docs page and crawl sitemap-style
    main_pages = [
        f"{BASE_URL}",
        f"{BASE_URL}getting-started/introduction/",
        f"{BASE_URL}layout/breakpoints/",
        f"{BASE_URL}content/reboot/",
        f"{BASE_URL}forms/overview/",
        f"{BASE_URL}components/accordion/",
        f"{BASE_URL}helpers/clearfix/",
        f"{BASE_URL}utilities/api/",
        f"{BASE_URL}extend/approach/",
        f"{BASE_URL}customize/overview/",
        f"{BASE_URL}about/overview/",
        f"{BASE_URL}migration/",
        f"{BASE_URL}examples/"
    ]
    
    print("🔍 Phase 1: Discovering links from main pages...")
    for page in main_pages:
        try:
            resp = session.get(page, timeout=30)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # Extract all Bootstrap docs links
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/docs/5.3/' in href:
                        if href.startswith('/'):
                            full_url = urljoin('https://getbootstrap.com', href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = urljoin(page, href)
                            
                        normalized = normalize_url(full_url)
                        if normalized:
                            all_links.add(normalized)
        except Exception as e:
            print(f"Error fetching {page}: {e}")
    
    # Strategy 2: Generate URLs based on Bootstrap's known structure
    print("🔍 Phase 2: Generating URLs from known Bootstrap structure...")
    sections = {
        'getting-started': [
            'introduction', 'download', 'contents', 'browsers-devices', 
            'javascript', 'webpack', 'parcel', 'vite', 'accessibility',
            'rtl', 'contribute', 'rfs'
        ],
        'layout': [
            'breakpoints', 'containers', 'grid', 'columns', 'gutters',
            'utilities', 'z-index', 'css-grid'
        ],
        'content': [
            'reboot', 'typography', 'images', 'tables', 'figures'
        ],
        'forms': [
            'overview', 'form-control', 'select', 'checks-radios', 'range',
            'input-group', 'floating-labels', 'layout', 'validation'
        ],
        'components': [
            'accordion', 'alerts', 'badge', 'breadcrumb', 'buttons',
            'button-group', 'card', 'carousel', 'close-button', 'collapse',
            'dropdowns', 'list-group', 'modal', 'navbar', 'navs-tabs',
            'offcanvas', 'pagination', 'placeholders', 'popovers',
            'progress', 'scrollspy', 'spinners', 'toasts', 'tooltips'
        ],
        'helpers': [
            'clearfix', 'color-background', 'colored-links', 'focus-ring',
            'icon-link', 'position', 'ratio', 'stacks', 'stretched-link',
            'text-truncation', 'vertical-rule', 'visually-hidden'
        ],
        'utilities': [
            'api', 'background', 'borders', 'colors', 'display', 'flex',
            'float', 'interactions', 'link', 'object-fit', 'opacity',
            'overflow', 'position', 'shadows', 'sizing', 'spacing',
            'text', 'vertical-align', 'visibility', 'z-index'
        ],
        'extend': ['approach', 'icons'],
        'customize': [
            'overview', 'sass', 'options', 'color', 'color-modes',
            'components', 'css-variables', 'optimize'
        ],
        'about': ['overview', 'team', 'brand', 'license', 'translations']
    }
    
    for section, pages in sections.items():
        for page in pages:
            # Try both with and without trailing slash
            for url_pattern in [f"{BASE_URL}{section}/{page}/", f"{BASE_URL}{section}/{page}"]:
                normalized = normalize_url(url_pattern)
                if normalized:
                    all_links.add(normalized)
    
    # Add migration and examples
    all_links.add(f"{BASE_URL}migration/")
    all_links.add(f"{BASE_URL}examples/")
    
    print(f"📋 Discovered {len(all_links)} unique URLs to scrape")
    return list(all_links)

def get_page_content(session, url):
    """Extract content with multiple fallback strategies"""
    try:
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', '.bd-sidebar']):
            element.decompose()
        
        # Multiple content extraction strategies
        content_strategies = [
            # Strategy 1: Bootstrap-specific selectors
            lambda s: s.select_one('main .bd-content'),
            lambda s: s.select_one('.bd-content'),
            lambda s: s.select_one('main'),
            # Strategy 2: Container-based selectors  
            lambda s: s.select_one('.container-xxl .col-md-9'),
            lambda s: s.select_one('.container .col-md-9'),
            lambda s: s.select_one('.col-md-9'),
            # Strategy 3: Generic content selectors
            lambda s: s.select_one('article'),
            lambda s: s.select_one('.docs-content'),
            lambda s: s.select_one('#content'),
            # Strategy 4: Fallback to body
            lambda s: s.select_one('body')
        ]
        
        main_content = None
        for strategy in content_strategies:
            try:
                main_content = strategy(soup)
                if main_content and len(main_content.get_text(strip=True)) > 200:
                    break
            except:
                continue
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)
        
        # Aggressive text cleaning
        lines = []
        skip_patterns = [
            r'^©', r'^Cookie', r'^Privacy', r'^Terms', r'^Skip to',
            r'^Back to top', r'^Toggle navigation', r'^Bootstrap',
            r'^\s*$', r'^v5\.3', r'getbootstrap\.com'
        ]
        
        for line in text.split('\n'):
            line = line.strip()
            if len(line) > 3:
                # Skip lines matching unwanted patterns
                skip = False
                for pattern in skip_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        skip = True
                        break
                if not skip:
                    lines.append(line)
        
        cleaned_text = '\n'.join(lines)
        
        # Final validation - ensure we have substantial content
        if len(cleaned_text.strip()) < 100:
            return ""
            
        return cleaned_text
        
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        return ""

def save_content(idx, content, url):
    """Save content with enhanced naming"""
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split('/') if p and p not in ['docs', '5.3']]
    
    if path_parts:
        filename = '_'.join(path_parts)
    else:
        filename = 'index'
    
    # Enhanced filename cleaning
    filename = re.sub(r'[^\w\-_]', '_', filename)
    filename = re.sub(r'_+', '_', filename).strip('_')
    filename = filename[:100]  # Limit length
    
    if not filename:
        filename = f'page_{idx}'
    
    filepath = f'{OUT_DIR}/{idx:03d}_{filename}.txt'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"URL: {url}\n")
        f.write('=' * 50 + "\n\n")
        f.write(content)
    
    return filepath

def scrape_single_url(url, idx):
    """Scrape a single URL - used for threading"""
    session = setup_session()
    
    with url_lock:
        if url in visited_urls:
            return None
        visited_urls.add(url)
    
    print(f"[{idx:03d}] 🌐 {url}")
    
    try:
        content = get_page_content(session, url)
        
        if not content or len(content.strip()) < 100:
            print(f"    ⚠️  No meaningful content found")
            return None
        
        # Check for duplicate content
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        with content_lock:
            if content_hash in seen_content_hash:
                print(f"    ⚠️  Duplicate content - skipped")
                return None
            seen_content_hash.add(content_hash)
        
        filepath = save_content(idx, content, url)
        print(f"    ✅ Saved: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"    ❌ Error scraping {url}: {e}")
        return None

def scrape_bootstrap_docs():
    """Main scraping function with threading for speed"""
    print("🚀 Starting ULTRA-AGGRESSIVE Bootstrap documentation scrape...")
    
    # Discover all URLs
    all_links = discover_bootstrap_links()
    
    print(f"📋 Found {len(all_links)} URLs to scrape")
    print("🔥 Starting parallel scraping with 5 threads...")
    
    successful_scrapes = 0
    failed_scrapes = 0
    
    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all URLs for scraping
        future_to_url = {
            executor.submit(scrape_single_url, url, idx): (url, idx) 
            for idx, url in enumerate(all_links, 1)
        }
        
        # Process completed futures
        for future in as_completed(future_to_url):
            url, idx = future_to_url[future]
            try:
                result = future.result()
                if result:
                    successful_scrapes += 1
                else:
                    failed_scrapes += 1
            except Exception as e:
                print(f"    ❌ Exception for {url}: {e}")
                failed_scrapes += 1
    
    total_attempted = successful_scrapes + failed_scrapes
    success_rate = (successful_scrapes / len(all_links)) * 100 if all_links else 0
    
    print(f"\n🎉 Ultra-aggressive Bootstrap scraping complete!")
    print(f"📊 Successfully scraped: {successful_scrapes} pages")
    print(f"📊 Failed/Duplicate: {failed_scrapes} pages") 
    print(f"📊 Total discovered: {len(all_links)} pages")
    print(f"📊 Success rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("🎯 TARGET ACHIEVED: >80% success rate!")
    else:
        print(f"⚠️  Target not reached. Need {80 - success_rate:.1f}% more coverage.")

if __name__ == "__main__":
    start_time = time.time()
    scrape_bootstrap_docs()
    print(f"⏱️  Total time: {time.time() - start_time:.1f}s")
    print("🎯 Ready to generate llms.txt!")
