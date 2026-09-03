"""
Cross-Encoder Re-ranking and Deduplication Module.
Implements ARCHITECTURE.md §2.5 and DATA_SCHEMA.md §3.
Uses BAAI/bge-reranker-base (or fallback cross-scoring) to rank candidates.
"""
from typing import List, Optional, Tuple
from backend.config import RERANKER_MODEL
from backend.models import RerankedCandidate, RetrievalCandidate


class Reranker:
    """
    Lazy-loaded Cross-Encoder re-ranker.
    """
    def __init__(self, model_name: str = RERANKER_MODEL):
        self.model_name = model_name
        self._model = None
        self._failed = False

    @property
    def model(self):
        if self._model is None and not self._failed:
            try:
                # Try loading CrossEncoder with local_files_only first if cached
                from sentence_transformers import CrossEncoder
                try:
                    self._model = CrossEncoder(self.model_name, local_files_only=True)
                except Exception:
                    self._model = CrossEncoder(self.model_name)
            except Exception as e:
                logger_msg = f"Notice: CrossEncoder {self.model_name} not available locally yet ({e}). Using hybrid RRF score fallback."
                print(logger_msg)
                self._failed = True
        return self._model

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
        top_n: int = 5
    ) -> Tuple[List[RetrievalCandidate], List[RerankedCandidate]]:
        """
        Scores (query, passage) pairs, sorts, deduplicates, and returns top_n passages.
        """
        if not candidates:
            return [], []

        # If cross-encoder is available, score pairs
        if self.model is not None:
            pairs = [[query, f"{c.title} {c.section_number}: {c.text}"] for c in candidates]
            scores = self.model.predict(pairs)
            scored_list = list(zip(candidates, scores))
            # Sort descending by cross-encoder score
            scored_list.sort(key=lambda x: float(x[1]), reverse=True)
        else:
            # Fallback to retrieval_score
            scored_list = [(c, c.retrieval_score) for c in candidates]
            scored_list.sort(key=lambda x: float(x[1]), reverse=True)

        # Deduplicate passages by section / ID
        seen_sections = set()
        deduped_candidates: List[RetrievalCandidate] = []
        reranked_scores: List[RerankedCandidate] = []

        for cand, score in scored_list:
            sec_key = f"{cand.source_type}_{cand.section_number}"
            if sec_key in seen_sections:
                continue
            seen_sections.add(sec_key)
            deduped_candidates.append(cand)
            reranked_scores.append(
                RerankedCandidate(
                    id=cand.id,
                    rerank_score=round(float(score), 4)
                )
            )
            if len(deduped_candidates) >= top_n:
                break

        return deduped_candidates, reranked_scores


# Global reranker instance
reranker_engine = Reranker()
