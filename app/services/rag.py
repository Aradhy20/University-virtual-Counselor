"""
RAG Service — Production-grade retrieval with:
  - FAISS vector search (semantic) with multilingual embeddings
  - BM25 keyword search (exact match)
  - Reciprocal Rank Fusion (RRF) to merge results
  - Cross-encoder re-ranking for semantic verification
  - Score thresholding (filters low-quality chunks)
  - Metadata filtering support
  - Dual-query support for Hinglish normalization

Phase 3 Upgrade:
  - Embedding: all-MiniLM-L6-v2 → paraphrase-multilingual-MiniLM-L12-v2
  - Added cross-encoder re-ranker (ms-marco-MiniLM-L-6-v2)
  - TOP_K: 2 → 3, FAISS_FETCH_K: 5 → 10
  - Real confidence scoring from re-ranker output
"""
import os
import pickle
import logging
from typing import Optional
from dotenv import load_dotenv
from urllib.parse import urlparse
from llama_index.llms.groq import Groq
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None
try:
    from langchain_community.vectorstores import SupabaseVectorStore, FAISS
except ImportError:
    SupabaseVectorStore = None
    FAISS = None
from langchain_core.documents import Document
from supabase.client import create_client, Client
from app.services.config_loader import config_loader


load_dotenv()

logger = logging.getLogger("aditi.rag")

# ----------------------------------------------------------
# Configuration
# ----------------------------------------------------------
# Embedding model — multilingual for Hindi/Hinglish/English
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Score threshold for FAISS (lower = more similar for L2 distance)
FAISS_SCORE_THRESHOLD = 2.0
# Number of results to fetch before filtering/re-ranking
FAISS_FETCH_K = 10
# Final number of chunks to return after re-ranking
TOP_K = 3

# Cross-encoder re-ranker config
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_THRESHOLD = 0.3  # Min re-ranker score to keep a result (range ~-10 to +10)
RERANK_TOP_K = 10  # How many candidates to pass to re-ranker


class RAGService:
    def __init__(self):
        config = config_loader.get_config()
        self.groq_api_key = config.api.groq_api_key or os.getenv("GROQ_API_KEY")
        self.supabase_url = config.api.supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = config.api.supabase_service_key or os.getenv("SUPABASE_SERVICE_KEY")


        # Local Embeddings (multilingual)
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        if HuggingFaceEmbeddings:
            self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        else:
            logger.warning("HuggingFaceEmbeddings not available. RAG disabled.")
            self.embeddings = None

        # LLM for Generation - Using LlamaIndex Groq!
        if not self.groq_api_key:
            logger.warning("GROQ_API_KEY is missing. Agent will fail to generate answers.")

        self.llm = Groq(
            model=config_loader.get_config().llm.model_name or "llama-3.3-70b-versatile",
            temperature=config_loader.get_config().llm.temperature or 0.25,
            api_key=self.groq_api_key
        )

        self.vector_store = self._initialize_vector_store()
        self.bm25_index = None
        self.bm25_docs = []
        self._load_bm25_index()

        # Cross-encoder re-ranker (lazy loaded)
        self._reranker = None

    # ----------------------------------------------------------
    # Cross-Encoder Re-Ranker
    # ----------------------------------------------------------
    def _get_reranker(self):
        """Lazy-load cross-encoder re-ranker on first use."""
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading cross-encoder re-ranker: {RERANKER_MODEL}")
                self._reranker = CrossEncoder(RERANKER_MODEL)
                logger.info("Cross-encoder re-ranker loaded successfully")
            except Exception as e:
                logger.warning(f"Cross-encoder load failed: {e}. Re-ranking disabled.")
                self._reranker = False  # Sentinel: tried and failed
        return self._reranker if self._reranker is not False else None

    # ----------------------------------------------------------
    # Vector Store Initialization
    # ----------------------------------------------------------
    def _initialize_vector_store(self):
        """Load FAISS (primary) with Supabase fallback."""
        if not self.embeddings:
            return None

        try:
            if FAISS:
                from pathlib import Path as _Path
                _project_root = _Path(__file__).parent.parent.parent
                index_path = str(_project_root / "app" / "data" / "faiss_index")
            if os.path.exists(index_path):
                vs = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
                doc_count = vs.index.ntotal if hasattr(vs, 'index') else "unknown"
                logger.info(f"FAISS index loaded: {doc_count} vectors")
                return vs
        except Exception as e:
            logger.warning(f"FAISS init failed: {e}")

        if self.supabase_url and self.supabase_key and SupabaseVectorStore:
            try:
                supabase: Client = create_client(self.supabase_url, self.supabase_key)
                return SupabaseVectorStore(
                    client=supabase,
                    embedding=self.embeddings,
                    table_name="documents",
                    query_name="match_documents"
                )
            except Exception as e:
                logger.warning(f"Supabase init failed: {e}")

        return None

    # ----------------------------------------------------------
    # BM25 Index Loading
    # ----------------------------------------------------------
    def _load_bm25_index(self):
        """Load pre-built BM25 index for keyword search."""
        from pathlib import Path as _Path
        _project_root = _Path(__file__).parent.parent.parent
        bm25_path = str(_project_root / "app" / "data" / "bm25_index.pkl")
        try:
            if os.path.exists(bm25_path):
                with open(bm25_path, "rb") as f:
                    data = pickle.load(f)
                self.bm25_index = data["bm25"]
                self.bm25_docs = data["docs"]
                logger.info(f"BM25 index loaded: {len(self.bm25_docs)} documents")
            else:
                logger.warning("BM25 index not found. Keyword search disabled.")
        except Exception as e:
            logger.warning(f"BM25 load failed: {e}")

    # ----------------------------------------------------------
    # Core Search Methods
    # ----------------------------------------------------------
    def vector_search(self, query: str, k: int = FAISS_FETCH_K,
                      score_threshold: float = FAISS_SCORE_THRESHOLD) -> list[Document]:
        """FAISS vector search with score thresholding."""
        if not self.vector_store:
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            # Filter by score threshold (lower = better for L2)
            filtered = [(doc, score) for doc, score in results if score < score_threshold]

            if filtered:
                logger.info(f"Vector search: {len(filtered)}/{len(results)} passed threshold "
                           f"(best={filtered[0][1]:.3f}, worst={filtered[-1][1]:.3f})")
            else:
                logger.warning(f"Vector search: all {len(results)} results below threshold")

            return [doc for doc, _ in filtered]
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def keyword_search(self, query: str, k: int = FAISS_FETCH_K) -> list[Document]:
        """BM25 keyword search — finds exact matches that vector search might miss."""
        if not self.bm25_index or not self.bm25_docs:
            return []

        try:
            tokenized_query = query.lower().split()
            scores = self.bm25_index.get_scores(tokenized_query)

            # Get top k indices by score
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
            # Filter out zero-score results
            results = [self.bm25_docs[i] for i in top_indices if scores[i] > 0]

            logger.info(f"BM25 search: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"BM25 search error: {e}")
            return []

    def hybrid_search(self, query: str, top_k: int = TOP_K) -> list[Document]:
        """
        Hybrid search: FAISS (semantic) + BM25 (keyword).
        Merges results using Reciprocal Rank Fusion (RRF).
        """
        vector_results = self.vector_search(query)
        keyword_results = self.keyword_search(query)

        if not vector_results and not keyword_results:
            return []

        # If BM25 isn't available, fall back to vector-only
        if not keyword_results:
            return vector_results[:top_k]

        # Reciprocal Rank Fusion
        merged = self._reciprocal_rank_fusion(
            [vector_results, keyword_results],
            k=60  # RRF constant
        )

        final = merged[:top_k]
        logger.info(f"Hybrid search: {len(final)} results after RRF merge")
        return final

    def hybrid_search_with_rerank(self, query: str, top_k: int = TOP_K) -> list[tuple[Document, float]]:
        """
        Enhanced hybrid search with cross-encoder re-ranking.
        Returns list of (Document, confidence_score) tuples.
        
        Pipeline:
          1. FAISS + BM25 → RRF merge (up to RERANK_TOP_K candidates)
          2. Cross-encoder re-ranks candidates by semantic relevance
          3. Filter by RERANK_THRESHOLD, return top_k
        """
        # Step 1: Get RRF-merged candidates (more than final top_k)
        vector_results = self.vector_search(query)
        keyword_results = self.keyword_search(query)

        if not vector_results and not keyword_results:
            return []

        # Merge all candidates
        all_results = vector_results + keyword_results
        if keyword_results and vector_results:
            merged = self._reciprocal_rank_fusion(
                [vector_results, keyword_results], k=60
            )
        else:
            merged = all_results

        candidates = merged[:RERANK_TOP_K]

        if not candidates:
            return []

        # Step 2: Cross-encoder re-ranking
        reranker = self._get_reranker()
        if reranker:
            try:
                pairs = [(query, doc.page_content) for doc in candidates]
                scores = reranker.predict(pairs)

                # Pair docs with scores and sort descending
                scored = list(zip(candidates, scores.tolist()))
                scored.sort(key=lambda x: x[1], reverse=True)

                # Filter by threshold
                filtered = [(doc, score) for doc, score in scored if score >= RERANK_THRESHOLD]

                if filtered:
                    result = filtered[:top_k]
                    logger.info(f"Re-ranked: {len(result)} results "
                               f"(best={result[0][1]:.3f}, worst={result[-1][1]:.3f})")
                    return result
                else:
                    # All below threshold — return best candidate with low score
                    logger.warning(f"Re-ranker: all {len(scored)} below threshold {RERANK_THRESHOLD}. "
                                   f"Best score: {scored[0][1]:.3f}")
                    return [(scored[0][0], scored[0][1])] if scored else []

            except Exception as e:
                logger.error(f"Re-ranking error: {e}. Falling back to RRF order.")

        # Fallback: no re-ranker, return RRF-ordered with neutral score
        return [(doc, 0.5) for doc in candidates[:top_k]]

    def _reciprocal_rank_fusion(self, result_lists: list[list[Document]],
                                 k: int = 60) -> list[Document]:
        """
        Reciprocal Rank Fusion (RRF) — merges ranked lists.
        Score = sum(1 / (k + rank)) for each list the document appears in.
        """
        scores = {}
        doc_map = {}

        for results in result_lists:
            for rank, doc in enumerate(results):
                # Use page_content as dedup key
                doc_key = doc.page_content[:100]  # First 100 chars as key
                if doc_key not in scores:
                    scores[doc_key] = 0.0
                    doc_map[doc_key] = doc
                scores[doc_key] += 1.0 / (k + rank + 1)

        # Sort by RRF score descending
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys]

    def search_with_metadata_filter(self, query: str,
                                     metadata_filter: Optional[dict] = None,
                                     top_k: int = TOP_K) -> list[Document]:
        """
        Search with optional metadata filtering.
        If FAISS supports filter, use it; otherwise filter post-retrieval.
        """
        # First get hybrid results
        results = self.hybrid_search(query, top_k=FAISS_FETCH_K)

        if not metadata_filter or not results:
            return results[:top_k]

        # Post-filter by metadata
        filtered = []
        for doc in results:
            match = True
            for key, value in metadata_filter.items():
                doc_value = doc.metadata.get(key, "")
                if value and value.lower() not in str(doc_value).lower():
                    match = False
                    break
            if match:
                filtered.append(doc)

        return filtered[:top_k] if filtered else results[:top_k]

    # ----------------------------------------------------------
    # Confidence Scoring
    # ----------------------------------------------------------
    @staticmethod
    def reranker_score_to_confidence(score: float) -> float:
        """
        Map cross-encoder re-ranker score to 0.0-1.0 confidence.
        Re-ranker output range is roughly -10 to +10 (sigmoid-ish).
        
        Mapping:
          score >= 5.0  → 0.95 (very high confidence)
          score >= 2.0  → 0.85
          score >= 0.5  → 0.75
          score >= 0.0  → 0.60
          score >= -2.0 → 0.40
          score < -2.0  → 0.20
        """
        import math
        # Sigmoid mapping: 1 / (1 + exp(-score * 0.5))
        # This gives a smooth 0-1 curve centered around 0
        try:
            confidence = 1.0 / (1.0 + math.exp(-score * 0.5))
        except OverflowError:
            confidence = 0.0 if score < 0 else 1.0
        return round(confidence, 3)

    # ----------------------------------------------------------
    # Public API (backward compatible)
    # ----------------------------------------------------------
    async def get_answer(self, query: str) -> str:
        """Direct RAG query (stand-alone, not used by voice agent)."""
        if not self.vector_store:
            return "I'm sorry, my knowledge base is currently unavailable."

        docs = self.hybrid_search(query, top_k=3)
        context = "\n".join([d.page_content for d in docs])
        return f"Context found: {context[:300]}..."


rag_service = None  # Will be initialized on import via agent_workflow.py
