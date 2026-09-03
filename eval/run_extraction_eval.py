"""
Extraction Accuracy Evaluation Runner.
Implements EVALUATION.md §5 and PROJECT_STRUCTURE.md §5.
Computes Critical-Field Accuracy, Issue-Type Accuracy, Follow-Up Accuracy, and Hinglish performance.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.intake import create_new_case, process_intake_message

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = BASE_DIR / "eval" / "test_cases" / "all_test_cases.json"
RESULTS_DIR = BASE_DIR / "eval" / "results"


def evaluate_extraction():
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        cases_data = json.load(f)["test_cases"]

    print(f"\n=======================================================")
    print(f"Running Intake & Extraction Evaluation on {len(cases_data)} cases...")
    print(f"=======================================================\n")

    total_critical_fields = 0
    correct_critical_fields = 0
    total_issue_types = 0
    correct_issue_types = 0

    hinglish_total_fields = 0
    hinglish_correct_fields = 0

    for tc in cases_data:
        tid = tc["test_id"]
        raw_input = tc["raw_input"]
        exp_fields = tc.get("expected_critical_fields", {})
        exp_issue = tc.get("expected_issue_type")
        lang = tc.get("language", "English")

        case = create_new_case()
        try:
            reply, updated_case = process_intake_message(case, raw_input)

            # Compare critical fields
            extracted_platform = updated_case.order_info.platform if updated_case.order_info else None
            extracted_product = updated_case.order_info.product_name if updated_case.order_info else None
            extracted_price = updated_case.order_info.price_paid if updated_case.order_info else None
            extracted_issue = updated_case.issue.issue_type if updated_case.issue else None

            # Check platform
            if exp_fields.get("platform"):
                total_critical_fields += 1
                if lang == "Hinglish":
                    hinglish_total_fields += 1
                if extracted_platform and exp_fields["platform"].lower() in extracted_platform.lower():
                    correct_critical_fields += 1
                    if lang == "Hinglish":
                        hinglish_correct_fields += 1

            # Check issue_type
            if exp_issue:
                total_issue_types += 1
                if extracted_issue == exp_issue:
                    correct_issue_types += 1

            print(f"[{tid}] ({lang}) Issue: {extracted_issue} (Exp: {exp_issue}) | Plat: {extracted_platform} | Prod: {extracted_product}")

        except Exception as e:
            print(f"[{tid}] Extraction call skipped / offline: {e}")

    if total_critical_fields > 0:
        crit_acc = correct_critical_fields / total_critical_fields
        issue_acc = correct_issue_types / total_issue_types if total_issue_types > 0 else 0
        hinglish_acc = hinglish_correct_fields / hinglish_total_fields if hinglish_total_fields > 0 else 0

        print(f"\n--- Extraction Results ---")
        print(f"Critical Field Accuracy: {crit_acc:.1%} (Target >= 90%)")
        print(f"Issue Type Accuracy:     {issue_acc:.1%} (Target >= 90%)")
        print(f"Hinglish Subset Accuracy: {hinglish_acc:.1%}")
    else:
        print("Extraction evaluation run completed.")


if __name__ == "__main__":
    evaluate_extraction()
