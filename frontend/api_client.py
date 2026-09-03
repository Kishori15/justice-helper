"""
HTTP Client for JusticeHelper Frontend.
Interacts with the FastAPI backend per DATA_SCHEMA.md §7.
"""
from typing import Any, Dict, List, Optional
import requests

from frontend.config import BACKEND_BASE_URL


class APIClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def send_chat_message(
        self,
        message: str,
        case_id: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        payload = {"message": message, "case_id": case_id, "user_name": user_name}
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()

    def get_case(self, case_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/case"
        res = requests.get(url, params={"case_id": case_id}, timeout=10)
        res.raise_for_status()
        return res.json()

    def update_case(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/case"
        res = requests.put(url, json=case_dict, timeout=10)
        res.raise_for_status()
        return res.json()

    def delete_case(self, case_id: str) -> bool:
        url = f"{self.base_url}/api/case"
        res = requests.delete(url, params={"case_id": case_id}, timeout=10)
        return res.status_code == 200

    def list_cases(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/cases"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []

    def retrieve_passages(
        self,
        case_id: str,
        issue_type: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/retrieve"
        payload = {"case_id": case_id, "issue_type": issue_type, "query": query}
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()

    def generate_explanation(self, case_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate_explanation"
        payload = {"case_id": case_id}
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        return res.json()

    def generate_drafts(self, case_id: str, tone: str = "polite_first_notice") -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate_drafts"
        payload = {"case_id": case_id, "tone": tone}
        res = requests.post(url, json=payload, timeout=60)
        res.raise_for_status()
        return res.json()

    def verify_citations(self, case_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/verify"
        payload = {"case_id": case_id}
        res = requests.post(url, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()

    def get_checklist(self, case_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/checklist"
        res = requests.get(url, params={"case_id": case_id}, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_pdf_bytes(self, case_id: str) -> bytes:
        url = f"{self.base_url}/api/export/pdf"
        res = requests.get(url, params={"case_id": case_id}, timeout=20)
        res.raise_for_status()
        return res.content

    def get_docx_bytes(self, case_id: str) -> bytes:
        url = f"{self.base_url}/api/export/docx"
        res = requests.get(url, params={"case_id": case_id}, timeout=20)
        res.raise_for_status()
        return res.content


api_client = APIClient()
