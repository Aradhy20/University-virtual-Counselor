import sys
from pathlib import Path
import asyncio

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService

async def main():
    print("[TEST] Initializing RAG Service...")
    try:
        rag = RAGService()
    except Exception as e:
        print(f"[ERROR] Failed to init RAG Service: {e}")
        return

    if not rag.vector_store:
        print("[ERROR] Vector Store not initialized via RAGService.")
        return

    query = "What is the fee structure for B.Tech CSE?"
    print(f"\n[TEST] Testing Retrieval for query: '{query}'")
    
    try:
        # Test pure retrieval
        docs = rag.vector_store.similarity_search(query, k=3)
        print(f"[SUCCESS] Retrieved {len(docs)} documents.")
        for i, doc in enumerate(docs):
            print(f"\n--- Document {i+1} ---")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Content Preview: {doc.page_content[:200]}...")
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
