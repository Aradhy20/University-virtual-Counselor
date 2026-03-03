import sys
import os
import asyncio
import uuid

# Add project root to path
sys.path.append(os.getcwd())

from app.services.rag import RAGService

async def test_rag():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    query = "What new technologies are integrated into TMU curriculum for 2026?"
    print(f"\nQuery: {query}")
    
    # Directly search FAISS
    results = rag.vector_store.similarity_search_with_score(query, k=3)
    
    print("\n--- RESULTS ---\n")
    for doc, score in results:
        print(f"Score: {score:.4f}")
        print(f"Content: {doc.page_content}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_rag())
