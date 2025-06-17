# generate_llms.py

import os
from pathlib import Path

def minify_text(text):
    return " ".join(text.split())

def merge_txt_files(folder_path, output_file):
    all_text = ""
    for file in sorted(Path(folder_path).glob("*.txt")):
        with open(file, "r", encoding="utf-8") as f:
            all_text += f.read() + "\n\n"
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(minify_text(all_text))

merge_txt_files("animejs/pages", "animejs/llms.txt")
