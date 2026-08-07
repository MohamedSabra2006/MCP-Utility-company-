"""
rag/naive_rag.py
Implements Naive RAG (baseline ANN similarity search).
"""
import logging
from typing import List, Dict, Any, Optional
from .vector_store import UtilityVectorStore

logger = logging.getLogger("NCEDC_NaiveRAG")


class NaiveRAG:
    def __init__(self, vector_store: UtilityVectorStore):
        self.vector_store = vector_store

    def retrieve(
        self, 
        query: str, 
        top_k: int = 3, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes basic ANN vector similarity retrieval.
        """
        logger.info(f"🔍 Running Naive RAG query: '{query}'")
        results = self.vector_store.query_similarity(
            query_text=query, 
            top_k=top_k, 
            metadata_filter=metadata_filter
        )
        
        for item in results:
            item["retrieval_type"] = "naive_vector"
            
        return results