"""
rag/hybrid_search.py
Combines ANN Vector Similarity Search with BM25 Keyword Search.
"""
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from .vector_store import UtilityVectorStore


class HybridSearchEngine:
    def __init__(self, vector_store: UtilityVectorStore, chunks: List[Dict[str, Any]]):
        self.vector_store = vector_store
        self.chunks = chunks
        
        # Build tokenized corpus for BM25 matching
        corpus = [chunk["text"].lower().split() for chunk in self.chunks]
        self.bm25 = BM25Okapi(corpus)

    def search(
        self, 
        query: str, 
        top_k: int = 3, 
        vector_weight: float = 0.5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval by blending normalized vector similarity and BM25 scores.
        """
        if not self.chunks:
            return []

        # 1. Vector Search
        vector_results = self.vector_store.query_similarity(
            query_text=query, 
            top_k=len(self.chunks), 
            metadata_filter=metadata_filter
        )
        
        vector_scores = {}
        for res in vector_results:
            dist = res.get("distance") or 0.0
            vector_scores[res["id"]] = 1.0 / (1.0 + dist)

        # 2. BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores_raw = self.bm25.get_scores(tokenized_query)
        max_bm25 = max(bm25_scores_raw) if len(bm25_scores_raw) > 0 and max(bm25_scores_raw) > 0 else 1.0

        # 3. Score Blending
        hybrid_results = []
        for idx, chunk in enumerate(self.chunks):
            cid = chunk["id"]
            
            if cid not in vector_scores and metadata_filter is not None:
                continue

            norm_v_score = vector_scores.get(cid, 0.0)
            norm_b_score = bm25_scores_raw[idx] / max_bm25
            
            combined_score = (vector_weight * norm_v_score) + ((1.0 - vector_weight) * norm_b_score)
            
            res_item = chunk.copy()
            res_item["retrieval_type"] = "hybrid_bm25_vector"
            res_item["vector_score"] = round(norm_v_score, 4)
            res_item["bm25_score"] = round(norm_b_score, 4)
            res_item["hybrid_score"] = round(combined_score, 4)
            hybrid_results.append(res_item)

        # Sort descending by hybrid score
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return hybrid_results[:top_k]