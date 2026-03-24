"""
Native RAG Service — Pure FAISS and SentenceTransformers.
Zero framework dependencies (No LangChain, No LlamaIndex).
"""
import os
import pickle
import logging
from pathlib import Path
from typing import List, Tuple, Dict
from dotenv import load_dotenv

try:
    import faiss
except ImportError:
    faiss = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
except ImportError:
    SentenceTransformer = None
    CrossEncoder = None

load_dotenv()
logger = logging.getLogger("riya.rag_native")

class RAGServiceNative:
    """
    Ultra-fast native FAISS retrieval service.
    Loads knowledge_base.txt, chunks it, and builds a flat L2 FAISS index.
    """
    def __init__(self, data_dir: str = "data", persist_dir: str = "data/faiss_index"):
        # Paths
        project_root = Path(__file__).parent.parent.parent
        self.data_path = project_root / data_dir / "knowledge_base.txt"
        self.persist_dir = project_root / persist_dir
        self.index_path = self.persist_dir / "index.faiss"
        self.metadata_path = self.persist_dir / "metadata.pkl"

        # Models
        self.embed_model_name = "paraphrase-multilingual-MiniLM-L12-v2" # Fast 384d bilingual model
        self.reranker_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self.encoder = None
        self.reranker = None
        self.index = None
        self.documents = []  # List of chunk strings

        self._initialize()

    def _initialize(self):
        """Loads FAISS index from disk or builds it if absent."""
        if SentenceTransformer is None or np is None or faiss is None:
            logger.warning("Native RAG dependencies missing. Falling back to keyword-only retrieval.")
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                self.documents = [c.strip() for c in raw_text.split('\n\n') if len(c.strip()) > 20]
            else:
                self.documents = ["TMU is Teerthanker Mahaveer University in Moradabad, Uttar Pradesh."]
            return

        try:
            logger.info(f"Loading native encoder: {self.embed_model_name}")
            self.encoder = SentenceTransformer(self.embed_model_name)
        except Exception as exc:
            logger.warning(f"Encoder load failed: {exc}. Falling back to keyword-only retrieval.")
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    raw_text = f.read()
                self.documents = [c.strip() for c in raw_text.split('\n\n') if len(c.strip()) > 20]
            else:
                self.documents = ["TMU is Teerthanker Mahaveer University in Moradabad, Uttar Pradesh."]
            self.encoder = None
            return

        if self.index_path.exists() and self.metadata_path.exists():
            logger.info("Loading existing FAISS index from disk.")
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'rb') as f:
                self.documents = pickle.load(f)
        else:
            logger.info("Building new native FAISS index...")
            self._build_index()

    def _build_index(self):
        """Reads knowledge base, chunks it, embeds it, and saves to FAISS."""
        # Ensure persistence directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        if not self.data_path.exists():
            logger.error(f"Knowledge base not found at: {self.data_path}")
            self.documents = ["Backup Knowledge: TMU is Teerthanker Mahaveer University in Moradabad."]
        else:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            
            # Simple chunking by double newlines or large paragraphs
            # For simplicity, split by double newline first
            raw_chunks = [c.strip() for c in raw_text.split('\n\n') if len(c.strip()) > 20]
            
            # Sub-chunk very large blocks (naive max length ~1000 chars)
            final_chunks = []
            for chunk in raw_chunks:
                if len(chunk) > 1200:
                    sentences = chunk.split('. ')
                    current_sub = ""
                    for sentence in sentences:
                        if len(current_sub) + len(sentence) < 1200:
                            current_sub += sentence + ". "
                        else:
                            final_chunks.append(current_sub.strip())
                            current_sub = sentence + ". "
                    if current_sub:
                        final_chunks.append(current_sub.strip())
                else:
                    final_chunks.append(chunk)
            
            self.documents = final_chunks

        # Embed all chunks
        logger.info(f"Embedding {len(self.documents)} chunks...")
        embeddings = self.encoder.encode(self.documents, convert_to_numpy=True)
        
        # Build FAISS Flat L2 Index
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

        # Save to disk
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.documents, f)
        logger.info(f"FAISS index built and saved with {len(self.documents)} chunks.")

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """Performs L2 vector search in FAISS."""
        if self.encoder is None or self.index is None:
            return self._keyword_fallback(query, top_k=top_k)

        if not self.documents:
            return []
            
        query_emb = self.encoder.encode([query], convert_to_numpy=True)
        distances, indices = self.index.search(query_emb, top_k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.documents):
                results.append(self.documents[idx])
        return results

    def _keyword_fallback(self, query: str, top_k: int = 5) -> List[str]:
        """Simple lexical fallback when FAISS or transformer dependencies are unavailable."""
        if not self.documents:
            return []

        query_terms = {term for term in query.lower().split() if term}
        scored = []
        for doc in self.documents:
            overlap = len(query_terms.intersection(doc.lower().split()))
            if overlap:
                scored.append((overlap, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        if scored:
            return [doc for _, doc in scored[:top_k]]
        return self.documents[:top_k]

    def _get_reranker(self):
        """Lazy loads the cross-encoder."""
        if self.reranker is None:
            if CrossEncoder is None:
                logger.warning("Cross-encoder dependency missing. Re-ranking disabled.")
                return None
            logger.info(f"Loading cross-encoder: {self.reranker_model_name}")
            self.reranker = CrossEncoder(self.reranker_model_name, max_length=512)
        return self.reranker

    def rerank_and_score(self, query: str, docs: List[str], top_k: int = 3) -> Tuple[List[str], float]:
        """Reranks FAISS candidates and computes a confidence score."""
        if not docs:
            return [], 0.0
            
        reranker = self._get_reranker()
        if reranker is None or np is None:
            return docs[:top_k], 0.5
        pairs = [[query, doc] for doc in docs]
        scores = reranker.predict(pairs)
        
        # Map raw logits (-10 to 10) to pseudo-probabilities (0 to 1) via sigmoid
        confidences = 1 / (1 + np.exp(-scores))
        
        # Sort by score descending
        scored_docs = list(zip(docs, confidences))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        best_confidence = float(scored_docs[0][1])
        final_docs = [doc for doc, _ in scored_docs[:top_k]]
        
        return final_docs, best_confidence
