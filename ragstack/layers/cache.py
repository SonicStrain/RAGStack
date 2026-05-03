from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ragstack.base import CacheBackend

if TYPE_CHECKING:
    pass


def _cosine(a, b) -> float:
    import numpy as np
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


class MemoryCacheBackend(CacheBackend):
    def __init__(self, embedder, similarity_threshold: float = 0.92, ttl_seconds: int = 3600):
        self._embedder = embedder
        self._threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._store: list[dict] = []

    def get(self, query: str) -> str | None:
        if not self._store:
            return None
        vec = self._embedder.embed(query)
        now = time.time()
        best_score = -1.0
        best_answer = None
        for entry in self._store:
            if self._ttl > 0 and now - entry["ts"] > self._ttl:
                continue
            score = _cosine(vec, entry["embedding"])
            if score > best_score:
                best_score = score
                best_answer = entry["answer"]
        if best_score >= self._threshold:
            return best_answer
        return None

    def set(self, query: str, answer: str) -> None:
        vec = self._embedder.embed(query)
        if not vec:
            return  # NullEmbedder — cache disabled, skip silently
        self._store.append({"embedding": vec, "answer": answer, "ts": time.time()})


class RedisCacheBackend(CacheBackend):
    def __init__(self, embedder, url: str, index_name: str,
                 similarity_threshold: float = 0.92, ttl_seconds: int = 3600):
        import redis as redis_lib
        from redis.commands.search.field import VectorField, TextField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType

        self._embedder = embedder
        self._threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._index = index_name
        self._r = redis_lib.from_url(url)

        try:
            self._r.ft(index_name).info()
        except Exception:
            schema = (
                TextField("answer"),
                VectorField(
                    "embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": 1536,
                        "DISTANCE_METRIC": "COSINE",
                    },
                ),
            )
            self._r.ft(index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=[f"{index_name}:"], index_type=IndexType.HASH),
            )

    def get(self, query: str) -> str | None:
        import numpy as np
        from redis.commands.search.query import Query

        vec = self._embedder.embed(query)
        vec_bytes = np.array(vec, dtype=np.float32).tobytes()
        q = (
            Query(f"*=>[KNN 1 @embedding $blob AS score]")
            .sort_by("score")
            .return_fields("answer", "score")
            .dialect(2)
        )
        results = self._r.ft(self._index).search(q, query_params={"blob": vec_bytes})
        if results.docs:
            doc = results.docs[0]
            score = float(getattr(doc, "score", 0))
            # RediSearch COSINE distance: 0 = identical, convert to similarity
            similarity = 1.0 - score
            if similarity >= self._threshold:
                return doc.answer
        return None

    def set(self, query: str, answer: str) -> None:
        import numpy as np

        vec = self._embedder.embed(query)
        key = f"{self._index}:{hash(query)}"
        mapping = {
            "answer": answer,
            "embedding": np.array(vec, dtype=np.float32).tobytes(),
        }
        self._r.hset(key, mapping=mapping)
        if self._ttl > 0:
            self._r.expire(key, self._ttl)


class QdrantCacheBackend(CacheBackend):
    def __init__(self, embedder, url: str, collection: str,
                 similarity_threshold: float = 0.92, ttl_seconds: int = 3600):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self._embedder = embedder
        self._threshold = similarity_threshold
        self._ttl = ttl_seconds
        self._collection = collection
        self._client = QdrantClient(url=url)

        existing = [c.name for c in self._client.get_collections().collections]
        if collection not in existing:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )

    def get(self, query: str) -> str | None:
        vec = self._embedder.embed(query)
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=vec,
            limit=1,
            score_threshold=self._threshold,
        )
        if hits:
            return hits[0].payload.get("answer")
        return None

    def set(self, query: str, answer: str) -> None:
        from qdrant_client.models import PointStruct
        import uuid

        vec = self._embedder.embed(query)
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vec,
                    payload={"answer": answer, "query": query},
                )
            ],
        )


CACHE_BACKENDS: dict[str, type[CacheBackend]] = {
    "memory": MemoryCacheBackend,
    "redis": RedisCacheBackend,
    "qdrant": QdrantCacheBackend,
}
