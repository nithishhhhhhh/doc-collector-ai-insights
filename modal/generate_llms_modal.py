
import os
import glob
from pathlib import Path
import re

def minify_content(content):
    """Minify content while preserving structure"""
    lines = []
    for line in content.split('\n'):
        line = line.strip()
        # Keep non-empty lines and preserve code structure
        if line and not line.startswith(('©', 'Cookie', 'Privacy', 'Terms')):
            lines.append(line)
    return '\n'.join(lines)

def process_github_files(github_dir):
    """Process GitHub files with better organization"""
    github_content = []
    
    if not os.path.exists(github_dir):
        return github_content
    
    # Organize files by category
    categories = {
        'getting_started': '01_getting_started',
        'containers': '02_building_containers', 
        'scaling': '03_scaling_out',
        'secrets': '04_secrets',
        'scheduling': '05_scheduling',
        'gpu_ml': '06_gpu_and_ml',
        'web_endpoints': '07_web_endpoints',
        'advanced': '08_advanced',
        'job_queues': '09_job_queues',
        'integrations': '10_integrations',
        'notebooks': '11_notebooks',
        'datasets': '12_datasets',
        'sandboxes': '13_sandboxes',
        'clusters': '14_clusters',
        'misc': 'misc',
        'internal': 'internal'
    }
    
    for category, folder_prefix in categories.items():
        category_files = []
        
        # Find all files in this category
        for root, dirs, files in os.walk(github_dir):
            if folder_prefix in root:
                for file in files:
                    if file.endswith(('.py', '.md', '.yml', '.yaml', '.txt')):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, github_dir)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if content.strip():  # Only include non-empty files
                                    category_files.append(f"=== GITHUB: {rel_path} ===\n{content}\n")
                        except Exception as e:
                            print(f"⚠️  Error reading {file_path}: {e}")
        
        if category_files:
            github_content.append(f"\n=== CATEGORY: {category.upper()} ===\n")
            github_content.extend(category_files)
    
    return github_content

def generate_llms_txt(site_folder):
    """Generate comprehensive llms.txt for a site folder"""
    pages_dir = os.path.join(site_folder, "pages")
    github_dir = os.path.join(site_folder, "github_examples")
    llms_file = os.path.join(site_folder, "llms.txt")
    
    if not os.path.exists(pages_dir):
        print(f"❌ No pages directory found in {site_folder}")
        return
    
    print(f"🔄 Generating llms.txt for {site_folder}...")
    
    all_content = []
    
    # Add header with metadata
    all_content.append(f"=== {site_folder.upper()} DOCUMENTATION COLLECTION ===")
    all_content.append(f"Generated: {Path().absolute()}")
    all_content.append(f"Source: Documentation scraper")
    all_content.append("=" * 60 + "\n")
    
    # Process documentation pages
    print(f"📄 Processing documentation pages...")
    txt_files = sorted(glob.glob(os.path.join(pages_dir, "*.txt")))
    doc_sections = []
    
    for file_path in txt_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract URL from content
                url_line = content.split('\n')[0] if content.startswith('URL:') else ""
                
                # Remove URL line and separator for cleaner content
                if content.startswith('URL:'):
                    content_lines = content.split('\n')[2:]  # Skip URL and separator
                    content = '\n'.join(content_lines)
                
                minified = minify_content(content)
                if len(minified.strip()) > 50:  # Only include substantial content
                    filename = os.path.basename(file_path)
                    doc_sections.append(f"=== DOC: {filename} ===\n{url_line}\n{minified}\n")
                    
        except Exception as e:
            print(f"⚠️  Error reading {file_path}: {e}")
    
    all_content.extend(doc_sections)
    print(f"✅ Processed {len(doc_sections)} documentation pages")
    
    # Process GitHub examples
    if os.path.exists(github_dir):
        print(f"📁 Processing GitHub examples...")
        github_content = process_github_files(github_dir)
        all_content.extend(github_content)
        print(f"✅ Processed GitHub examples from {github_dir}")
    else:
        print(f"⚠️  No GitHub directory found at {github_dir}")
    
    # Write combined content
    try:
        with open(llms_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_content))
        
        file_size_mb = os.path.getsize(llms_file) / 1024 / 1024
        print(f"✅ Generated {llms_file}")
        print(f"📊 Total sections: {len([c for c in all_content if c.startswith('===')])} ")
        print(f"📊 File size: {file_size_mb:.1f} MB")
        
        # Generate summary stats
        doc_count = len([c for c in all_content if c.startswith('=== DOC:')])
        github_count = len([c for c in all_content if c.startswith('=== GITHUB:')])
        category_count = len([c for c in all_content if c.startswith('=== CATEGORY:')])
        
        print(f"📈 Content breakdown:")
        print(f"   - Documentation pages: {doc_count}")
        print(f"   - GitHub files: {github_count}")
        print(f"   - GitHub categories: {category_count}")
        
    except Exception as e:
        print(f"❌ Error writing {llms_file}: {e}")

def generate_combined_llms():
    """Generate a master llms.txt combining all sites"""
    print("\n🔥 Generating master combined llms.txt...")
    
    all_sites_content = []
    sites_found = []
    
    for folder in ["animejs", "modal"]:
        if os.path.exists(folder):
            sites_found.append(folder)
            llms_file = os.path.join(folder, "llms.txt")
            
            if os.path.exists(llms_file):
                with open(llms_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_sites_content.append(f"\n{'='*80}")
                    all_sites_content.append(f"SITE: {folder.upper()}")
                    all_sites_content.append(f"{'='*80}\n")
                    all_sites_content.append(content)
    
    if all_sites_content:
        master_file = "master_llms.txt"
        with open(master_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_sites_content))
        
        file_size_mb = os.path.getsize(master_file) / 1024 / 1024
        print(f"🎯 Generated {master_file}")
        print(f"📊 Combined {len(sites_found)} sites: {', '.join(sites_found)}")
        print(f"📊 Total size: {file_size_mb:.1f} MB")
    else:
        print("❌ No site llms.txt files found to combine")

if __name__ == "__main__":
    print("🚀 Starting LLM file generation...")
    
    # Generate for individual sites
    sites_processed = 0
    for folder in ["animejs", "modal"]:
        if os.path.exists(folder):
            generate_llms_txt(folder)
            sites_processed += 1
        else:
            print(f"⚠️  Folder {folder} not found")
    
    if sites_processed > 0:
        # Generate master combined file
        generate_combined_llms()
        
        print(f"\n🎉 All done! Processed {sites_processed} sites")
        print("🎯 Your research, dev, and marketing teams now have:")
        print("   - Individual site llms.txt files")
        print("   - Master combined llms.txt file") 
        print("   - Organized GitHub examples by category")
        print("   - Minified content optimized for LLM consumption")
    else:
        print("❌ No sites found to process")
