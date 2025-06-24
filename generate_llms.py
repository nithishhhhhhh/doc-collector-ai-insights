import os
import glob

def generate_llms_txt(base_folder):
    """Generate llms.txt for a given folder structure"""
    
    # Find all .txt files in subdirectories
    txt_files = []
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith('.txt') and file != 'llms.txt':
                txt_files.append(os.path.join(root, file))
    
    if not txt_files:
        print(f"⚠️  No .txt files found in {base_folder}")
        return
    
    print(f"📁 Processing {len(txt_files)} files in {base_folder}")
    
    # Combine all content
    combined_content = []
    
    for file_path in sorted(txt_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # Minify content - remove extra whitespace and empty lines
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                minified = ' '.join(lines)
                
                # Add separator
                combined_content.append(f"--- FILE: {os.path.relpath(file_path, base_folder)} ---")
                combined_content.append(minified)
                combined_content.append("")  # Empty line for separation
                
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
    
    # Write combined content to llms.txt
    llms_path = os.path.join(base_folder, 'llms.txt')
    
    with open(llms_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(combined_content))
    
    print(f"✅ Generated {llms_path}")
    print(f"📊 Total size: {len('\n'.join(combined_content))} characters")

def main():
    """Generate llms.txt for all project folders"""
    
    # Process AnimeJS (if it exists)
    if os.path.exists('animejs'):
        print("🎬 Processing AnimeJS...")
        generate_llms_txt('animejs')
    
    # Process Dribbble
    if os.path.exists('dribbble'):
        print("\n🎨 Processing Dribbble...")
        generate_llms_txt('dribbble')
    
    print("\n🎉 All llms.txt files generated!")

if __name__ == "__main__":
    main()
