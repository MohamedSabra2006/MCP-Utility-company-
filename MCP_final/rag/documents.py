"""
rag/documents.py
Document Loader, Semantic Chunker, and Seed Policy Regulations.
"""
from typing import List, Dict, Any, Optional


class DocumentChunker:
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks(
        self, 
        text: str, 
        metadata: Dict[str, Any], 
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Splits regulatory text into overlapping chunks and attaches unique chunk IDs.
        """
        words = text.split()
        chunks = []
        i = 0
        chunk_id = 0
        
        # Determine base ID for unique chunk naming
        base_id = doc_id or metadata.get("doc_id", "doc")
        
        while i < len(words):
            chunk_words = words[i : i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunk_meta = metadata.copy()
            unique_chunk_id = f"{base_id}_c{chunk_id}"
            chunk_meta["chunk_id"] = unique_chunk_id
            
            chunks.append({
                "id": unique_chunk_id,
                "text": chunk_text,
                "metadata": chunk_meta
            })
            
            chunk_id += 1
            i += (self.chunk_size - self.chunk_overlap)
            
        return chunks


# Seed Utility Regulations for RAG Indexing
SEED_REGULATIONS = [
    {
        "doc_id": "LAW-87-WINTER",
        "text": (
            "Rule 8.3-B: Winter Moratorium Mandate. No electric utility distribution company "
            "shall disconnect residential electrical service for non-payment during the winter freeze "
            "period starting November 1 through March 31 when forecasted temperatures drop below 32°F (0°C). "
            "Any pending disconnection tickets during this period must be suspended immediately."
        ),
        "metadata": {
            "doc_id": "LAW-87-WINTER",
            "state": "Cairo_North", 
            "year": 2026, 
            "policy_type": "Moratorium", 
            "effective_date": "2026-11-01"
        }
    },
    {
        "doc_id": "LAW-87-MEDICAL",
        "text": (
            "Rule 12.1-A: Medical Life-Support Exemption. Residential customer accounts where a registered "
            "resident relies on life-sustaining medical equipment (including home dialysis units, ventilators, "
            "and oxygen concentrators) are strictly protected from forced power disconnections under EgyptERA Law 87. "
            "Disconnection of protected meters requires high-level supervisor authorization via MCP Elicitation protocol."
        ),
        "metadata": {
            "doc_id": "LAW-87-MEDICAL",
            "state": "Cairo_North", 
            "year": 2026, 
            "policy_type": "Medical_Exemption", 
            "effective_date": "2026-01-01"
        }
    }
]