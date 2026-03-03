"""
Robust Retrieval Accuracy Test — Phase 5 (No LLM dependency)

Bypasses the full RAGService to avoid langchain version conflicts with ChatGroq.
Directly loads FAISS index and Embedding model to test retrieval quality.
"""
import sys
import os
import time
import json
import logging

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Fix Windows Unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Configuration
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FAISS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "data", "faiss_index")
GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "golden_dataset.json")

def load_golden_dataset():
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["queries"]

def main():
    print("🔬" * 30)
    print("   ROBUST RETRIEVAL ACCURACY TEST (Direct FAISS)")
    print("🔬" * 30)

    # 1. Load Embedding Model
    print(f"\n[1/3] Loading embedding model: {EMBEDDING_MODEL}...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        print("  ✅ Model loaded.")
    except Exception as e:
        print(f"  ❌ Failed to load model: {e}")
        return

    # 2. Load FAISS Index
    print(f"\n[2/3] Loading FAISS index from {FAISS_PATH}...")
    try:
        vector_store = FAISS.load_local(
            FAISS_PATH, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        print("  ✅ FAISS index loaded.")
    except Exception as e:
        print(f"  ❌ Failed to load FAISS index: {e}")
        return

    # 3. Load Dataset
    queries = load_golden_dataset()
    print(f"\n[3/3] Running {len(queries)} queries...")

    hits = 0
    total = len(queries)
    results_log = []

    start_time = time.time()

    for i, q in enumerate(queries):
        query_text = q["query"]
        expected_kws = [k.lower() for k in q["expected_keywords"]]
        
        # Search
        try:
            # Get top 3
            docs = vector_store.similarity_search(query_text, k=3)
            
            # Check for matches
            hit = False
            matched = []
            for doc in docs:
                content = doc.page_content.lower()
                found = [k for k in expected_kws if k in content]
                if found:
                    hit = True
                    matched.extend(found)
            
            if hit:
                hits += 1
                status = "✅"
            else:
                status = "❌"
            
            print(f"  {status} Q{q['id']:02d}: {query_text[:40]:<40} -> {list(set(matched))[:3]}")
            
            results_log.append({
                "id": q["id"],
                "query": query_text,
                "hit": hit,
                "matched": list(set(matched))
            })

        except Exception as e:
            print(f"  ⚠️ Error on Q{q['id']}: {e}")

    elapsed = time.time() - start_time
    hit_rate = (hits / total) * 100

    print("\n" + "=" * 60)
    print(f"RESULTS: {hits}/{total} Hits ({hit_rate:.1f}%)")
    print(f"Time: {elapsed:.2f}s")
    print("=" * 60)

    # Save minimal report
    with open("data/robust_accuracy_report.json", "w", encoding="utf-8") as f:
        json.dump({"hit_rate": hit_rate, "details": results_log}, f, indent=2)

if __name__ == "__main__":
    main()
