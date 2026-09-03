"""
Unit tests for Legal Corpus Loading and Index Structure.
"""
from backend.config import CORPUS_DIR, FAISS_INDEX_PATH, BM25_INDEX_PATH, ID_MAP_PATH
from backend.corpus import load_corpus_entries, corpus_store


def test_corpus_files_exist_and_parse():
    entries = load_corpus_entries(CORPUS_DIR)
    assert len(entries) >= 12, "Corpus should contain at least 12 curated sections"
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids)), "Corpus IDs must be unique"
    assert "cpa2019_sec2_7" in ids
    assert "ecomm2020_rule4_2" in ids
    assert "nch_process_filing" in ids


def test_corpus_store_loaded():
    corpus_store.load()
    assert corpus_store.faiss_index is not None
    assert corpus_store.bm25_index is not None
    assert len(corpus_store.entries_by_id) > 0
    assert FAISS_INDEX_PATH.exists()
    assert BM25_INDEX_PATH.exists()
    assert ID_MAP_PATH.exists()
