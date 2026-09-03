"""
Evidence Checklist Module (Non-LLM local lookup).
Implements ARCHITECTURE.md §2.6a, DATA_SCHEMA.md §4, and PROMPTS.md §4.
Deterministic, instant, and free from LLM call quota.
"""
from typing import List, Optional
from backend.models import EvidenceChecklist, EvidenceChecklistItem, IssueType

# Base checklist definitions
CHECKLIST_DEFINITIONS = [
    {
        "item": "Order confirmation with Order ID and date",
        "how_to": "Check your email/SMS inbox for the original order confirmation from {platform}.",
        "applies_to": ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"],
    },
    {
        "item": "Tax invoice / purchase receipt",
        "how_to": "Go to Your Orders on {platform} → select order → Download Invoice / Bill.",
        "applies_to": ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"],
    },
    {
        "item": "Proof of payment (UPI ID / Bank Statement)",
        "how_to": "Find the transaction reference in your UPI app (GPay/PhonePe/Paytm) or bank account statement.",
        "applies_to": ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"],
    },
    {
        "item": "Customer support communications and ticket IDs",
        "how_to": "Take screenshots of chat history, support emails, or ticket numbers issued by {platform} support.",
        "applies_to": ["not_delivered", "wrong_item", "defective", "refund_not_received", "refund_delayed"],
    },
    {
        "item": "Delivery tracking status screenshot",
        "how_to": "Go to {platform} tracking page showing the original estimated delivery date and non-delivery status.",
        "applies_to": ["not_delivered"],
    },
    {
        "item": "Photos of wrong item received and shipping label",
        "how_to": "Take clear photos of the incorrect product and the outer courier packaging showing the shipping label.",
        "applies_to": ["wrong_item"],
    },
    {
        "item": "Photos / video evidence of product defect or damage",
        "how_to": "Take clear close-up photos and a short video demonstrating the defect, damage, or malfunction.",
        "applies_to": ["defective"],
    },
    {
        "item": "Platform refund initiation confirmation screenshot",
        "how_to": "Go to Your Orders on {platform} → select order → Track Refund / Refund Summary showing initiated amount.",
        "applies_to": ["refund_not_received", "refund_delayed"],
    },
    {
        "item": "Bank statement confirming non-receipt of refund",
        "how_to": "Download your bank statement covering the period from refund initiation date to present date showing no credit.",
        "applies_to": ["refund_not_received", "refund_delayed"],
    },
]


def generate_checklist(case_id: str, issue_type: IssueType, platform: Optional[str] = None) -> EvidenceChecklist:
    """
    Generates a tailored evidence checklist for the given issue_type and platform.
    Uses platform string substitution without LLM calls.
    """
    platform_name = platform.strip() if platform and platform.strip() else "the e-commerce platform"
    items: List[EvidenceChecklistItem] = []

    for defn in CHECKLIST_DEFINITIONS:
        if issue_type in defn["applies_to"]:
            formatted_how_to = defn["how_to"].format(platform=platform_name)
            items.append(
                EvidenceChecklistItem(
                    item=defn["item"],
                    how_to=formatted_how_to,
                    applies_to=defn["applies_to"],
                    checked=False
                )
            )

    return EvidenceChecklist(case_id=case_id, checklist=items)
