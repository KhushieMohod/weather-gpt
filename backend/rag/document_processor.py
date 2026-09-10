from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    source: str
    chunk_index: int


class DocumentProcessor:
    def __init__(self, documents_dir: str | Path) -> None:
        self.documents_dir = Path(documents_dir)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _read_file(self, path: Path) -> str:
        if path.suffix.lower() == ".txt":
            return path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        return ""

    def load_chunks(self) -> list[DocumentChunk]:
        if not self.documents_dir.exists():
            return []

        chunks: list[DocumentChunk] = []
        for path in sorted(self.documents_dir.iterdir()):
            if path.suffix.lower() not in {".txt", ".pdf"} or not path.is_file():
                continue
            text = self._read_file(path).strip()
            for index, chunk in enumerate(self.splitter.split_text(text)):
                chunks.append(DocumentChunk(chunk, str(path), index))
        return chunks


def load_document_chunks(documents_dir: str | Path) -> list[DocumentChunk]:
    return DocumentProcessor(documents_dir).load_chunks()
