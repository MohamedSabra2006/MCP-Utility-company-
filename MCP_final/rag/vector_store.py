"""
rag/vector_store.py
Vector DB Management using ChromaDB ANN Vector Similarity.
"""
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional


class UtilityVectorStore:
    def __init__(self, collection_name: str = "utility_regulations"):
        self.client = chromadb.Client()
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )

    def add_documents(self, chunks: List[Dict[str, Any]]):
        """
        Adds text chunks with unique IDs and metadata into ChromaDB.
        """
        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query_similarity(
        self, 
        query_text: str, 
        top_k: int = 3, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes ANN HNSW similarity search with optional metadata filtering.
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=metadata_filter
        )
        
        formatted_results = []
        if results and results.get("documents"):
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        return formatted_results