"""
rag/pipeline.py
Main Gateway unifying Vector Store, Hybrid Search, Agentic Multi-hop, and Self-RAG.
"""
import logging
from typing import List, Dict, Any, Optional
from .documents import DocumentChunker, SEED_REGULATIONS
from .vector_store import UtilityVectorStore
from .hybrid_search import HybridSearchEngine
from .agentic_rag import AgenticRAGRouter
from .self_rag import SelfRAGVerifier

logger = logging.getLogger("NCEDC_RAGPipeline")


class RAGPipeline:
    def __init__(self):
        logger.info("⚡ Initializing NCEDC Legal RAG Engine...")
        
        # 1. Chunk documents with unique IDs
        self.chunker = DocumentChunker()
        self.all_chunks = []
        for doc in SEED_REGULATIONS:
            chunks = self.chunker.create_chunks(
                text=doc["text"], 
                metadata=doc["metadata"], 
                doc_id=doc.get("doc_id")
            )
            self.all_chunks.extend(chunks)

        # 2. Add to Vector Store
        self.vector_store = UtilityVectorStore()
        self.vector_store.add_documents(self.all_chunks)

        # 3. Instantiate search engines & verifiers
        self.hybrid_engine = HybridSearchEngine(self.vector_store, self.all_chunks)
        self.verifier = SelfRAGVerifier()
        self.agentic_router = AgenticRAGRouter(self.hybrid_engine, self.verifier)
        
        logger.info(f"✅ RAG Engine online with {len(self.all_chunks)} indexed policy chunks.")

    def query_policy(
        self, 
        query: str, 
        mode: str = "hybrid", 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Unified Query Method. Modes available: 'naive', 'hybrid', 'agentic'
        """
        if mode == "agentic":
            return self.agentic_router.multi_hop_retrieval(query, metadata_filter=metadata_filter)
        
        elif mode == "hybrid":
            results = self.hybrid_engine.search(query, top_k=3, metadata_filter=metadata_filter)
            is_relevant = self.verifier.verify_retrieval(query, results)
            return {
                "query": query,
                "mode": "hybrid",
                "retrieved_chunks": results,
                "is_relevant": is_relevant,
                "synthesized_context": "\n---\n".join([c["text"] for c in results])
            }
        
        else:  # Naive Vector
            results = self.vector_store.query_similarity(query, top_k=3, metadata_filter=metadata_filter)
            return {
                "query": query,
                "mode": "naive",
                "retrieved_chunks": results,
                "synthesized_context": "\n---\n".join([c["text"] for c in results])
            }