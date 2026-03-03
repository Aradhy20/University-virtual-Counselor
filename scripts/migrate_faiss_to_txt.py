
import os
import sys
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Add parent dir
sys.path.insert(0, ".")

def migrate():
    print("Loading FAISS index...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    try:
        vs = FAISS.load_local(r"d:\tmu\university_counselor\app\data\faiss_index", embeddings, allow_dangerous_deserialization=True)
        print(f"Index loaded. Count: {vs.index.ntotal}")
        
        # Access docstore
        docstore = vs.docstore
        print(f"Docstore keys: {len(docstore._dict)}")
        
        output_dir = r"d:\tmu\university_counselor\data\migrated_docs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"Exporting to {output_dir}...")
        
        count = 0
        for key, doc in docstore._dict.items():
            source = doc.metadata.get("source", "unknown")
            # Clean filename
            safe_name = "".join([c for c in os.path.basename(source) if c.isalnum() or c in (' ', '.', '_')]).strip()
            if not safe_name:
                safe_name = f"doc_{count}.txt"
            if not safe_name.endswith(".txt"):
                safe_name += ".txt"
                
            content = doc.page_content
            
            # Append to file (consolidate chunks by source)
            with open(os.path.join(output_dir, safe_name), "a", encoding="utf-8") as f:
                f.write(content + "\n\n")
            
            count += 1
            
        print(f"Exported {count} chunks.")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
