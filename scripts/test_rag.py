import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.getcwd())

from app.services.rag import RAGService

async def test_rag():
    print("Initializing RAG Service...")
    rag = RAGService()
    
    query = "What is the contact number for admission?"
    print(f"\nQuery: {query}")
    
    answer = await rag.get_answer(query)
    print(f"Result: {answer}")

    if "Context found:" in answer:
        print("\n✅ RAG Index is properly built and retrieving context.")
    else:
        print("\n❌ RAG retrieval failed.")

if __name__ == "__main__":
    asyncio.run(test_rag())
