
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag import RAGService

load_dotenv(r"d:\tmu\university_counselor\.env")

async def test_rag():
    print("--- Testing RAG Service ---")
    try:
        rag = RAGService()
        print(f"[OK] Service Initialized. Index Size: {rag.vector_store.index.ntotal if rag.vector_store else 'None'}")
        
        query = "What is the fee for B.Tech CSE?"
        print(f"\nQuery: {query}")
        
        # Test Search directly
        docs = rag.hybrid_search(query, top_k=2)
        if docs:
            print(f"[OK] Found {len(docs)} docs.")
            for i, d in enumerate(docs):
                print(f"[{i+1}] {d.page_content[:100]}...")
                print(f"     Source: {d.metadata.get('source', 'unknown')}")
        else:
            print("[FAIL] No docs found.")
            
    except Exception as e:
        print(f"[ERROR] RAG Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag())
