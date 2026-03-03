
import json
import collections

VECTOR_FILE = r"d:\tmu\university_counselor\university details\vectors.json"

def analyze_vectors():
    try:
        with open(VECTOR_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Total items: {len(data)}")
        
        texts = [item.get('text', '') for item in data]
        ids = [item.get('id', '') for item in data]
        
        text_counts = collections.Counter(texts)
        id_counts = collections.Counter(ids)
        
        duplicate_texts = {k: v for k, v in text_counts.items() if v > 1}
        duplicate_ids = {k: v for k, v in id_counts.items() if v > 1}
        
        print(f"Duplicate Texts Found: {len(duplicate_texts)}")
        if duplicate_texts:
            print("Top 5 duplicate texts:")
            for text, count in list(duplicate_texts.items())[:5]:
                print(f"  {count}x: {text[:100]}...")
                
        print(f"Duplicate IDs Found: {len(duplicate_ids)}")
        if duplicate_ids:
            print("Top 5 duplicate IDs:")
            for id_, count in list(duplicate_ids.items())[:5]:
                print(f"  {count}x: {id_}")

    except Exception as e:
        print(f"Error reading {VECTOR_FILE}: {e}")

if __name__ == "__main__":
    analyze_vectors()
