from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_DIR = ROOT / "backend" / "rag" / "vector_db"
INDEX_FILE = INDEX_DIR / "advisories.faiss"
METADATA_FILE = INDEX_DIR / "metadata.json"


def ensure_index() -> None:
    if INDEX_FILE.exists() and METADATA_FILE.exists():
        print(f"Using existing advisory index: {INDEX_DIR}")
        return
    print("Advisory index not found. Seeding local documents...")
    subprocess.run(
        [sys.executable, "-m", "backend.scripts.ingest_docs"],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    ensure_index()
    os.environ.setdefault("LLM_PROVIDER", "gemini")
    os.environ.setdefault("ENABLE_RISK_MONITOR", "false")
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is not installed. Run `pip install -r backend/requirements.txt` first."
        ) from exc
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
