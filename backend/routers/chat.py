"""
FastAPI router for Chat Intake endpoint.
Implements DATA_SCHEMA.md §7: POST /api/chat
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_case, save_case
from backend.intake import create_new_case, process_intake_message
from backend.models import CaseObject

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    case_id: Optional[str] = None
    message: str
    user_name: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    updated_case_summary: CaseObject
    intake_round: int
    is_intake_complete: bool
    follow_up_question: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
def handle_chat(req: ChatRequest):
    case: Optional[CaseObject] = None
    if req.case_id:
        case = get_case(req.case_id)

    if not case:
        case = create_new_case(user_name=req.user_name)

    reply, updated_case = process_intake_message(case, req.message)
    save_case(updated_case)

    is_complete = updated_case.status in ["intake_completed", "issue_classified"]

    return ChatResponse(
        reply=reply,
        updated_case_summary=updated_case,
        intake_round=updated_case.intake_round,
        is_intake_complete=is_complete,
        follow_up_question=None if is_complete else reply
    )
