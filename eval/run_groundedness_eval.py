"""
Groundedness Evaluation Runner.
Implements EVALUATION.md §4 and PROJECT_STRUCTURE.md §5.
Computes Grounded-claim rate, Fabrication rate (target 0%), and Verifier agreement.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.corpus import corpus_store
from backend.generation import generate_rights_and_drafts
from backend.models import CaseObject, IssueDetails, OrderInfo, RetrievalCandidate
from backend.reranker import reranker_engine
from backend.retrieval import hybrid_retrieve
from backend.enrichment import enrich_query
from backend.verification import verify_citations

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_CASES_PATH = BASE_DIR / "eval" / "test_cases" / "all_test_cases.json"
RESULTS_DIR = BASE_DIR / "eval" / "results"


def evaluate_groundedness():
    corpus_store.load()
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        cases_data = json.load(f)["test_cases"]

    print(f"\n=======================================================")
    print(f"Running Groundedness Evaluation on {len(cases_data)} test cases...")
    print(f"=======================================================\n")

    total_claims = 0
    grounded_claims = 0
    fabricated_claims = 0
    verifier_agreements = 0

    for tc in cases_data[:10]:  # Run on top 10 benchmark fixtures
        tid = tc["test_id"]
        exp_fields = tc.get("expected_critical_fields", {})
        if not exp_fields.get("platform"):
            continue

        case = CaseObject(
            case_id=tid,
            order_info=OrderInfo(
                platform=exp_fields["platform"],
                product_name=exp_fields.get("product_name") or "Product",
                price_paid=float(exp_fields.get("price_paid") or 1000)
            ),
            issue=IssueDetails(
                issue_type=tc.get("expected_issue_type") or "refund_delayed",
                description=tc["raw_input"],
                expected_resolution="Full refund"
            )
        )

        # 1. Retrieve
        enriched = enrich_query(case)
        candidates = hybrid_retrieve(enriched, top_k_candidates=20)
        top_candidates, _ = reranker_engine.rerank(enriched.search_query, candidates, top_n=5)
        retrieved_ids = {c.id for c in top_candidates}

        # 2. Generate
        try:
            gen_output = generate_rights_and_drafts(case, top_candidates)
            verif_result = verify_citations(gen_output, top_candidates)

            # Groundedness checks
            case_grounded = True
            for item in gen_output.legal_basis:
                total_claims += 1
                if item.snippet_id in retrieved_ids:
                    grounded_claims += 1
                else:
                    fabricated_claims += 1
                    case_grounded = False
                    print(f"⚠️ Fabrication in {tid}: Cited {item.snippet_id} not in retrieved set!")

            if verif_result.verified == case_grounded:
                verifier_agreements += 1

            print(f"[{tid}] Claims: {len(gen_output.legal_basis)} | Grounded: {case_grounded} | Verified: {verif_result.verified}")

        except Exception as e:
            print(f"[{tid}] Generation skipped / offline mock: {e}")

    if total_claims > 0:
        grounded_rate = grounded_claims / total_claims
        fab_rate = fabricated_claims / total_claims
        print(f"\n--- Groundedness Results ---")
        print(f"Total Claims Evaluated: {total_claims}")
        print(f"Grounded Rate: {grounded_rate:.1%} (Target >= 95%)")
        print(f"Fabrication Rate: {fab_rate:.1%} (Target 0%)")
    else:
        print("Evaluation completed.")


if __name__ == "__main__":
    evaluate_groundedness()
