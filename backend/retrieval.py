"""
Hybrid Retrieval Module for JusticeHelper.
Implements ARCHITECTURE.md §2.4 and DATA_SCHEMA.md §3.
Combines Vector Search (FAISS), BM25 Keyword Search, and Topic Metadata Filtering via RRF.
"""
from typing import Dict, List, Set, Tuple
import numpy as np

from backend.corpus import corpus_store, tokenize_for_bm25
from backend.models import EnrichedQuery, RetrievalCandidate, RetrievalResult


def hybrid_retrieve(
    enriched_query: EnrichedQuery,
    top_k_candidates: int = 20
) -> List[RetrievalCandidate]:
    """
    Executes 3 parallel retrieval signals:
    1. FAISS dense vector search
    2. BM25 keyword search
    3. Metadata filtering by topic
    Fuses rankings with Reciprocal Rank Fusion (RRF) and topic boosting.
    """
    corpus_store.load()

    query_str = enriched_query.search_query
    topic_filter_set: Set[str] = set(enriched_query.topic_filter)
    total_docs = len(corpus_store.index_to_id)
    k_search = min(top_k_candidates * 2, total_docs)

    # 1. Vector Search via FAISS
    q_emb = corpus_store.embedder.encode([query_str], normalize_embeddings=True, show_progress_bar=False)
    q_emb = np.array(q_emb, dtype=np.float32)
    vector_scores, vector_indices = corpus_store.faiss_index.search(q_emb, k_search)

    vector_ranks: Dict[str, int] = {}
    for rank, idx in enumerate(vector_indices[0]):
        if idx >= 0 and idx < total_docs:
            doc_id = corpus_store.index_to_id[idx]
            vector_ranks[doc_id] = rank + 1

    # 2. Keyword Search via BM25
    q_tokens = tokenize_for_bm25(query_str)
    bm25_scores = corpus_store.bm25_index.get_scores(q_tokens)
    bm25_top_indices = np.argsort(bm25_scores)[::-1][:k_search]

    bm25_ranks: Dict[str, int] = {}
    for rank, idx in enumerate(bm25_top_indices):
        if idx >= 0 and idx < total_docs:
            doc_id = corpus_store.index_to_id[idx]
            bm25_ranks[doc_id] = rank + 1

    # 3. Combine with Reciprocal Rank Fusion (RRF) + Topic Boost
    rrf_k = 60.0
    all_doc_ids = set(vector_ranks.keys()).union(set(bm25_ranks.keys()))
    scored_candidates: List[Tuple[str, float, str]] = []

    for doc_id in all_doc_ids:
        entry = corpus_store.entries_by_id.get(doc_id)
        if not entry:
            continue

        score = 0.0
        sources = []

        if doc_id in vector_ranks:
            score += 1.0 / (rrf_k + vector_ranks[doc_id])
            sources.append("vector")

        if doc_id in bm25_ranks:
            score += 1.0 / (rrf_k + bm25_ranks[doc_id])
            sources.append("keyword")

        # Metadata Topic Filtering / Boosting
        entry_topics_set = set(entry.topics)
        matching_topics = entry_topics_set.intersection(topic_filter_set)
        if matching_topics:
            # Boost score for relevant domain topics
            boost = 1.0 + (0.25 * len(matching_topics))
            score *= boost

        retrieval_source = "both" if len(sources) > 1 else sources[0]
        scored_candidates.append((doc_id, score, retrieval_source))

    # Sort candidates by combined score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    top_candidates = scored_candidates[:top_k_candidates]

    results: List[RetrievalCandidate] = []
    for doc_id, score, source in top_candidates:
        entry = corpus_store.entries_by_id[doc_id]
        results.append(
            RetrievalCandidate(
                id=entry.id,
                retrieval_score=round(float(score), 4),
                retrieval_source=source,  # type: ignore
                text=entry.text,
                title=entry.title,
                section_number=entry.section_number,
                source_type=entry.source_type,
                url=entry.url,
            )
        )

    return results
