"""
Script to ingest the TMU comprehensive knowledge base into the FAISS vector store.
Run this script ONCE to add all new data to the index.

Usage:
  cd c:\\tmu\\university_counselor
  python scripts/ingest_tmu_knowledge.py
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ingestion")

from dotenv import load_dotenv
load_dotenv()

# Load the knowledge files
KNOWLEDGE_FILES = [
    project_root / "data" / "tmu_comprehensive_knowledge.txt",
    project_root / "data" / "tmu_2026_brochure_updates_and_nlp.txt",
    project_root / "data" / "aditi_faqs.txt",
]

# Migrated docs directory
MIGRATED_DOCS_DIR = project_root / "data" / "migrated_docs"


def load_text_file(path: Path) -> list[dict]:
    """Load a text file and split into chunks."""
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return []
    
    text = path.read_text(encoding="utf-8")
    
    # Split by double newlines or section markers
    chunks = []
    current_chunk = []
    
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if current_chunk:
                chunk_text = " ".join(current_chunk).strip()
                if len(chunk_text) > 50:  # Only keep meaningful chunks
                    chunks.append({
                        "content": chunk_text,
                        "source": path.name
                    })
                current_chunk = []
        else:
            current_chunk.append(line)
    
    # Last chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk).strip()
        if len(chunk_text) > 50:
            chunks.append({
                "content": chunk_text,
                "source": path.name
            })
    
    logger.info(f"Loaded {len(chunks)} chunks from {path.name}")
    return chunks


def load_migrated_docs() -> list[dict]:
    """Load all migrated docs from the data directory."""
    chunks = []
    if not MIGRATED_DOCS_DIR.exists():
        return chunks
    
    for file_path in MIGRATED_DOCS_DIR.glob("*.txt"):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(text.strip()) > 100:
                # Split into smaller chunks if needed
                parts = text.split("\n\n")
                for part in parts:
                    part = part.strip()
                    if len(part) > 100:
                        chunks.append({
                            "content": part,
                            "source": file_path.name
                        })
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
    
    logger.info(f"Loaded {len(chunks)} chunks from migrated_docs/")
    return chunks


def main():
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
    except ImportError:
        logger.error("Required packages not available. Run: pip install langchain-community sentence-transformers faiss-cpu")
        sys.exit(1)
    
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    FAISS_INDEX_PATH = str(project_root / "app" / "data" / "faiss_index")
    
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    # Collect all chunks
    all_chunks = []
    
    for file_path in KNOWLEDGE_FILES:
        chunks = load_text_file(file_path)
        all_chunks.extend(chunks)
    
    migrated_chunks = load_migrated_docs()
    all_chunks.extend(migrated_chunks)
    
    if not all_chunks:
        logger.error("No chunks loaded! Check knowledge file paths.")
        sys.exit(1)
    
    logger.info(f"Total chunks to ingest: {len(all_chunks)}")
    
    # Convert to LangChain Documents
    documents = [
        Document(
            page_content=chunk["content"],
            metadata={"source": chunk["source"]}
        )
        for chunk in all_chunks
    ]
    
    # Load existing index or create new
    if os.path.exists(FAISS_INDEX_PATH):
        logger.info(f"Loading existing FAISS index from: {FAISS_INDEX_PATH}")
        try:
            existing_vs = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            logger.info(f"Existing index has {existing_vs.index.ntotal} vectors")
            
            # Add new documents to existing index
            existing_vs.add_documents(documents)
            logger.info(f"Added {len(documents)} new vectors. Total: {existing_vs.index.ntotal}")
            existing_vs.save_local(FAISS_INDEX_PATH)
        except Exception as e:
            logger.warning(f"Existing index load failed ({e}). Creating new index.")
            vs = FAISS.from_documents(documents, embeddings)
            vs.save_local(FAISS_INDEX_PATH)
            logger.info(f"New FAISS index saved with {vs.index.ntotal} vectors")
    else:
        logger.info("Creating new FAISS index...")
        os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
        vs = FAISS.from_documents(documents, embeddings)
        vs.save_local(FAISS_INDEX_PATH)
        logger.info(f"New FAISS index saved at: {FAISS_INDEX_PATH}")
        logger.info(f"Total vectors: {vs.index.ntotal}")
    
    # Also rebuild BM25 index
    try:
        from rank_bm25 import BM25Okapi
        import pickle
        
        bm25_path = str(project_root / "app" / "data" / "bm25_index.pkl")
        tokenized_corpus = [doc.page_content.lower().split() for doc in documents]
        bm25 = BM25Okapi(tokenized_corpus)
        
        with open(bm25_path, "wb") as f:
            pickle.dump({"bm25": bm25, "docs": documents}, f)
        logger.info(f"BM25 index rebuilt with {len(documents)} documents at: {bm25_path}")
    except Exception as e:
        logger.warning(f"BM25 index rebuild failed: {e}")
    
    logger.info("✅ Knowledge ingestion complete! Restart the server to load the new index.")


if __name__ == "__main__":
    main()
