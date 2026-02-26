"""
ChromaDB vector store operations.
Embeds incident text using Ollama's embedding model.
All config from environment variables — no hardcoded values.
"""
import logging
import os
import uuid
from typing import Any

import chromadb
from langchain_ollama import OllamaEmbeddings

from apps.incidents.models import Fix, Incident

logger = logging.getLogger(__name__)


class IncidentVectorStore:
    """Vector store for incidents and fixes using ChromaDB and Ollama embeddings."""

    def __init__(self) -> None:
        persist_dir = os.environ.get("CHROMA_PERSIST_DIR") or "/app/chroma_data"
        collection_name = os.environ.get("CHROMA_COLLECTION_NAME") or "kubememory_incidents"
        ollama_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        embed_model = os.environ.get("OLLAMA_EMBED_MODEL") or "nomic-embed-text"

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embeddings = OllamaEmbeddings(
            model=embed_model,
            base_url=ollama_url,
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed_text(self, text: str) -> list[float]:
        """Embed a single text using Ollama. Raises on connection error."""
        try:
            return self._embeddings.embed_query(text)
        except Exception as e:
            msg = (
                "Ollama connection failed. Ensure Ollama is running and "
                f"OLLAMA_BASE_URL is correct. Error: {e}"
            )
            logger.error(msg)
            raise ConnectionError(msg) from e

    def embed_incident(self, incident: Incident) -> str:
        """
        Build embedding text from incident, add to collection, return Chroma document ID.
        Handles Ollama connection errors with a clear message.
        """
        parts = [
            str(incident.incident_type),
            incident.pod_name or "",
            incident.namespace or "",
            incident.description or "",
            (incident.raw_logs or "")[:500],
        ]
        embedding_text = " ".join(p.strip() for p in parts if p)

        occurred_at_str = (
            incident.occurred_at.isoformat() if incident.occurred_at else ""
        )
        metadata: dict[str, Any] = {
            "doc_type": "incident",
            "incident_id": incident.id,
            "pod_name": incident.pod_name or "",
            "namespace": incident.namespace or "",
            "incident_type": incident.incident_type or "",
            "severity": incident.severity or "",
            "occurred_at": occurred_at_str,
        }

        doc_id = f"incident_{incident.id}_{uuid.uuid4().hex[:8]}"
        vector = self._embed_text(embedding_text)

        self._collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[embedding_text[:50000]],
            metadatas=[{k: str(v) for k, v in metadata.items()}],
        )
        return doc_id

    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        filter_namespace: str | None = None,
        doc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Embed query, search collection with optional namespace and doc_type filter.
        doc_type: "incident", "fix", or "correction" to restrict results.
        Returns list of dicts: incident_id, similarity_score, metadata, document.
        """
        where_clauses: list[dict[str, Any]] = []
        if filter_namespace:
            where_clauses.append({"namespace": filter_namespace})
        if doc_type:
            where_clauses.append({"doc_type": doc_type})
        where = (
            {"$and": where_clauses}
            if len(where_clauses) > 1
            else (where_clauses[0] if where_clauses else None)
        )

        query_embedding = self._embed_text(query)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        out: list[dict[str, Any]] = []
        ids = result["ids"][0] if result["ids"] else []
        metadatas = result["metadatas"][0] if result["metadatas"] else []
        documents = result["documents"][0] if result["documents"] else []
        distances = result["distances"][0] if result["distances"] else []

        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else ""
            dist = distances[i] if i < len(distances) else None
            # Cosine distance: 0 = identical, 2 = opposite. Convert to similarity.
            similarity_score = 1.0 - (dist / 2.0) if dist is not None else 0.0
            out.append({
                "incident_id": meta.get("incident_id"),
                "similarity_score": round(similarity_score, 4),
                "metadata": meta,
                "document": doc,
            })
        return out

    def clear_all(self) -> None:
        """
        Remove all documents from the incidents collection (reset for disconnect/null state).
        Deletes and recreates the collection so it is empty.
        """
        name = self._collection.name
        self._client.delete_collection(name=name)
        self._collection = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB collection %s cleared.", name)

    def embed_fix(self, fix: Fix) -> str:
        """
        Embed fix description with metadata linking to incident.
        Tag with doc_type: "fix" in metadata for filtering.
        """
        text = fix.description or ""
        metadata = {
            "doc_type": "fix",
            "fix_id": fix.id,
            "incident_id": fix.incident_id,
            "pod_name": fix.incident.pod_name or "",
            "namespace": fix.incident.namespace or "",
        }
        doc_id = f"fix_{fix.id}_{uuid.uuid4().hex[:8]}"
        vector = self._embed_text(text)
        self._collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[text[:50000]],
            metadatas=[{k: str(v) for k, v in metadata.items()}],
        )
        return doc_id

    def update_with_correction(
        self,
        fix: Fix,
        correction: Fix,
    ) -> None:
        """
        Corrective RAG loop: add a document stating the correction overrides the fix.
        Metadata: doc_type: "correction", incident_id, original_fix_id, correction_fix_id.
        """
        text = (
            f"CORRECTION: {correction.description or ''} overrides "
            f"{fix.description or ''}"
        )
        metadata = {
            "doc_type": "correction",
            "incident_id": correction.incident_id,
            "original_fix_id": fix.id,
            "correction_fix_id": correction.id,
        }
        doc_id = f"correction_{correction.id}_{uuid.uuid4().hex[:8]}"
        vector = self._embed_text(text)
        self._collection.add(
            ids=[doc_id],
            embeddings=[vector],
            documents=[text[:50000]],
            metadatas=[{k: str(v) for k, v in metadata.items()}],
        )

    def get_incident_history(
        self,
        pod_name: str,
        namespace: str,
    ) -> list[dict[str, Any]]:
        """
        Query with where filter for pod_name and namespace.
        Returns all past incidents for this pod (metadata + document).
        """
        result = self._collection.get(
            where={
                "$and": [
                    {"pod_name": pod_name},
                    {"namespace": namespace},
                ]
            },
            include=["documents", "metadatas"],
        )
        out: list[dict[str, Any]] = []
        for i, doc_id in enumerate(result["ids"]):
            meta = result["metadatas"][i] if result["metadatas"] else {}
            doc = result["documents"][i] if result["documents"] else ""
            if meta.get("doc_type") in (None, ""):
                out.append({
                    "id": doc_id,
                    "metadata": meta,
                    "document": doc,
                })
        return out
