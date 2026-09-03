"""
FastAPI router for Retrieval endpoint.
Implements DATA_SCHEMA.md §7: POST /api/retrieve
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_case, save_case
from backend.enrichment import enrich_query
from backend.models import RetrievalResult
from backend.reranker import reranker_engine
from backend.retrieval import hybrid_retrieve

router = APIRouter(prefix="/api", tags=["retrieve"])


class RetrieveRequest(BaseModel):
    case_id: str
    issue_type: Optional[str] = None
    query: Optional[str] = None


@router.post("/retrieve", response_model=RetrievalResult)
def handle_retrieve(req: RetrieveRequest):
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if req.issue_type and case.issue:
        case.issue.issue_type = req.issue_type  # type: ignore

    # 1. Query enrichment & topic mapping
    enriched = enrich_query(case)
    if req.query:
        enriched.search_query = req.query

    # 2. Hybrid retrieval (FAISS + BM25 + Topic metadata)
    candidates = hybrid_retrieve(enriched, top_k_candidates=20)

    # 3. Cross-encoder re-ranking & deduplication
    top_candidates, reranked_scores = reranker_engine.rerank(
        query=enriched.search_query,
        candidates=candidates,
        top_n=5
    )

    # Update case state
    case.retrieved_passage_ids = [c.id for c in top_candidates]
    case.status = "retrieved"
    save_case(case)

    return RetrievalResult(
        case_id=case.case_id,
        candidates=top_candidates,
        reranked=reranked_scores
    )
