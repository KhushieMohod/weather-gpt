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
        import faiss
        from .document_processor import DocumentProcessor

        chunks = DocumentProcessor(self.documents_dir).load_chunks()
        if not chunks:
            raise ValueError(f"No .txt or .pdf advisory documents found in {self.documents_dir}")

        texts = [chunk.text for chunk in chunks]
        embeddings = self._load_model().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_dir / "advisories.faiss"))
        (self.index_dir / "metadata.json").write_text(
            json.dumps([chunk.__dict__ for chunk in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._index = index
        self._metadata = [chunk.__dict__ for chunk in chunks]
        return len(chunks)

    def _load_persisted(self) -> None:
        import faiss

        index_path = self.index_dir / "advisories.faiss"
        metadata_path = self.index_dir / "metadata.json"
        if not index_path.exists() or not metadata_path.exists():
            self.initialize_vector_db()
            return
        self._index = faiss.read_index(str(index_path))
        self._metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    def similarity_search(self, query: str, k: int = 3) -> list[str]:
        if not query.strip() or k < 1:
            return []
        if self._index is None:
            self._load_persisted()
        query_embedding = self._load_model().encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        _, indices = self._index.search(query_embedding, min(k, self._index.ntotal))
        return [self._metadata[index]["text"] for index in indices[0] if index >= 0]
