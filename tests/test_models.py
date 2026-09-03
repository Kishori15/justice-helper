"""
Unit tests for Pydantic Models and Validation Rules.
Implements tests for DATA_SCHEMA.md §8 rules.
"""
import pytest
from pydantic import ValidationError
from backend.models import (
    BasicInfo,
    CaseObject,
    CorpusEntry,
    EvidenceChecklistItem,
    LegalBasisItem,
    OrderInfo,
    IssueDetails,
    DesiredOutcome
)


def test_valid_corpus_entry():
    entry = CorpusEntry(
        id="test_entry_1",
        source_type="act",
        source_name="Consumer Protection Act, 2019",
        title="Sec 2(7)",
        section_number="Sec 2(7)",
        topics=["consumer_definition", "rights"],
        jurisdiction="India",
        url="https://consumeraffairs.nic.in",
        text="Sample text of the section",
        last_verified="2026-08-01"
    )
    assert entry.id == "test_entry_1"
    assert "rights" in entry.topics


def test_invalid_topic_in_corpus_entry():
    with pytest.raises(ValidationError):
        CorpusEntry(
            id="bad_entry",
            source_type="act",
            source_name="CPA",
            title="Title",
            section_number="Sec 1",
            topics=["unknown_topic_not_in_controlled_vocab"],
            jurisdiction="India",
            url="https://example.com",
            text="Text",
            last_verified="2026-08-01"
        )


def test_order_info_negative_price():
    with pytest.raises(ValidationError):
        OrderInfo(
            platform="Amazon",
            product_name="Phone",
            price_paid=-500.0
        )


def test_issue_details_invalid_type():
    with pytest.raises(ValidationError):
        IssueDetails(
            issue_type="warranty_expired",  # Not in the 5 supported refund issue types
            description="Broken",
            expected_resolution="Refund"
        )


def test_case_object_instantiation():
    case = CaseObject(
        case_id="c_12345678",
        basic_info=BasicInfo(name="Rahul Sharma", city="Delhi"),
        order_info=OrderInfo(platform="Flipkart", product_name="Shoes", price_paid=2500.0),
        issue=IssueDetails(issue_type="not_delivered", description="Never arrived", expected_resolution="Full refund"),
        retrieved_passage_ids=["cpa2019_sec2_11"]
    )
    assert case.case_id == "c_12345678"
    assert case.status == "intake_in_progress"
    assert case.order_info.price_paid == 2500.0
