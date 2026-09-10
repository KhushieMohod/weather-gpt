from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.rag.vector_store import VectorStoreManager

DOCUMENTS_DIR = ROOT / "backend" / "rag" / "advisory_docs"
INDEX_DIR = ROOT / "backend" / "rag" / "vector_db"


def clear_index(index_dir: Path = INDEX_DIR) -> None:
    if index_dir.exists():
        shutil.rmtree(index_dir)


def seed_index() -> int:
    clear_index()
    manager = VectorStoreManager(documents_dir=DOCUMENTS_DIR, index_dir=INDEX_DIR)
    count = manager.initialize_vector_db()
    print(f"Indexed {count} advisory chunks into {INDEX_DIR}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the local WeatherGPT advisory index.")
    parser.parse_args()
    seed_index()


if __name__ == "__main__":
    main()
