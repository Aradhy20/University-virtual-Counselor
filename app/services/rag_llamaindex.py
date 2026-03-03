
import os
import logging
from typing import Optional
from dotenv import load_dotenv

# LlamaIndex Imports
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings
)
from llama_index.llms.groq import Groq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

class LangChainDocument:
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}

load_dotenv()

logger = logging.getLogger("aditi.rag_llama")

class RAGServiceV2:
    def __init__(self):
        from pathlib import Path
        ROOT_DIR = Path(__file__).parent.parent.parent
        self.persist_dir = str(ROOT_DIR / "app" / "data" / "storage")
        # Ensure we point to actual content
        self.data_dir = str(ROOT_DIR / "data" / "migrated_docs")
        
        # 1. Setup Models
        self._setup_models()
        
        # 2. Load or Build Index
        self.index = self._initialize_index()
        
        # 3. Create Query Engine
        self.query_engine = self.index.as_query_engine(
            llm=self.llm,
            similarity_top_k=3
        ) if self.index else None
        
        # 4. Agent Compatibility Flag
        self.vector_store = True

        # 5. Cross-encoder re-ranker (lazy loaded)
        self._reranker = None

    def _get_reranker(self):
        """Lazy-load cross-encoder re-ranker on first use."""
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
                logger.info(f"Loading cross-encoder re-ranker: {RERANKER_MODEL}")
                self._reranker = CrossEncoder(RERANKER_MODEL)
                logger.info("Cross-encoder re-ranker loaded successfully")
            except Exception as e:
                logger.warning(f"Cross-encoder load failed: {e}. Re-ranking disabled.")
                self._reranker = False
        return self._reranker if self._reranker is not False else None

    def _setup_models(self):
        """Configure global settings for LlamaIndex."""
        try:
            # Embedding Model (Local)
            # Using all-MiniLM-L6-v2 which is fast and effective
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            # LLM (Groq)
            # Using Llama-3.3-70b-versatile for high quality answers
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.error("GROQ_API_KEY missing!")
                
            self.llm = Groq(model="llama-3.3-70b-versatile", api_key=groq_api_key)
            Settings.llm = self.llm
            
            # Chunking
            Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
            
            logger.info("LlamaIndex models configured (Groq + HF Embeddings).")
        except Exception as e:
            logger.error(f"Model setup failed: {e}")

    def _initialize_index(self) -> Optional[VectorStoreIndex]:
        """Load index from disk or build from docs."""
        # Check if storage exists
        if os.path.exists(self.persist_dir):
            try:
                logger.info("Loading existing LlamaIndex from storage...")
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                index = load_index_from_storage(storage_context)
                logger.info("Index loaded successfully.")
                return index
            except Exception as e:
                logger.warning(f"Failed to load index: {e}. Rebuilding...")

        # Build new index
        if os.path.exists(self.data_dir):
            try:
                logger.info(f"Building new index from {self.data_dir}...")
                documents = SimpleDirectoryReader(self.data_dir, recursive=True).load_data()
                index = VectorStoreIndex.from_documents(documents)
                
                # Persist
                if not os.path.exists(self.persist_dir):
                    os.makedirs(self.persist_dir)
                index.storage_context.persist(persist_dir=self.persist_dir)
                
                logger.info(f"New index built with {len(documents)} documents.")
                return index
            except Exception as e:
                logger.error(f"Index build failed: {e}")
                return None
        else:
            logger.error(f"Data directory not found: {self.data_dir}")
            return None

    def retrieve_documents(self, query: str, top_k: int = 3) -> list[LangChainDocument]:
        """Retrieve relevant chunks as LangChain Documents (compatibility layer)."""
        if not self.index:
            return []
            
        try:
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            
            docs = []
            for node_with_score in nodes:
                node = node_with_score.node
                # Create LangChain document structure
                doc = LangChainDocument(
                    page_content=node.get_content(),
                    metadata={
                        "source": node.metadata.get("file_name", "unknown"),
                        "score": node_with_score.score
                    }
                )
                docs.append(doc)
            
            logger.info(f"Retrieved {len(docs)} documents via LlamaIndex")
            return docs
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def get_answer(self, query: str) -> str:
        """Async query interface."""
        if not self.query_engine:
            return "System is initializing or index failed."
            
        try:
            response = await self.query_engine.aquery(query)
            return str(response)
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return "I'm having trouble accessing my knowledge base properly."

    def hybrid_search(self, query: str, top_k: int = 3) -> list[LangChainDocument]:
        """Wrap retriever to satisfy agent signature."""
        return self.retrieve_documents(query, top_k=top_k)

    @staticmethod
    def reranker_score_to_confidence(score: float) -> float:
        """
        Map cross-encoder re-ranker score to 0.0-1.0 confidence.
        """
        import math
        try:
            confidence = 1.0 / (1.0 + math.exp(-score * 0.5))
        except OverflowError:
            confidence = 0.0 if score < 0 else 1.0
        return round(confidence, 3)

# Singleton
rag_service_v2 = None

if __name__ == "__main__":
    # Test Script
    import asyncio
    
    async def main():
        print("Initializing LlamaIndex Service...")
        rag = RAGServiceV2()
        
        test_queries = ["What is the fee structure for B.Tech?", "Hostel facilities available?", "Tell me about placement record"]
        
        print("\n--- Testing Retrieval ---")
        for q in test_queries:
            print(f"\nQuery: {q}")
            docs = rag.retrieve_documents(q)
            for i, d in enumerate(docs):
                print(f"[{i+1}] Score: {d.metadata['score']:.4f} | Source: {d.metadata['source']}")
                print(f"Content: {d.page_content[:150]}...")
                
        print("\n--- Testing Generation ---")
        ans = await rag.get_answer(test_queries[0])
        print(f"Answer: {ans}")

    asyncio.run(main())
