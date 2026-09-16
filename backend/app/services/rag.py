"""RAG Pipeline — ChromaDB + DeepSeek Embedding for question retrieval."""
import json
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import settings


class RAGPipeline:
    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )

    def add_question(self, question_id: int, content: str, embedding: list[float],
                     metadata: dict) -> str:
        """Add a single question vector to ChromaDB. Returns the embedding_id."""
        eid = str(question_id)
        self._collection.upsert(
            ids=[eid],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[content],
        )
        return eid

    def add_questions_batch(self, items: list[dict]) -> list[str]:
        """Batch upsert questions. Each item: {id, content, embedding, metadata}."""
        if not items:
            return []
        ids = [str(it["id"]) for it in items]
        embeddings = [it["embedding"] for it in items]
        metadatas = [it["metadata"] for it in items]
        documents = [it["content"] for it in items]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return ids

    def search(self, query_embedding: list[float], top_k: int = 20,
               where: dict | None = None) -> list[dict]:
        """Semantic search. Returns [{id, metadata, distance}, ...]."""
        kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        out = []
        if results["ids"] and results["ids"][0]:
            for i, eid in enumerate(results["ids"][0]):
                out.append({
                    "id": int(eid),
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "document": results["documents"][0][i] if results["documents"] else "",
                })
        return out

    def delete_question(self, question_id: int):
        """Remove a question vector by its database ID."""
        self._collection.delete(ids=[str(question_id)])

    def count(self) -> int:
        return self._collection.count()

    def reset(self):
        """Delete the collection and recreate it."""
        self._client.delete_collection("questions")
        self._collection = self._client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )
