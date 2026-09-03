"""
FastAPI router for PDF and DOCX Export endpoints.
Implements DATA_SCHEMA.md §7: GET /api/export/pdf, GET /api/export/docx
"""
from fastapi import APIRouter, HTTPException, Query, Response
from backend.db import get_case
from backend.export_docx import generate_docx_bytes
from backend.export_pdf import generate_pdf_bytes

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/pdf")
def export_pdf_endpoint(case_id: str = Query(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    pdf_bytes = generate_pdf_bytes(case)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="justicehelper_{case_id}.pdf"'}
    )


@router.get("/docx")
def export_docx_endpoint(case_id: str = Query(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    docx_bytes = generate_docx_bytes(case)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="justicehelper_{case_id}.docx"'}
    )
