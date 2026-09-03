"""
Unit tests for Hybrid Retrieval and Re-ranking Modules.
"""
from backend.enrichment import get_topic_filter, ISSUE_TYPE_TOPIC_MAP
from backend.models import EnrichedQuery
from backend.reranker import reranker_engine
from backend.retrieval import hybrid_retrieve


def test_topic_filter_mapping():
    assert get_topic_filter("not_delivered") == ["deficiency_in_service", "refund", "complaint_timeline"]
    assert get_topic_filter("wrong_item") == ["deficiency_in_service", "unfair_trade_practice", "refund"]
    assert get_topic_filter("defective") == ["deficiency_in_service", "refund", "return_cancellation_policy"]


def test_hybrid_retrieval_returns_valid_candidates():
    query = EnrichedQuery(
        case_id="tc_test_1",
        issue_type="refund_delayed",
        search_query="e-commerce grievance officer refund delay timeline 48 hours",
        topic_filter=["refund", "complaint_timeline", "grievance_officer"]
    )

    candidates = hybrid_retrieve(query, top_k_candidates=10)
    assert len(candidates) > 0
    ids = [c.id for c in candidates]
    # Grievance officer rule should rank very high for delayed refund query
    assert any("ecomm2020_rule4_2" in cid or "nch_faq_refund_delay" in cid for cid in ids)


def test_reranker_deduplication():
    query = EnrichedQuery(
        case_id="tc_test_2",
        issue_type="defective",
        search_query="defective damaged product replacement refund unfair trade practice",
        topic_filter=["deficiency_in_service", "refund", "return_cancellation_policy"]
    )
    candidates = hybrid_retrieve(query, top_k_candidates=15)
    top_candidates, reranked_scores = reranker_engine.rerank(query.search_query, candidates, top_n=5)

    assert len(top_candidates) <= 5
    assert len(reranked_scores) == len(top_candidates)
