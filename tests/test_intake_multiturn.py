"""
Unit tests for Multi-Turn Intake and 3-Round Cap.
Tests backend/intake.py and ARCHITECTURE.md §2.1 logic.
"""
from unittest.mock import MagicMock
from backend.intake import create_new_case, process_intake_message


def test_intake_single_turn_complete():
    case = create_new_case(user_name="Anita")
    mock_client = MagicMock()
    mock_client.generate_json.return_value = {
        "extracted_fields": {
            "order_info": {"platform": "Amazon", "product_name": "Headphones", "price_paid": 2999.0},
            "issue": {"issue_type": "defective", "description": "Left ear speaker not working", "expected_resolution": "Full refund"}
        },
        "follow_up_question": None
    }

    reply, updated_case = process_intake_message(
        case=case,
        user_message="I bought headphones worth 2999 on Amazon and they are defective.",
        client=mock_client
    )

    assert updated_case.status == "issue_classified"
    assert updated_case.order_info.platform == "Amazon"
    assert updated_case.order_info.product_name == "Headphones"
    assert updated_case.order_info.price_paid == 2999.0
    assert updated_case.issue.issue_type == "defective"


def test_intake_multi_turn_capping():
    case = create_new_case(user_name="Vikas")
    mock_client = MagicMock()

    # Turn 1: Only platform extracted
    mock_client.generate_json.return_value = {
        "extracted_fields": {"order_info": {"platform": "Flipkart", "product_name": "", "price_paid": 0.0}},
        "follow_up_question": "What product did you order and what was the price?"
    }
    reply1, case = process_intake_message(case, "I ordered something on Flipkart.", client=mock_client)
    assert case.intake_round == 1
    assert case.status == "intake_in_progress"

    # Turn 2: Product extracted, price and issue still missing
    mock_client.generate_json.return_value = {
        "extracted_fields": {"order_info": {"platform": "Flipkart", "product_name": "Watch", "price_paid": 0.0}},
        "follow_up_question": "What was the price and what issue occurred?"
    }
    reply2, case = process_intake_message(case, "It was a Watch.", client=mock_client)
    assert case.intake_round == 2
    assert case.status == "intake_in_progress"

    # Turn 3: 3rd follow-up asked
    mock_client.generate_json.return_value = {
        "extracted_fields": {"order_info": {"platform": "Flipkart", "product_name": "Watch", "price_paid": 0.0}},
        "follow_up_question": "What was the price paid?"
    }
    reply3, case = process_intake_message(case, "It was never delivered.", client=mock_client)
    assert case.intake_round == 3
    assert case.status == "intake_in_progress"

    # Turn 4: User responds to 3rd follow-up -> 3-round cap reached, no more questions asked!
    mock_client.generate_json.return_value = {
        "extracted_fields": {"order_info": {"platform": "Flipkart", "product_name": "Watch", "price_paid": 0.0}},
        "follow_up_question": "What was the price paid?"
    }
    reply4, case = process_intake_message(case, "Still missing price", client=mock_client)
    assert case.intake_round == 3
    assert case.status in ["intake_completed", "issue_classified"]
    assert "captured your details" in reply4.lower()


def test_null_enum_field_resilience():
    case = create_new_case(user_name="Siddharth")
    mock_client = MagicMock()
    # LLM returns null for refund_type, delivery_status, payment_mode
    mock_client.generate_json.return_value = {
        "extracted_fields": {
            "order_info": {
                "platform": "Amazon",
                "product_name": "Shoes",
                "price_paid": 1200.0,
                "delivery_status": None,
                "payment_mode": None
            },
            "issue": {"issue_type": "wrong_item", "description": "Received wrong size", "expected_resolution": "Refund"},
            "desired_outcome": {
                "refund_type": None,
                "refund_amount": None
            }
        },
        "follow_up_question": None
    }

    reply, updated_case = process_intake_message(case, "Wrong shoes sent", client=mock_client)

    assert updated_case.status == "issue_classified"
    assert updated_case.desired_outcome.refund_type == "full"
    assert updated_case.order_info.delivery_status == "unknown"
    assert updated_case.order_info.payment_mode == "other"
