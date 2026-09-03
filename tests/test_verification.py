"""
Unit tests for Citation Verification Module.
Implements ARCHITECTURE.md §2.7 and PROMPTS.md §5 tests.
"""
from backend.models import (
    EmailDraft,
    GenerationOutput,
    LegalBasisItem,
    NCHComplaintDraft,
    RetrievalCandidate,
)
from backend.verification import verify_citations


def test_verification_flags_unretrieved_snippet_id():
    """
    Ensure citation verification flags a claim when snippet_id does not exist in retrieved set.
    """
    retrieved_passages = [
        RetrievalCandidate(
            id="cpa2019_sec2_11",
            retrieval_score=0.9,
            retrieval_source="both",
            text="Deficiency in service definition...",
            title="Section 2(11)",
            section_number="Sec 2(11)",
            source_type="act",
            url="https://consumeraffairs.nic.in"
        )
    ]

    # Generation output citing a non-existent snippet ID
    gen_output = GenerationOutput(
        case_id="tc_bad_citation",
        rights_summary="Summary of rights.",
        legal_basis=[
            LegalBasisItem(
                claim="Consumer is entitled to automatic treble damages",
                citation="Consumer Protection Act, 2019, Sec 999(1)",
                snippet_id="cpa2019_sec999_fake"  # Invalid snippet ID
            )
        ],
        draft_email=EmailDraft(subject="Grievance", body="Please refund."),
        draft_nch_complaint=NCHComplaintDraft(
            complainant_details="A", opposite_party_details="B", jurisdiction_note="J",
            facts="F", grounds="G", relief_sought="R", verification_clause="V"
        )
    )

    result = verify_citations(gen_output, retrieved_passages)

    assert result.verified is False
    assert len(result.flags) >= 1
    assert result.flags[0].issue == "citation_not_in_retrieved_set"
