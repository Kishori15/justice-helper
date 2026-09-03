"""
Grounded Generation Module for Rights Summary and Complaint Drafts.
Implements ARCHITECTURE.md §2.6, DATA_SCHEMA.md §5, and PROMPTS.md §3.
"""
from typing import Any, List, Optional

from backend.llm_client import llm_client
from backend.models import (
    CaseObject,
    EmailDraft,
    GenerationOutput,
    LegalBasisItem,
    NCHComplaintDraft,
    RetrievalCandidate,
)
from backend.prompts.generation_prompt import GENERATION_SYSTEM_PROMPT

DEFAULT_DISCLAIMER = (
    "Draft for reference only. Please verify details and adapt to the actual NCH/e-Daakhil form before filing."
)


def format_generation_user_prompt(case: CaseObject, retrieved_passages: List[RetrievalCandidate]) -> str:
    """
    Constructs the exact user turn content specified in PROMPTS.md §3.
    """
    case_json = case.model_dump_json(
        include={
            "case_id",
            "basic_info",
            "order_info",
            "issue",
            "actions_taken",
            "desired_outcome",
            "evidence_available",
        },
        indent=2,
    )

    passage_lines = []
    for p in retrieved_passages:
        passage_lines.append(f"[DOC: {p.id}] {p.source_type.title()}: {p.title} ({p.section_number}): \"{p.text}\"")

    passages_text = "\n\n".join(passage_lines)

    prompt = f"""CASE RECORD:
{case_json}

RETRIEVED PASSAGES:
{passages_text}

Generate the rights summary, legal basis, and both drafts for this case, using only the passages above as the basis for any legal claim."""
    return prompt


def generate_rights_and_drafts(
    case: CaseObject,
    retrieved_passages: List[RetrievalCandidate],
    client: Optional[Any] = None
) -> GenerationOutput:
    """
    Generates grounded rights summary, cited legal claims, seller notice, and NCH draft.
    """
    active_client = client or llm_client
    user_prompt = format_generation_user_prompt(case, retrieved_passages)

    # Single high-stakes LLM call per ARCHITECTURE.md §4.1
    response = active_client.generate_json(
        system_prompt=GENERATION_SYSTEM_PROMPT,
        user_prompt=user_prompt
    )

    # Parse legal_basis items
    legal_basis_items: List[LegalBasisItem] = []
    for item in response.get("legal_basis", []):
        if isinstance(item, dict) and item.get("claim") and item.get("snippet_id"):
            legal_basis_items.append(
                LegalBasisItem(
                    claim=str(item["claim"]),
                    citation=str(item.get("citation", "")),
                    snippet_id=str(item["snippet_id"]),
                )
            )

    # Parse email draft
    email_dict = response.get("draft_email", {})
    draft_email = EmailDraft(
        tone=email_dict.get("tone", "polite_first_notice"),
        subject=email_dict.get("subject", f"Grievance regarding Order - {case.order_info.product_name if case.order_info else ''}"),
        body=email_dict.get("body", "Please find details of my grievance above.")
    )

    # Parse NCH complaint draft
    nch_dict = response.get("draft_nch_complaint", {})
    draft_nch = NCHComplaintDraft(
        complainant_details=nch_dict.get("complainant_details", case.basic_info.name or "Complainant"),
        opposite_party_details=nch_dict.get("opposite_party_details", case.order_info.platform if case.order_info else "Opposite Party"),
        jurisdiction_note=nch_dict.get("jurisdiction_note", "Under jurisdiction of District Consumer Disputes Redressal Commission / NCH"),
        facts=nch_dict.get("facts", case.issue.description if case.issue else "Facts of the dispute"),
        grounds=nch_dict.get("grounds", "Grounds under Consumer Protection Act, 2019"),
        relief_sought=nch_dict.get("relief_sought", f"Full refund of ₹{case.order_info.price_paid if case.order_info else 0} with interest and compensation"),
        enclosures=nch_dict.get("enclosures", ["Invoice", "Payment Proof", "Order Confirmation"]),
        verification_clause=nch_dict.get("verification_clause", "I verify that the contents stated above are true to my knowledge.")
    )

    output = GenerationOutput(
        case_id=case.case_id,
        rights_summary=response.get("rights_summary", "Summary of consumer protection rights."),
        legal_basis=legal_basis_items,
        draft_email=draft_email,
        draft_nch_complaint=draft_nch,
        disclaimer=DEFAULT_DISCLAIMER
    )

    # Update case object state
    case.retrieved_passage_ids = [p.id for p in retrieved_passages]
    case.generation_output = output
    case.status = "generated"

    return output
