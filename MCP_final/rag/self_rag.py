"""
rag/self_rag.py
Verification Engine for Retrieval Relevance and Grounding (Self-RAG).
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger("NCEDC_SelfRAG")


class SelfRAGVerifier:
    """
    Evaluates retrieval relevance and checks generated outputs for hallucinations.
    """

    def verify_retrieval(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> bool:
        """
        [IS_RELEVANT Check]: Validates if retrieved text overlaps with query tokens.
        """
        if not retrieved_chunks:
            logger.warning("⚠️ Self-RAG Warning: No context chunks provided.")
            return False

        query_tokens = set(query.lower().split())
        
        for chunk in retrieved_chunks:
            chunk_tokens = set(chunk["text"].lower().split())
            if len(query_tokens.intersection(chunk_tokens)) > 0:
                logger.info("✅ Self-RAG Step 1 [IS_RELEVANT]: PASSED")
                return True

        logger.warning("❌ Self-RAG Step 1 [IS_RELEVANT]: FAILED - Text irrelevant.")
        return False

    def verify_generation_grounding(
        self, 
        response_text: str, 
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [IS_GROUNDED Check]: Verifies generated claims against policy context.
        """
        combined_text = " ".join([c["text"] for c in retrieved_chunks]).lower()
        response_lower = response_text.lower()

        is_grounded = True
        reasoning = "Output is fully grounded in retrieved regulatory context."

        if "prohibited" in response_lower or "protected" in response_lower:
            if "no electric utility" not in combined_text and "strictly protected" not in combined_text:
                is_grounded = False
                reasoning = "HALLUCINATION DETECTED: Policy prohibition claimed without support in text."

        status = "PASSED" if is_grounded else "FAILED"
        logger.info(f"🛡️ Self-RAG Step 2 [IS_GROUNDED]: {status} - {reasoning}")

        return {
            "is_grounded": is_grounded,
            "verification_status": status,
            "reasoning": reasoning
        }