"""
Query Understanding & Enrichment Module.
Implements ARCHITECTURE.md §2.2, DATA_SCHEMA.md §2, and CORPUS.md §4.
"""
from typing import Any, Dict, List, Optional
import json

from backend.models import CaseObject, EnrichedQuery, IssueType
from backend.prompts.enrichment_prompt import ENRICHMENT_SYSTEM_PROMPT

# Static issue-type to controlled topics mapping per CORPUS.md §4
ISSUE_TYPE_TOPIC_MAP: Dict[str, List[str]] = {
    "not_delivered": ["deficiency_in_service", "refund", "complaint_timeline"],
    "wrong_item": ["deficiency_in_service", "unfair_trade_practice", "refund"],
    "defective": ["deficiency_in_service", "refund", "return_cancellation_policy"],
    "refund_not_received": ["refund", "grievance_officer", "complaint_timeline"],
    "refund_delayed": ["refund", "complaint_timeline", "grievance_officer"],
}

# Fallback statutory keyword queries if LLM is unavailable or for deterministic baseline
DEFAULT_SEARCH_QUERIES: Dict[str, str] = {
    "not_delivered": "Consumer Protection Act deficiency in service e-commerce delivery timeline refund",
    "wrong_item": "Consumer Protection Act unfair trade practice wrong goods replacement refund return",
    "defective": "Consumer Protection Act defective goods deficiency in service return take back refund",
    "refund_not_received": "Consumer Protection e-commerce rules grievance officer refund turnaround time non-receipt",
    "refund_delayed": "Consumer Protection e-commerce rules grievance officer refund delay timeline interest compensation",
}


def get_topic_filter(issue_type: str) -> List[str]:
    """
    Returns controlled vocabulary topics for a given issue type per CORPUS.md §4.
    """
    return ISSUE_TYPE_TOPIC_MAP.get(issue_type, ["refund", "deficiency_in_service"])


def enrich_query(case: CaseObject, llm_client: Optional[Any] = None) -> EnrichedQuery:
    """
    Produces EnrichedQuery object from CaseObject.
    Uses LLM with enrichment_prompt.py if llm_client provided, otherwise deterministic extraction.
    Topic filter is strictly looked up from static table per CORPUS.md §4.
    """
    issue_type: IssueType = case.issue.issue_type if case.issue else "refund_delayed"
    topic_filter = get_topic_filter(issue_type)

    entities: Dict[str, Any] = {}
    if case.order_info:
        if case.order_info.platform:
            entities["platform"] = case.order_info.platform
        if case.order_info.price_paid:
            entities["amount"] = case.order_info.price_paid
        if case.order_info.product_name:
            entities["product"] = case.order_info.product_name

    search_query = DEFAULT_SEARCH_QUERIES.get(issue_type, "e-commerce refund consumer rights CPA 2019")

    if llm_client is not None:
        try:
            case_json_str = case.model_dump_json(include={"case_id", "order_info", "issue", "actions_taken", "desired_outcome"})
            user_prompt = f"CASE RECORD:\n{case_json_str}\n\nProduce the search query and entities JSON."
            response = llm_client.generate_json(
                system_prompt=ENRICHMENT_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            if isinstance(response, dict):
                if response.get("search_query"):
                    search_query = str(response["search_query"]).strip()
                if isinstance(response.get("entities"), dict):
                    entities.update(response["entities"])
        except Exception as e:
            # Fall back gracefully to deterministic search query without breaking pipeline
            print(f"Warning: LLM enrichment failed ({e}), using default statutory query.")

    return EnrichedQuery(
        case_id=case.case_id,
        issue_type=issue_type,
        entities=entities,
        search_query=search_query,
        topic_filter=topic_filter
    )
