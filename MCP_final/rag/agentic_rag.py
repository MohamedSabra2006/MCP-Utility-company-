"""
rag/agentic_rag.py
Multi-Hop Agentic RAG Reasoning Loop for complex queries.
"""
import logging
from typing import List, Dict, Any, Optional
from .hybrid_search import HybridSearchEngine
from .self_rag import SelfRAGVerifier

logger = logging.getLogger("NCEDC_AgenticRAG")


class AgenticRAGRouter:
    def __init__(self, hybrid_engine: HybridSearchEngine, verifier: Optional[SelfRAGVerifier] = None):
        self.hybrid_engine = hybrid_engine
        self.verifier = verifier or SelfRAGVerifier()

    def decompose_query(self, complex_query: str) -> List[str]:
        """
        Decomposes multi-part policy questions into simple sub-queries.
        """
        sub_queries = [complex_query]
        lowered = complex_query.lower()

        if "winter" in lowered or "freeze" in lowered or "moratorium" in lowered:
            sub_queries.append("winter moratorium weather freeze rule 8.3-B temperature")
        if "medical" in lowered or "dialysis" in lowered or "life support" in lowered:
            sub_queries.append("medical life support exemption rule 12.1-A EgyptERA")
        if "overdue" in lowered or "disconnection" in lowered:
            sub_queries.append("disconnection criteria non payment overdue days")

        seen = set()
        return [q for q in sub_queries if not (q in seen or seen.add(q))]

    def multi_hop_retrieval(
        self, 
        complex_query: str, 
        top_k_per_hop: int = 2, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes multi-hop retrieval across decomposed sub-queries.
        """
        logger.info(f"🔍 Starting Agentic Multi-Hop Retrieval for: '{complex_query}'")
        sub_queries = self.decompose_query(complex_query)
        logger.info(f"📋 Generated {len(sub_queries)} sub-queries: {sub_queries}")

        accumulated_chunks: Dict[str, Dict[str, Any]] = {}

        for hop_idx, sub_q in enumerate(sub_queries, start=1):
            hop_results = self.hybrid_engine.search(
                query=sub_q, 
                top_k=top_k_per_hop, 
                metadata_filter=metadata_filter
            )
            logger.info(f"  └─ Hop #{hop_idx} ('{sub_q}') retrieved {len(hop_results)} chunks.")
            
            for chunk in hop_results:
                if chunk["id"] not in accumulated_chunks:
                    chunk["retrieval_type"] = "agentic_multihop"
                    accumulated_chunks[chunk["id"]] = chunk

        retrieved_list = list(accumulated_chunks.values())
        is_relevant = self.verifier.verify_retrieval(complex_query, retrieved_list)
        
        return {
            "query": complex_query,
            "sub_queries": sub_queries,
            "total_hops": len(sub_queries),
            "retrieved_chunks": retrieved_list,
            "is_relevant": is_relevant,
            "synthesized_context": "\n---\n".join([c["text"] for c in retrieved_list])
        }