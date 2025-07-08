source_file = "pages/anime_migration_v3_to_v4.txt"
destination_file = "llm.txt"

# Read the new content
with open(source_file, "r", encoding="utf-8") as src:
    new_content = src.read().strip()

# Append to llm.txt with a separator for clarity
with open(destination_file, "a", encoding="utf-8") as dest:
    dest.write("\n\n--- anime_migration_v3_to_v4 ---\n\n")
    dest.write(new_content)
    dest.write("\n")  # Optional: ensure trailing newline

print("Content appended to llm.txt successfully.")
