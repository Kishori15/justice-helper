"""
Integration tests for FastAPI Backend API Routes.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import BasicInfo, CaseObject, IssueDetails, OrderInfo
from backend.db import save_case, delete_case


client = TestClient(app)


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["app"] == "JusticeHelper"


def test_case_lifecycle_and_export():
    case_id = "c_test_lifecycle_1"
    # Seed a case
    case = CaseObject(
        case_id=case_id,
        basic_info=BasicInfo(name="Anil Verma"),
        order_info=OrderInfo(platform="Amazon", product_name="Bluetooth Speaker", price_paid=1599.0),
        issue=IssueDetails(issue_type="defective", description="Speaker won't charge", expected_resolution="Full refund"),
        retrieved_passage_ids=["cpa2019_sec2_47", "ecomm2020_rule6_2"]
    )
    save_case(case)

    # 1. Get Case
    res = client.get(f"/api/case?case_id={case_id}")
    assert res.status_code == 200
    assert res.json()["case_id"] == case_id

    # 2. Get Evidence Checklist
    res_chk = client.get(f"/api/checklist?case_id={case_id}")
    assert res_chk.status_code == 200
    chk_json = res_chk.json()
    assert len(chk_json["checklist"]) > 0
    # Check platform substitution
    assert any("Amazon" in item["how_to"] for item in chk_json["checklist"])

    # 3. Retrieve
    res_ret = client.post("/api/retrieve", json={"case_id": case_id})
    assert res_ret.status_code == 200
    assert len(res_ret.json()["candidates"]) > 0

    # 4. Export PDF
    res_pdf = client.get(f"/api/export/pdf?case_id={case_id}")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 0

    # 5. Export DOCX
    res_docx = client.get(f"/api/export/docx?case_id={case_id}")
    assert res_docx.status_code == 200
    assert len(res_docx.content) > 0

    # 6. Delete Case
    res_del = client.delete(f"/api/case?case_id={case_id}")
    assert res_del.status_code == 200
    assert res_del.json()["deleted"] is True
