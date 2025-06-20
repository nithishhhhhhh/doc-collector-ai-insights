import os
import re
from pathlib import Path

def minify_text(text):
    """Minify text while preserving important structure"""
    lines = text.split('\n')
    minified_lines = []
    in_code_block = False

    for line in lines:
        # Check for code block marker (triple backticks)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            minified_lines.append(line.strip())
        elif in_code_block:
            minified_lines.append(line)
        else:
            # Minify regular text
            line = line.strip()
            if line:
                line = re.sub(r'\s+', ' ', line)
                minified_lines.append(line)

    return '\n'.join(minified_lines)

def generate_llms_txt(site_folder):
    """Generate llms.txt for a specific site folder"""
    site_path = Path(site_folder)
    pages_dir = site_path / "pages"

    if not pages_dir.exists():
        print(f"❌ No pages directory found in {site_folder}")
        return

    print(f"🔄 Processing {site_folder}...")

    all_content = []
    file_count = 0

    # Process all .txt files recursively
    for txt_file in pages_dir.rglob("*.txt"):
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract just the main content (skip metadata)
            if "=" * 50 in content or "=" * 60 in content:
                content_parts = content.split("=" * 50, 1)
                if len(content_parts) < 2:
                    content_parts = content.split("=" * 60, 1)
                if len(content_parts) > 1:
                    content = content_parts[1].strip()

            # Minify and add to collection
            minified = minify_text(content)
            if minified.strip():
                all_content.append(f"--- {txt_file.name} ---\n{minified}")
                file_count += 1

        except Exception as e:
            print(f"⚠️  Error processing {txt_file}: {e}")

    # Write combined llms.txt
    llms_file = site_path / "llms.txt"
    with open(llms_file, 'w', encoding='utf-8') as f:
        f.write(f"# {site_folder.upper()} Documentation\n")
        f.write(f"# Generated from {file_count} documentation pages\n")
        f.write(f"# Minified for LLM consumption\n\n")
        f.write('\n\n'.join(all_content))

    print(f"✅ Generated {llms_file} from {file_count} files")
    print(f"📏 File size: {llms_file.stat().st_size / 1024:.1f} KB")

def main():
    """Generate llms.txt for all site folders"""
    current_dir = Path('.')

    # Look for site folders (containing pages subdirectory)
    site_folders = []
    for item in current_dir.iterdir():
        if item.is_dir() and (item / "pages").exists():
            site_folders.append(item.name)

    if not site_folders:
        print("❌ No site folders with 'pages' subdirectory found")
        return

    print(f"🎯 Found site folders: {', '.join(site_folders)}")

    for folder in site_folders:
        generate_llms_txt(folder)

    print(f"\n🎉 All done! Generated llms.txt files for {len(site_folders)} sites")

if __name__ == "__main__":
    main()
