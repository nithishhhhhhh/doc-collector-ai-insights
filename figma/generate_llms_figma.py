import os
import re
import json
from pathlib import Path

def minify_text(text):
    """Minify text by removing extra whitespace and empty lines"""
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\n\s*\n', '\n', text)  # Remove empty lines
    text = re.sub(r'[ \t]+', ' ', text)    # Normalize spaces/tabs
    text = re.sub(r'\n ', '\n', text)      # Remove leading spaces on lines
    
    # Remove common boilerplate patterns
    boilerplate_patterns = [
        r'Cookie Policy.*?(?=\n\n|\n[A-Z])',
        r'Privacy Policy.*?(?=\n\n|\n[A-Z])',
        r'Terms of Service.*?(?=\n\n|\n[A-Z])',
        r'Sign in.*?(?=\n\n|\n[A-Z])',
        r'Contact us.*?(?=\n\n|\n[A-Z])',
        r'Help Center.*?(?=\n\n|\n[A-Z])',
        r'Back to top.*?(?=\n\n|\n[A-Z])',
        r'Was this article helpful\?.*?(?=\n\n|\n[A-Z])',
        r'Submit a request.*?(?=\n\n|\n[A-Z])',
    ]
    
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
    
    return text.strip()

def extract_metadata(content):
    """Extract URL and title from content"""
    lines = content.split('\n')
    url = ""
    title = ""
    
    # Extract URL (should be first line)
    if lines and lines[0].startswith('URL: '):
        url = lines[0].replace('URL: ', '').strip()
    
    # Find title (usually after the separator line)
    for i, line in enumerate(lines):
        if '=' * 20 in line and i + 2 < len(lines):
            potential_title = lines[i + 2].strip()
            if potential_title and len(potential_title) < 200:
                title = potential_title
                break
    
    return url, title

def process_site_folder(site_folder):
    """Process a single site folder and generate llms.txt"""
    pages_dir = os.path.join(site_folder, 'pages')
    
    if not os.path.exists(pages_dir):
        print(f"⚠️  No pages directory found in {site_folder}")
        return
    
    # Get all .txt files and sort them
    txt_files = sorted([f for f in os.listdir(pages_dir) if f.endswith('.txt')])
    
    if not txt_files:
        print(f"⚠️  No .txt files found in {pages_dir}")
        return
    
    print(f"📁 Processing {site_folder} ({len(txt_files)} files)")
    
    combined_content = []
    metadata_list = []
    
    for filename in txt_files:
        filepath = os.path.join(pages_dir, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if len(content.strip()) < 50:  # Skip very short files
                continue
            
            # Extract metadata
            url, title = extract_metadata(content)
            
            # Remove URL and separator lines from content
            lines = content.split('\n')
            content_start = 0
            for i, line in enumerate(lines):
                if '=' * 20 in line:
                    content_start = i + 1
                    break
            
            clean_content = '\n'.join(lines[content_start:])
            minified = minify_text(clean_content)
            
            if len(minified.strip()) < 30:  # Skip if too short after minification
                continue
            
            # Add to combined content with clear separation
            section_header = f"--- {title or filename} ---"
            combined_content.append(section_header)
            combined_content.append(minified)
            combined_content.append("")  # Empty line for separation
            
            # Track metadata
            metadata_list.append({
                'filename': filename,
                'title': title,
                'url': url,
                'content_length': len(minified)
            })
            
        except Exception as e:
            print(f"    ❌ Error processing {filename}: {e}")
            continue
    
    if not combined_content:
        print(f"    ⚠️  No valid content found to combine")
        return
    
    # Generate final combined text
    site_name = os.path.basename(site_folder).upper()
    header = f"{site_name} DOCUMENTATION\n{'=' * (len(site_name) + 13)}\n\n"
    
    final_content = header + '\n'.join(combined_content)
    
    # Save llms.txt
    llms_path = os.path.join(site_folder, 'llms.txt')
    with open(llms_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    # Save metadata
    metadata_path = os.path.join(site_folder, 'metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump({
            'site': site_name.lower(),
            'total_files': len(txt_files),
            'processed_files': len(metadata_list),
            'total_content_length': len(final_content),
            'files': metadata_list
        }, f, indent=2)
    
    print(f"    ✅ Generated {llms_path}")
    print(f"    📊 Combined {len(metadata_list)} files into {len(final_content):,} characters")
    print(f"    📋 Metadata saved to {metadata_path}")

def main():
    """Main function to process all site folders"""
    print("🚀 Starting llms.txt generation...")
    
    # Look for site folders in current directory
    current_dir = os.getcwd()
    site_folders = []
    
    # Common site folder names
    potential_folders = ['animejs', 'figma', 'bootstrap', 'modal']
    
    for folder in potential_folders:
        if os.path.exists(folder) and os.path.isdir(folder):
            site_folders.append(folder)
    
    # Also check for any folder with a 'pages' subdirectory
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        if (os.path.isdir(item_path) and 
            os.path.exists(os.path.join(item_path, 'pages')) and 
            item not in site_folders):
            site_folders.append(item)
    
    if not site_folders:
        print("❌ No site folders found with 'pages' subdirectories")
        print("   Expected folders like: animejs/, figma/, etc.")
        return
    
    print(f"📁 Found {len(site_folders)} site folders: {', '.join(site_folders)}")
    
    total_processed = 0
    for folder in site_folders:
        try:
            process_site_folder(folder)
            total_processed += 1
            print()  # Empty line between sites
        except Exception as e:
            print(f"❌ Error processing {folder}: {e}")
            continue
    
    print(f"🎉 Generation complete!")
    print(f"📊 Successfully processed {total_processed}/{len(site_folders)} site folders")
    
    # Show final summary
    print("\n📋 Summary:")
    for folder in site_folders:
        llms_path = os.path.join(folder, 'llms.txt')
        if os.path.exists(llms_path):
            size = os.path.getsize(llms_path)
            print(f"    {folder}/llms.txt - {size:,} bytes")

if __name__ == "__main__":
    main()
