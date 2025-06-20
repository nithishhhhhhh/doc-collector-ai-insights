import os
import re
import json
from pathlib import Path
from datetime import datetime

def minify_text(text):
    """Minify text by removing excessive whitespace while preserving structure"""
    # Remove multiple consecutive spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove multiple consecutive newlines (keep max 2 for readability)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove trailing/leading whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    
    # Remove empty lines at start/end but keep internal structure
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    
    return '\n'.join(lines)

def clean_tframex_content(content):
    """Clean and optimize TFrameX content for LLM consumption"""
    # Remove URL line and separator
    lines = content.split('\n')
    if lines and lines[0].startswith('URL:'):
        lines = lines[1:]
    if lines and lines[0].startswith('SCRAPED:'):
        lines = lines[1:]
    if lines and '=' in lines[0]:
        lines = lines[1:]
    
    content = '\n'.join(lines).strip()
    
    # Remove excessive punctuation repetition
    content = re.sub(r'[=\-_]{4,}', '---', content)
    
    # Normalize section headers
    content = re.sub(r'^#+\s*', '## ', content, flags=re.MULTILINE)
    
    # Clean up TFrameX-specific artifacts
    tframex_artifacts = [
        r'Table of Contents?',
        r'Skip to (?:main )?content',
        r'Edit this page',
        r'Last updated:.*',
        r'Copyright.*Tesslate.*',
        r'All rights reserved',
        r'Back to top',
        r'Print this page',
        r'=== CODE EXAMPLES ===',
        r'--- Code Block \d+ ---'
    ]
    
    for artifact in tframex_artifacts:
        content = re.sub(artifact, '', content, flags=re.IGNORECASE)
    
    # Preserve TFrameX-specific patterns and terminology
    # Keep pattern names, agent types, etc. clearly formatted
    content = re.sub(r'(SequentialPattern|RouterPattern|ConditionalPattern|LoopPattern)', r'**\1**', content)
    content = re.sub(r'(Agent|Tool|Pattern|Framework)', r'**\1**', content)
    
    return minify_text(content)

def generate_tframex_llms():
    """Generate llms.txt specifically for TFrameX documentation"""
    tframex_path = Path("tframex")
    pages_path = tframex_path / "pages"
    
    if not pages_path.exists():
        print("❌ TFrameX pages folder not found!")
        print("   Expected: tframex/pages/")
        return False
    
    print("🔄 Processing TFrameX documentation...")
    
    # Get all .txt files in pages folder
    txt_files = list(pages_path.glob("*.txt"))
    if not txt_files:
        print("❌ No .txt files found in tframex/pages/")
        return False
    
    # Sort files by name for consistent ordering
    txt_files.sort()
    
    all_content = []
    total_chars = 0
    processed_files = 0
    
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Clean and minify content
            cleaned_content = clean_tframex_content(content)
            
            if len(cleaned_content.strip()) < 100:  # Skip very short content
                print(f"    ⚠️  Skipping {txt_file.name} (too short)")
                continue
            
            # Add file separator with filename
            file_header = f"\n## {txt_file.stem.upper().replace('_', ' ')}\n"
            all_content.append(file_header + cleaned_content)
            
            total_chars += len(cleaned_content)
            processed_files += 1
            
            print(f"    ✅ {txt_file.name} ({len(cleaned_content):,} chars)")
            
        except Exception as e:
            print(f"    ❌ Error processing {txt_file.name}: {e}")
            continue
    
    if not all_content:
        print("❌ No valid content found for TFrameX")
        return False
    
    # Generate TFrameX-specific summary header
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    summary = f"""# TFRAMEX DOCUMENTATION
Generated: {timestamp}
Files processed: {processed_files}
Total characters: {total_chars:,}
Source: https://tframex.tesslate.com/

## OVERVIEW
This file contains the complete TFrameX documentation, minified and optimized for LLM consumption.
TFrameX is a powerful framework for building AI agents with various patterns, tools, and workflows.
All content has been cleaned, deduplicated, and formatted for maximum information density.

Key concepts covered:
- **Patterns**: SequentialPattern, RouterPattern, ConditionalPattern, LoopPattern
- **Agents**: AI agent creation and management
- **Tools**: Built-in and custom tools for agent workflows
- **Framework**: Core TFrameX architecture and usage

---

"""
    
    # Combine everything
    final_content = summary + '\n'.join(all_content)
    
    # Save to llms.txt
    llms_file = tframex_path / "llms.txt"
    try:
        with open(llms_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"\n🎉 Generated {llms_file}")
        print(f"📊 {processed_files} files processed")
        print(f"📏 {total_chars:,} characters total")
        print(f"💾 Final file size: {len(final_content):,} characters")
        
        # Generate metadata for reference
        metadata = {
            "site_name": "TFrameX",
            "generated_at": datetime.now().isoformat(),
            "files_processed": processed_files,
            "total_characters": total_chars,
            "source_files": [f.name for f in txt_files],
            "llms_file_size": len(final_content),
            "source_url": "https://tframex.tesslate.com/"
        }
        
        metadata_file = tframex_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📋 Metadata saved to {metadata_file}")
        
        # Show final file size in KB
        size_kb = len(final_content.encode('utf-8')) / 1024
        print(f"📊 Final llms.txt size: {size_kb:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving llms.txt: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting TFrameX LLM content generation...")
    
    if generate_tframex_llms():
        print("\n✨ TFrameX documentation successfully processed!")
        print("📁 Ready for LLM consumption: tframex/llms.txt")
    else:
        print("\n💥 Failed to process TFrameX documentation")
