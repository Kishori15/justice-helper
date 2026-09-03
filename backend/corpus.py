"""
Corpus loader and indexing engine for JusticeHelper.
Implements ARCHITECTURE.md §2.3 and CORPUS.md §5, §6, §7.
"""
import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from backend.config import (
    BM25_INDEX_PATH,
    CORPUS_DIR,
    EMBEDDING_MODEL,
    FAISS_INDEX_PATH,
    ID_MAP_PATH,
    INDEX_DIR,
)
from backend.models import CorpusEntry


def load_corpus_entries(corpus_dir: Optional[Path] = None) -> List[CorpusEntry]:
    """
    Loads and validates all JSONL corpus files in data/corpus/ per CORPUS.md schema.
    """
    target_dir = corpus_dir or CORPUS_DIR
    entries: List[CorpusEntry] = []
    seen_ids = set()

    for jsonl_file in sorted(target_dir.glob("*.jsonl")):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = CorpusEntry(**data)
                    if entry.id in seen_ids:
                        raise ValueError(f"Duplicate corpus ID '{entry.id}' in {jsonl_file.name}:{line_no}")
                    seen_ids.add(entry.id)
                    entries.append(entry)
                except Exception as e:
                    raise ValueError(f"Error parsing {jsonl_file.name}:{line_no} - {e}")

    return entries


def get_corpus_lookup(entries: Optional[List[CorpusEntry]] = None) -> Dict[str, CorpusEntry]:
    """
    Returns a dictionary mapping entry id -> CorpusEntry.
    """
    if entries is None:
        entries = load_corpus_entries()
    return {entry.id: entry for entry in entries}


def tokenize_for_bm25(text: str) -> List[str]:
    """
    Simple whitespace & lowercase tokenizer for BM25 indexing.
    """
    import re
    tokens = re.findall(r"\b\w+\b", text.lower())
    return tokens


def build_indexes(force_rebuild: bool = False) -> None:
    """
    Builds FAISS vector index, BM25 keyword index, and ID map file.
    Saves artifacts in data/index/.
    """
    import faiss
    from rank_bm25 import BM25Okapi
    from sentence_transformers import SentenceTransformer

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if not force_rebuild and FAISS_INDEX_PATH.exists() and BM25_INDEX_PATH.exists() and ID_MAP_PATH.exists():
        print("Indexes already exist. Use --rebuild-index to force re-indexing.")
        return

    print("Loading corpus entries from", CORPUS_DIR)
    entries = load_corpus_entries()
    if not entries:
        raise ValueError(f"No corpus entries found in {CORPUS_DIR}")

    print(f"Found {len(entries)} corpus entries across statutory sources.")

    # 1. Prepare texts for embedding & BM25
    # Combine title, section_number, and text for rich indexing
    combined_texts = [
        f"{e.source_name} {e.section_number} {e.title}\n{e.text}"
        for e in entries
    ]

    # 2. Build Dense Vector Index with BGE embeddings
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = embedder.encode(combined_texts, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(embeddings)
    faiss.write_index(faiss_index, str(FAISS_INDEX_PATH))
    print(f"Saved FAISS index to {FAISS_INDEX_PATH} (vectors: {faiss_index.ntotal}, dim: {dim})")

    # 3. Build BM25 Index
    tokenized_corpus = [tokenize_for_bm25(t) for t in combined_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print(f"Saved BM25 index to {BM25_INDEX_PATH}")

    # 4. Save ID map & full metadata
    id_map = {
        "index_to_id": [e.id for e in entries],
        "entries": {e.id: e.model_dump() for e in entries}
    }
    with open(ID_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)
    print(f"Saved ID Map metadata to {ID_MAP_PATH}")
    print("Corpus index build complete.")


class CorpusStore:
    """
    Singleton / In-memory store for loaded indexes and corpus entries.
    """
    def __init__(self):
        self.entries_by_id: Dict[str, CorpusEntry] = {}
        self.index_to_id: List[str] = []
        self.faiss_index = None
        self.bm25_index = None
        self.embedder = None
        self._loaded = False

    def load(self):
        if self._loaded:
            return

        if not (FAISS_INDEX_PATH.exists() and BM25_INDEX_PATH.exists() and ID_MAP_PATH.exists()):
            print("Index files not found. Triggering index build...")
            build_indexes(force_rebuild=True)

        import faiss
        from sentence_transformers import SentenceTransformer

        with open(ID_MAP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.index_to_id = data["index_to_id"]
            self.entries_by_id = {k: CorpusEntry(**v) for k, v in data["entries"].items()}

        self.faiss_index = faiss.read_index(str(FAISS_INDEX_PATH))

        with open(BM25_INDEX_PATH, "rb") as f:
            self.bm25_index = pickle.load(f)

        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self._loaded = True


# Global store instance
corpus_store = CorpusStore()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JusticeHelper Corpus Management")
    parser.add_argument("--rebuild-index", action="store_true", help="Force rebuild of FAISS and BM25 indexes")
    args = parser.parse_args()

    build_indexes(force_rebuild=args.rebuild_index)
