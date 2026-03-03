import sys
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def check_vector_db():
    print("--- Verifying Vector Database ---")
    index_path = Path(__file__).parent.parent / "data" / "faiss_index"
    
    if not index_path.exists():
        print(f"[ERROR] Index path does not exist: {index_path}")
        return

    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_db = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
        
        # Check Document Count
        print(f"[SUCCESS] Vector DB loaded.")
        print(f"Index Document Count: {vector_db.index.ntotal}")

        # Test Search
        query = "What is the fee for BTech CSE?"
        docs = vector_db.similarity_search(query, k=3)
        print(f"\n[TEST SEARCH] Query: '{query}'")
        for i, doc in enumerate(docs):
            print(f"  {i+1}. Source: {doc.metadata.get('source', 'Unknown')} | Content: {doc.page_content[:100]}...")
            
    except Exception as e:
        print(f"[ERROR] Failed to load/query vector DB: {e}")

if __name__ == "__main__":
    check_vector_db()
