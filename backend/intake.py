"""
Case Intake and Structured Extraction Module.
Implements ARCHITECTURE.md §2.1 and PROMPTS.md §1.
"""
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone
import uuid

from backend.llm_client import llm_client
from backend.models import (
    ActionsTaken,
    BasicInfo,
    CaseObject,
    ConversationMessage,
    DesiredOutcome,
    EvidenceAvailable,
    IssueDetails,
    OrderInfo,
)
from backend.prompts.intake_prompt import INTAKE_SYSTEM_PROMPT


def create_new_case(user_name: Optional[str] = None) -> CaseObject:
    """
    Initializes a blank CaseObject with a unique case_id.
    """
    case_id = f"c_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    basic_info = BasicInfo(name=user_name) if user_name else BasicInfo()

    return CaseObject(
        case_id=case_id,
        created_at=now_iso,
        updated_at=now_iso,
        status="intake_in_progress",
        basic_info=basic_info
    )


def process_intake_message(
    case: CaseObject,
    user_message: str,
    client: Optional[Any] = None
) -> Tuple[str, CaseObject]:
    """
    Processes a user message in the conversational intake flow.
    Extracts structured fields and checks for critical missing fields.
    Returns (assistant_reply, updated_case).
    """
    active_client = client or llm_client
    now_iso = datetime.now(timezone.utc).isoformat()

    # Append user turn to conversation history
    case.conversation.append(
        ConversationMessage(role="user", text=user_message, timestamp=now_iso)
    )

    # Build conversation context for prompt
    history_lines = []
    for msg in case.conversation:
        history_lines.append(f"{msg.role.upper()}: {msg.text}")
    conversation_text = "\n".join(history_lines)

    # Call LLM for extraction
    response_data = active_client.generate_json(
        system_prompt=INTAKE_SYSTEM_PROMPT,
        user_prompt=f"CONVERSATION HISTORY:\n{conversation_text}\n\nExtract fields and identify if a critical follow-up question is needed."
    )

    extracted = response_data.get("extracted_fields", {})
    follow_up = response_data.get("follow_up_question")

    # Update basic_info if extracted
    if "basic_info" in extracted and isinstance(extracted["basic_info"], dict):
        b = extracted["basic_info"]
        if b.get("name") and not case.basic_info.name:
            case.basic_info.name = b["name"]
        if b.get("contact"):
            case.basic_info.contact = b["contact"]
        if b.get("city"):
            case.basic_info.city = b["city"]
        if b.get("state"):
            case.basic_info.state = b["state"]

    # Update order_info
    if "order_info" in extracted and isinstance(extracted["order_info"], dict):
        o = extracted["order_info"]
        platform = o.get("platform") or (case.order_info.platform if case.order_info else None)
        product_name = o.get("product_name") or (case.order_info.product_name if case.order_info else None)
        price_paid = o.get("price_paid")
        if price_paid is None and case.order_info:
            price_paid = case.order_info.price_paid

        if platform or product_name or (price_paid is not None):
            case.order_info = OrderInfo(
                platform=str(platform or ""),
                order_id=o.get("order_id") or (case.order_info.order_id if case.order_info else None),
                order_date=o.get("order_date") or (case.order_info.order_date if case.order_info else None),
                delivery_date=o.get("delivery_date") or (case.order_info.delivery_date if case.order_info else None),
                delivery_status=o.get("delivery_status") or (case.order_info.delivery_status if case.order_info else "unknown"),
                product_name=str(product_name or ""),
                product_category=o.get("product_category") or (case.order_info.product_category if case.order_info else None),
                price_paid=float(price_paid) if price_paid is not None else 0.0,
                payment_mode=o.get("payment_mode") or (case.order_info.payment_mode if case.order_info else "other"),
                transaction_id=o.get("transaction_id") or (case.order_info.transaction_id if case.order_info else None),
            )

    # Update issue
    if "issue" in extracted and isinstance(extracted["issue"], dict):
        iss = extracted["issue"]
        issue_type = iss.get("issue_type")
        desc = iss.get("description") or user_message
        exp_res = iss.get("expected_resolution") or "Full refund"

        if issue_type and issue_type in ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"]:
            case.issue = IssueDetails(
                issue_type=issue_type,
                description=desc,
                expected_resolution=exp_res
            )
            case.status = "issue_classified"

    # Update desired_outcome
    if "desired_outcome" in extracted and isinstance(extracted["desired_outcome"], dict):
        d = extracted["desired_outcome"]
        case.desired_outcome = DesiredOutcome(
            refund_type=d.get("refund_type", "full"),
            refund_amount=d.get("refund_amount"),
            compensation_requested=bool(d.get("compensation_requested", False)),
            compensation_amount=d.get("compensation_amount"),
            apology_requested=bool(d.get("apology_requested", False))
        )

    # Update actions_taken
    if "actions_taken" in extracted and isinstance(extracted["actions_taken"], dict):
        act = extracted["actions_taken"]
        case.actions_taken.contacted_seller = bool(act.get("contacted_seller", case.actions_taken.contacted_seller))
        case.actions_taken.contacted_platform_support = bool(act.get("contacted_platform_support", case.actions_taken.contacted_platform_support))
        if act.get("ticket_ids"):
            case.actions_taken.ticket_ids = list(set(case.actions_taken.ticket_ids + act["ticket_ids"]))

    # Update evidence_available
    if "evidence_available" in extracted and isinstance(extracted["evidence_available"], dict):
        ev = extracted["evidence_available"]
        for k in ["invoice", "order_confirmation", "payment_proof", "chat_logs", "product_photos"]:
            if k in ev:
                setattr(case.evidence_available, k, bool(ev[k]))

    # Critical fields validation per PROMPTS.md §1
    has_issue = case.issue and case.issue.issue_type
    has_platform = case.order_info and case.order_info.platform
    has_product = case.order_info and case.order_info.product_name
    has_price = case.order_info and case.order_info.price_paid > 0

    if not has_issue:
        reply = follow_up or "Could you please specify what happened with your order (e.g. item not delivered, wrong item, defective item, or delayed refund)?"
    elif not has_platform:
        reply = follow_up or "Which e-commerce platform did you purchase this from (e.g. Amazon, Flipkart, Myntra)?"
    elif not has_product:
        reply = follow_up or "What product did you order?"
    elif not has_price:
        reply = follow_up or "What was the price/amount paid for the order?"
    else:
        reply = (
            f"Thank you. I have recorded your case regarding the {case.order_info.product_name} on {case.order_info.platform} "
            f"(Issue: {case.issue.issue_type.replace('_', ' ').title()}). "
            f"We are ready to fetch your legal rights and draft your grievance notices."
        )

    # Append assistant response to conversation
    case.conversation.append(
        ConversationMessage(role="system", text=reply, timestamp=datetime.now(timezone.utc).isoformat())
    )

    return reply, case
