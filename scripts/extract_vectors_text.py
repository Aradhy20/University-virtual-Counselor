
import json
import os

def extract_text():
    source_file = r"d:\tmu\university_counselor\university details\vectors.json"
    target_file = r"d:\tmu\university_counselor\data\university_vectors_content.txt"
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = 0
        with open(target_file, "w", encoding="utf-8") as f:
            for item in data:
                if "text" in item:
                    f.write(item["text"] + "\n\n")
                    count += 1
        
        print(f"Successfully extracted {count} items to {target_file}")
        
    except Exception as e:
        print(f"Failed to extract: {e}")

if __name__ == "__main__":
    extract_text()
