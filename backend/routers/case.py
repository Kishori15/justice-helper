"""
FastAPI router for Case Management and Issue Classification.
Implements DATA_SCHEMA.md §7: POST /api/classify_issue, DELETE /api/case, and case lifecycle.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.checklist import generate_checklist
from backend.db import delete_case, get_case, list_cases, save_case
from backend.models import CaseObject, EvidenceChecklist

router = APIRouter(prefix="/api", tags=["case"])


class ClassifyIssueRequest(BaseModel):
    case_id: str
    user_text: str


class ClassifyIssueResponse(BaseModel):
    issue_type: Optional[str]
    extracted_fields: Dict[str, Any]


@router.post("/classify_issue", response_model=ClassifyIssueResponse)
def classify_issue_endpoint(req: ClassifyIssueRequest):
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    issue_type = case.issue.issue_type if case.issue else None
    return ClassifyIssueResponse(
        issue_type=issue_type,
        extracted_fields=case.model_dump()
    )


@router.get("/case", response_model=CaseObject)
def get_case_endpoint(case_id: str = Query(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/case", response_model=CaseObject)
def update_case_endpoint(case: CaseObject):
    save_case(case)
    return case


@router.delete("/case")
def delete_case_endpoint(case_id: str = Query(...)):
    success = delete_case(case_id)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found or already deleted")
    return {"deleted": True, "case_id": case_id}


@router.get("/cases")
def list_cases_endpoint():
    return list_cases()


@router.get("/checklist", response_model=EvidenceChecklist)
def get_checklist_endpoint(case_id: str = Query(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    issue_type = case.issue.issue_type if case.issue else "refund_delayed"
    platform = case.order_info.platform if case.order_info else None
    return generate_checklist(case_id=case_id, issue_type=issue_type, platform=platform)
