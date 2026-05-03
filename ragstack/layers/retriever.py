from __future__ import annotations

import json
from collections import deque

from ragstack.base import RetrieverBackend


class GraphifyRetrieverBackend(RetrieverBackend):
    def __init__(
        self,
        graph_path: str,
        report_path: str,
        hop_limit: int = 3,
        edge_types: list[str] | None = None,
    ):
        self._hop_limit = hop_limit
        self._edge_types = set(edge_types or [])
        self._graph = self._load_graph(graph_path)
        self._report = self._load_report(report_path)

    def _load_graph(self, path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[ragstack] graphify: graph file not found at {path}, using empty graph")
            return {"nodes": [], "edges": []}

    def _load_report(self, path: str) -> str:
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def _seed_nodes(self, query: str) -> list[str]:
        query_lower = query.lower()
        seeds = []
        for node in self._graph.get("nodes", []):
            label = str(node.get("label", node.get("id", ""))).lower()
            if any(word in label for word in query_lower.split() if len(word) > 2):
                seeds.append(node["id"])
            if len(seeds) >= 5:
                break
        return seeds

    def _bfs(self, seed_ids: list[str]) -> list[str]:
        # Build adjacency: node_id → [(neighbor_id, relation)]
        adj: dict[str, list[tuple[str, str]]] = {}
        for edge in self._graph.get("edges", []):
            relation = edge.get("relation", edge.get("type", ""))
            if self._edge_types and relation not in self._edge_types:
                continue
            src, dst = edge.get("source", edge.get("src", "")), edge.get("target", edge.get("dst", ""))
            adj.setdefault(src, []).append((dst, relation))
            adj.setdefault(dst, []).append((src, relation))

        visited: set[str] = set(seed_ids)
        queue: deque[tuple[str, int]] = deque((n, 0) for n in seed_ids)
        result = list(seed_ids)

        while queue:
            node_id, depth = queue.popleft()
            if depth >= self._hop_limit:
                continue
            for neighbor, _ in adj.get(node_id, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    queue.append((neighbor, depth + 1))

        return result

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        seeds = self._seed_nodes(query)
        if not seeds:
            # Fall back to report text if no seed nodes found
            if self._report:
                return [{"text": self._report[:2000], "source": "GRAPH_REPORT.md", "score": 0.5, "metadata": {}}]
            return []

        node_ids = self._bfs(seeds)
        node_map = {n["id"]: n for n in self._graph.get("nodes", [])}

        chunks = []
        for nid in node_ids[:top_k]:
            node = node_map.get(nid, {})
            text = node.get("content", node.get("label", node.get("description", str(node))))
            chunks.append({
                "text": text,
                "source": node.get("file", node.get("source", nid)),
                "score": 1.0 if nid in seeds else 0.7,
                "metadata": {"node_id": nid, "type": node.get("type", "")},
            })
        return chunks


class ChromaRetrieverBackend(RetrieverBackend):
    def __init__(self, embedder, host: str, port: int, collection: str):
        import chromadb
        self._embedder = embedder
        self._client = chromadb.HttpClient(host=host, port=port)
        self._col = self._client.get_or_create_collection(collection)

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        vec = self._embedder.embed(query)
        results = self._col.query(query_embeddings=[vec], n_results=top_k)
        chunks = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            chunks.append({
                "text": doc,
                "source": meta.get("source", ""),
                "score": 1.0 - float(dist),
                "metadata": meta,
            })
        return chunks


class PineconeRetrieverBackend(RetrieverBackend):
    def __init__(self, embedder, index_name: str, environment: str):
        import pinecone
        self._embedder = embedder
        pinecone.init(environment=environment)
        self._index = pinecone.Index(index_name)

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        vec = self._embedder.embed(query)
        results = self._index.query(vector=vec, top_k=top_k, include_metadata=True)
        chunks = []
        for match in results.get("matches", []):
            meta = match.get("metadata", {})
            chunks.append({
                "text": meta.get("text", ""),
                "source": meta.get("source", match["id"]),
                "score": float(match.get("score", 0)),
                "metadata": meta,
            })
        return chunks


class WeaviateRetrieverBackend(RetrieverBackend):
    def __init__(self, embedder, url: str, class_name: str):
        import weaviate
        self._embedder = embedder
        self._client = weaviate.Client(url=url)
        self._class_name = class_name

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        vec = self._embedder.embed(query)
        result = (
            self._client.query
            .get(self._class_name, ["text", "source"])
            .with_near_vector({"vector": vec})
            .with_limit(top_k)
            .with_additional(["distance"])
            .do()
        )
        items = result.get("data", {}).get("Get", {}).get(self._class_name, [])
        chunks = []
        for item in items:
            dist = item.get("_additional", {}).get("distance", 1.0)
            chunks.append({
                "text": item.get("text", ""),
                "source": item.get("source", ""),
                "score": 1.0 - float(dist),
                "metadata": {},
            })
        return chunks


class MemoryRetrieverBackend(RetrieverBackend):
    """Zero-dependency backend. Accepts docs at init; supports dynamic add_docs()."""

    def __init__(self, docs: list[dict] | None = None):
        self._docs: list[dict] = list(docs or [])

    def add_docs(self, docs: list[dict]) -> int:
        """Append documents at runtime. Returns new total count."""
        self._docs.extend(docs)
        return len(self._docs)

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        query_words = set(query.lower().split())
        scored = []
        for doc in self._docs:
            text = doc.get("text", "")
            doc_words = set(text.lower().split())
            hits = len(query_words & doc_words)
            score = hits / max(len(query_words), 1)
            scored.append({
                "text": text,
                "source": doc.get("source", "memory"),
                "score": score,
                "metadata": doc.get("metadata", {}),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


RETRIEVER_BACKENDS: dict[str, type[RetrieverBackend]] = {
    "graphify": GraphifyRetrieverBackend,
    "chroma": ChromaRetrieverBackend,
    "pinecone": PineconeRetrieverBackend,
    "weaviate": WeaviateRetrieverBackend,
    "memory": MemoryRetrieverBackend,
}
