from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class VectorStoreManager:
    def __init__(
        self,
        documents_dir: str | Path | None = None,
        index_dir: str | Path | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        root = Path(__file__).resolve().parent
        self.documents_dir = Path(documents_dir or root / "advisory_docs")
        self.index_dir = Path(index_dir or root / "vector_db")
        self.model_name = model_name
        self._index: Any = None
        self._model: Any = None
        self._metadata: list[dict[str, Any]] = []

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def initialize_vector_db(self) -> int:
        """Process advisory files, build a FAISS index, and persist it locally."""
        from .document_processor import DocumentProcessor

        chunks = DocumentProcessor(self.documents_dir).load_chunks()
        if not chunks:
            raise ValueError(f"No .txt or .pdf advisory documents found in {self.documents_dir}")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        (self.index_dir / "metadata.json").write_text(
            json.dumps([chunk.__dict__ for chunk in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._metadata = [chunk.__dict__ for chunk in chunks]

        try:
            import faiss
            texts = [chunk.text for chunk in chunks]
            embeddings = self._load_model().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            index = faiss.IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, str(self.index_dir / "advisories.faiss"))
            self._index = index
        except ImportError:
            logger.warning("faiss is not installed. Persisting advisory chunk metadata for local text keyword search.")
            self._index = None

        return len(chunks)

    def _local_keyword_search(self, query: str, k: int = 3) -> list[str]:
        """Fallback retrieval reading raw advisory text documents when vector index is unavailable."""
        docs_dir = Path(__file__).resolve().parent / "advisory_docs"
        if not docs_dir.exists():
            return []
        words = {w.lower() for w in query.split() if len(w) > 3}
        matches: list[tuple[int, str]] = []
        for file in docs_dir.glob("*.txt"):
            try:
                text = file.read_text(encoding="utf-8")
                score = sum(1 for w in words if w in text.lower())
                matches.append((score, text[:1000]))
            except Exception:
                continue
        matches.sort(key=lambda m: m[0], reverse=True)
        return [m[1] for m in matches[:k] if m[0] > 0] or [m[1] for m in matches[:1]]

    def _load_persisted(self) -> None:
        try:
            import faiss
        except ImportError:
            logger.warning("faiss-cpu not installed; using local text advisory fallback")
            return

        index_path = self.index_dir / "advisories.faiss"
        metadata_path = self.index_dir / "metadata.json"
        if not index_path.exists() or not metadata_path.exists():
            try:
                self.initialize_vector_db()
            except Exception as exc:
                logger.warning("Could not initialize FAISS index (%s)", exc)
            return
        try:
            self._index = faiss.read_index(str(index_path))
            self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Could not load FAISS index (%s)", exc)

    def similarity_search(self, query: str, k: int = 3) -> list[str]:
        if not query.strip() or k < 1:
            return []
        if self._index is None:
            self._load_persisted()

        if self._index is None or not self._metadata:
            return self._local_keyword_search(query, k)

        try:
            query_embedding = self._load_model().encode(
                [query], convert_to_numpy=True, normalize_embeddings=True
            )
            _, indices = self._index.search(query_embedding, min(k, self._index.ntotal))
            return [self._metadata[index]["text"] for index in indices[0] if index >= 0]
        except Exception as exc:
            logger.warning("FAISS similarity search failed (%s), using local fallback", exc)
            return self._local_keyword_search(query, k)
