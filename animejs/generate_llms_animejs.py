
import os
import glob

def generate_llms_txt(site_folder):
    """Generate llms.txt from all scraped pages"""
    pages_dir = os.path.join(site_folder, "pages")
    
    if not os.path.exists(pages_dir):
        print(f"❌ Pages directory not found: {pages_dir}")
        return
    
    # Get all text files
    txt_files = glob.glob(os.path.join(pages_dir, "*.txt"))
    
    if not txt_files:
        print(f"❌ No text files found in {pages_dir}")
        return
    
    print(f"📁 Found {len(txt_files)} text files")
    
    combined_content = []
    
    for txt_file in sorted(txt_files):
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    # Add separator between files
                    combined_content.append(f"\n{'='*60}")
                    combined_content.append(f"FILE: {os.path.basename(txt_file)}")
                    combined_content.append(f"{'='*60}\n")
                    combined_content.append(content)
        except Exception as e:
            print(f"⚠️  Error reading {txt_file}: {e}")
    
    # Write combined content
    llms_file = os.path.join(site_folder, "llms.txt")
    
    with open(llms_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(combined_content))
    
    print(f"✅ Generated: {llms_file}")
    print(f"📊 Total content length: {len(''.join(combined_content))} characters")

if __name__ == "__main__":
    generate_llms_txt("animejs")

    
