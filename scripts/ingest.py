"""
Ingestion Script — Production-grade document processing.

Phase 3 Upgrade:
  - Embedding: all-MiniLM-L6-v2 → paraphrase-multilingual-MiniLM-L12-v2
  - Chunking: Naive 400-char → Section-aware splitting
    * Small files (<500 chars): single chunk (no splitting)
    * Large files: split by section headers first, then sub-split if >600 chars
    * Section headers preserved as metadata
  - BM25 corpus saved alongside FAISS
  - Backup of old index before overwrite
"""
import os
import re
import sys
import shutil
import pickle
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from langchain_community.document_loaders import Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore, FAISS
from langchain_core.documents import Document
from supabase.client import create_client
from rank_bm25 import BM25Okapi

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Fix Windows Unicode Output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load Env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Must match rag.py
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ---------------------------------------------------------------
# Metadata Inference
# ---------------------------------------------------------------
DEPARTMENT_MAP = {
    "btech": "Engineering",
    "b.tech": "Engineering",
    "cse": "Computer Science",
    "computer science": "Computer Science",
    "ece": "Electronics",
    "mechanical": "Mechanical Engineering",
    "civil": "Civil Engineering",
    "electrical": "Electrical Engineering",
    "bca": "Computer Applications",
    "mca": "Computer Applications",
    "bba": "Management",
    "mba": "Management",
    "mbbs": "Medical",
    "md": "Medical",
    "ms": "Medical",
    "bds": "Dental",
    "mds": "Dental",
    "pharmacy": "Pharmacy",
    "pharm": "Pharmacy",
    "law": "Law",
    "llb": "Law",
    "agriculture": "Agriculture",
    "agronomy": "Agriculture",
    "nursing": "Nursing",
    "education": "Education",
    "bed": "Education",
    "bped": "Physical Education",
    "mped": "Physical Education",
    "bsc": "Science",
    "msc": "Science",
    "bcom": "Commerce",
    "mcom": "Commerce",
}

CATEGORY_MAP = {
    "fee": "fees",
    "fees": "fees",
    "placement": "placements",
    "hostel": "hostel",
    "admission": "admission",
    "eligibility": "eligibility",
    "scholarship": "scholarship",
    "campus": "campus",
    "facility": "campus",
    "contact": "contact",
}


def infer_metadata(filename: str, content: str = "") -> dict:
    """Auto-infer metadata from filename and content."""
    name_lower = filename.lower()
    metadata = {
        "source": filename,
        "category": "course",  # default
        "department": "General",
        "course_name": "",
        "topic": "general",
        "keywords": [],
    }

    # Extract course name from filename
    course_name = Path(filename).stem
    course_name = re.sub(r'\(.*?\)', '', course_name).strip()
    metadata["course_name"] = course_name

    # Detect department
    for key, dept in DEPARTMENT_MAP.items():
        if key in name_lower:
            metadata["department"] = dept
            break

    # Detect category from filename
    for key, cat in CATEGORY_MAP.items():
        if key in name_lower:
            metadata["category"] = cat
            break

    # Detect category from content
    if not metadata["category"] or metadata["category"] == "course":
        content_lower = content[:500].lower() if content else ""
        for key, cat in CATEGORY_MAP.items():
            if key in content_lower:
                metadata["topic"] = cat
                break

    # Extract keywords from filename
    keywords = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z]|$)|[a-z]+', course_name)
    metadata["keywords"] = [kw.lower() for kw in keywords if len(kw) > 2]

    # Website content detection
    if filename.endswith(".txt") and any(w in name_lower for w in ["tmu", "home", "contact", "why"]):
        metadata["category"] = "website"
        metadata["department"] = "General"

    return metadata


# ---------------------------------------------------------------
# Section-Aware Chunking
# ---------------------------------------------------------------

# Patterns that indicate section headers
HEADER_PATTERNS = [
    r'^#{1,4}\s+.+',              # Markdown headers: # Title, ## Section
    r'^[A-Z][A-Z\s\-&]{4,}$',     # ALL CAPS LINES (>4 chars)
    r'^[\d]+\.\s+[A-Z].+',        # Numbered sections: 1. Title
    r'^={3,}$',                    # === dividers
    r'^-{3,}$',                    # --- dividers
    r'^\*{3,}$',                   # *** dividers
    r'^[A-Z][a-zA-Z\s]+:$',       # Label lines ending in colon: "Eligibility:"
]

HEADER_REGEX = re.compile('|'.join(HEADER_PATTERNS), re.MULTILINE)


def section_aware_split(doc: Document, max_chunk: int = 500, overlap: int = 50) -> list[Document]:
    """
    Section-aware document splitter:
    1. Small docs (<500 chars) → single chunk
    2. Split by section headers → each section is a candidate chunk
    3. Sections >max_chunk → sub-split with RecursiveCharacterTextSplitter
    4. Section header preserved in metadata as 'chunk_header'
    """
    content = doc.page_content.strip()

    # Rule 1: Small documents stay as single chunk
    if len(content) < 500:
        return [doc]

    # Rule 2: Split by section headers
    sections = _split_by_headers(content)

    # Sub-splitter for oversized sections
    sub_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_chunk,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", ", ", " "],
    )

    chunks = []
    for header, section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue

        if len(section_text) <= max_chunk:
            # Section fits in one chunk
            chunk_doc = Document(
                page_content=section_text,
                metadata={**doc.metadata, "chunk_header": header}
            )
            chunks.append(chunk_doc)
        else:
            # Sub-split large sections
            sub_docs = sub_splitter.create_documents(
                [section_text],
                metadatas=[{**doc.metadata, "chunk_header": header}]
            )
            chunks.extend(sub_docs)

    # Fallback: if no sections found, use basic splitter
    if not chunks:
        fallback = sub_splitter.split_documents([doc])
        return fallback

    return chunks


def _split_by_headers(text: str) -> list[tuple[str, str]]:
    """
    Split text into (header, content) pairs by detecting section headers.
    Returns list of (header_text, section_content) tuples.
    """
    lines = text.split('\n')
    sections = []
    current_header = ""
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and HEADER_REGEX.match(stripped):
            # Save previous section
            if current_lines:
                section_text = '\n'.join(current_lines)
                if section_text.strip():
                    sections.append((current_header, section_text))
            current_header = stripped
            current_lines = [line]  # Include header in content for context
        else:
            current_lines.append(line)

    # Don't forget the last section
    if current_lines:
        section_text = '\n'.join(current_lines)
        if section_text.strip():
            sections.append((current_header, section_text))

    # If we found no headers (plain text), return entire text as one section
    if len(sections) <= 1:
        return [("", text)]

    return sections


# ---------------------------------------------------------------
# Main Ingestion
# ---------------------------------------------------------------
def ingest_data(source_dirs: list[str]):
    print("=" * 60)
    print("  ADITI RAG — PHASE 3 INGESTION (Section-Aware)")
    print(f"  Embedding: {EMBEDDING_MODEL}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    docs = []

    for source_dir in source_dirs:
        print(f"\n[SCAN] Directory: {source_dir}")
        source_path = Path(source_dir)

        if not source_path.exists():
            print(f"  [WARN] Directory not found, skipping.")
            continue

        # Load .docx files
        for file_path in source_path.rglob("*.docx"):
            if file_path.name.startswith("~$"):
                continue
            try:
                loader = Docx2txtLoader(str(file_path))
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    meta = infer_metadata(file_path.name, doc.page_content)
                    doc.metadata.update(meta)
                docs.extend(loaded_docs)
                print(f"  [OK] {file_path.name} → {loaded_docs[0].metadata.get('department', '?')}")
            except Exception as e:
                print(f"  [WARN] Failed: {file_path.name}: {e}")

        # Load .txt files
        for file_path in source_path.rglob("*.txt"):
            try:
                loader = TextLoader(str(file_path), encoding="utf-8")
                loaded_docs = loader.load()
                for doc in loaded_docs:
                    meta = infer_metadata(file_path.name, doc.page_content)
                    doc.metadata.update(meta)
                docs.extend(loaded_docs)
                print(f"  [OK] {file_path.name} → {loaded_docs[0].metadata.get('department', '?')}")
            except Exception as e:
                print(f"  [WARN] Failed: {file_path.name}: {e}")

    print(f"\n[INFO] Loaded {len(docs)} documents total.")

    if not docs:
        print("[ERROR] No documents found. Exiting.")
        return

    # ---- Section-Aware Chunking ----
    print("\n[CHUNK] Section-aware splitting...")
    splits = []
    small_count = 0
    section_count = 0

    for doc in docs:
        doc_chunks = section_aware_split(doc, max_chunk=500, overlap=50)
        if len(doc_chunks) == 1 and len(doc.page_content) < 500:
            small_count += 1
        else:
            section_count += 1
        splits.extend(doc_chunks)

    # Propagate metadata
    for split in splits:
        if "source" not in split.metadata:
            split.metadata["source"] = "unknown"

    avg_chars = sum(len(s.page_content) for s in splits) // max(len(splits), 1)
    print(f"[CHUNK] Created {len(splits)} chunks (avg {avg_chars} chars)")
    print(f"  - {small_count} docs kept as single chunk (<500 chars)")
    print(f"  - {section_count} docs section-split")

    # ---- Embeddings ----
    print(f"\n[EMBED] Generating embeddings ({EMBEDDING_MODEL})...")
    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    except Exception as e:
        print(f"[ERROR] Embeddings failed: {e}")
        return

    # ---- Save FAISS Index ----
    _save_faiss(splits, embeddings)

    # ---- Save BM25 Index ----
    _save_bm25(splits)

    # ---- Optional: Supabase Backup ----
    if SUPABASE_URL and SUPABASE_KEY:
        print("\n[CLOUD] Uploading to Supabase (backup)...")
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            SupabaseVectorStore.from_documents(
                splits, embeddings,
                client=supabase,
                table_name="documents",
                query_name="match_documents"
            )
            print("[OK] Supabase ingestion complete!")
        except Exception as e:
            print(f"[WARN] Supabase upload failed: {e}")

    print("\n" + "=" * 60)
    print("  INGESTION COMPLETE!")
    print(f"  Documents: {len(docs)} | Chunks: {len(splits)}")
    print(f"  Embedding: {EMBEDDING_MODEL}")
    print(f"  Chunking: section-aware (max 500 chars)")
    print("=" * 60)


def _save_faiss(splits, embeddings):
    """Save FAISS index with backup."""
    index_path = Path(__file__).parent.parent / "app" / "data" / "faiss_index"

    # Backup old index
    if index_path.exists():
        backup_path = str(index_path) + f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copytree(str(index_path), backup_path)
        print(f"[BACKUP] Old FAISS index backed up to: {backup_path}")

    if not index_path.parent.exists():
        index_path.parent.mkdir(parents=True)

    try:
        vector_db = FAISS.from_documents(splits, embeddings)
        vector_db.save_local(str(index_path))
        print(f"[OK] FAISS index saved: {index_path} ({vector_db.index.ntotal} vectors)")
    except Exception as e:
        print(f"[ERROR] FAISS save failed: {e}")


def _save_bm25(splits):
    """Build and save BM25 index for keyword search."""
    bm25_path = Path(__file__).parent.parent / "app" / "data" / "bm25_index.pkl"

    try:
        # Tokenize documents for BM25
        corpus = [doc.page_content.lower().split() for doc in splits]
        bm25 = BM25Okapi(corpus)

        # Save BM25 index + original docs
        with open(str(bm25_path), "wb") as f:
            pickle.dump({
                "bm25": bm25,
                "docs": splits,  # Keep original Document objects for metadata
            }, f)
        print(f"[OK] BM25 index saved: {bm25_path} ({len(splits)} documents)")
    except Exception as e:
        print(f"[ERROR] BM25 save failed: {e}")


# ---------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------
if __name__ == "__main__":
    DIRS = [
        r"c:\tmu\university_counselor\data\migrated_docs",
        r"c:\tmu\university_counselor\data\website_content",
        r"c:\tmu\university_counselor\university details",
    ]
    
    # Also add standalone FAQ files
    EXTRA_FILES = [
        r"c:\tmu\university_counselor\data\aditi_faqs.txt",
    ]

    ingest_data(DIRS)
