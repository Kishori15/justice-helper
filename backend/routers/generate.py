"""
FastAPI router for Grounded Generation and Verification endpoints.
Implements DATA_SCHEMA.md §7: POST /api/generate_explanation, POST /api/generate_drafts
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.corpus import corpus_store
from backend.db import get_case, save_case
from backend.enrichment import enrich_query
from backend.generation import generate_rights_and_drafts
from backend.models import (
    CitationVerificationResult,
    GenerationOutput,
    LegalBasisItem,
    RetrievalCandidate,
)
from backend.reranker import reranker_engine
from backend.retrieval import hybrid_retrieve
from backend.verification import verify_citations

router = APIRouter(prefix="/api", tags=["generate"])


class GenerateRequest(BaseModel):
    case_id: str
    tone: Optional[str] = "polite_first_notice"


class ExplanationResponse(BaseModel):
    rights_summary: str
    legal_basis: List[LegalBasisItem]


def _get_or_fetch_retrieved_passages(case) -> List[RetrievalCandidate]:
    corpus_store.load()
    if case.retrieved_passage_ids:
        passages = []
        for pid in case.retrieved_passage_ids:
            entry = corpus_store.entries_by_id.get(pid)
            if entry:
                passages.append(
                    RetrievalCandidate(
                        id=entry.id,
                        retrieval_score=1.0,
                        retrieval_source="both",
                        text=entry.text,
                        title=entry.title,
                        section_number=entry.section_number,
                        source_type=entry.source_type,
                        url=entry.url,
                    )
                )
        if passages:
            return passages

    # Otherwise run retrieval
    enriched = enrich_query(case)
    candidates = hybrid_retrieve(enriched, top_k_candidates=20)
    top_candidates, _ = reranker_engine.rerank(enriched.search_query, candidates, top_n=5)
    case.retrieved_passage_ids = [c.id for c in top_candidates]
    return top_candidates


@router.post("/generate_explanation", response_model=ExplanationResponse)
def generate_explanation_endpoint(req: GenerateRequest):
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    passages = _get_or_fetch_retrieved_passages(case)
    output = generate_rights_and_drafts(case, passages)
    save_case(case)

    return ExplanationResponse(
        rights_summary=output.rights_summary,
        legal_basis=output.legal_basis
    )


@router.post("/generate_drafts", response_model=GenerationOutput)
def generate_drafts_endpoint(req: GenerateRequest):
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    passages = _get_or_fetch_retrieved_passages(case)
    output = generate_rights_and_drafts(case, passages)
    if req.tone and output.draft_email:
        output.draft_email.tone = req.tone  # type: ignore

    case.generation_output = output
    case.status = "generated"
    save_case(case)

    return output


@router.post("/verify", response_model=CitationVerificationResult)
def verify_endpoint(req: GenerateRequest):
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.generation_output:
        raise HTTPException(status_code=400, detail="No generation output found on case to verify")

    passages = _get_or_fetch_retrieved_passages(case)
    verification_res = verify_citations(case.generation_output, passages)
    case.status = "verified"
    save_case(case)

    return verification_res
