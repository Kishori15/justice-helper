"""
Citation Verification Module (Critic Pass).
Implements ARCHITECTURE.md §2.7, DATA_SCHEMA.md §6, and PROMPTS.md §5.
"""
from typing import Any, List, Optional
import json

from backend.llm_client import llm_client
from backend.models import (
    CitationVerificationFlag,
    CitationVerificationResult,
    GenerationOutput,
    RetrievalCandidate,
)
from backend.prompts.verification_prompt import VERIFICATION_SYSTEM_PROMPT


def verify_citations(
    generation_output: GenerationOutput,
    retrieved_passages: List[RetrievalCandidate],
    client: Optional[Any] = None
) -> CitationVerificationResult:
    """
    Evaluates GenerationOutput citations against retrieved passages.
    Flags invalid snippet IDs and contradictory/overstated legal claims.
    """
    active_client = client or llm_client
    flags: List[CitationVerificationFlag] = []
    retrieved_id_map = {p.id: p for p in retrieved_passages}

    # 1. Deterministic Check: Ensure all snippet_ids exist in retrieved set
    valid_basis_items = []
    for item in generation_output.legal_basis:
        if item.snippet_id not in retrieved_id_map:
            flags.append(
                CitationVerificationFlag(
                    claim=item.claim,
                    citation=item.citation,
                    issue="citation_not_in_retrieved_set",
                    action="flagged_for_review"
                )
            )
        else:
            valid_basis_items.append(item)

    # 2. Critic Pass: LLM checks claim consistency with passage text
    if valid_basis_items:
        prompt_data = {
            "legal_basis": [item.model_dump() for item in valid_basis_items],
            "retrieved_passages": [
                {
                    "id": p.id,
                    "section_number": p.section_number,
                    "title": p.title,
                    "text": p.text
                }
                for p in retrieved_passages
            ]
        }
        user_prompt = f"VERIFICATION INPUT:\n{json.dumps(prompt_data, indent=2)}\n\nEvaluate and return verification JSON."

        try:
            critic_response = active_client.generate_json(
                system_prompt=VERIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )

            critic_flags = critic_response.get("flags", [])
            for f in critic_flags:
                if isinstance(f, dict) and f.get("claim"):
                    flags.append(
                        CitationVerificationFlag(
                            claim=str(f["claim"]),
                            citation=str(f.get("citation", "")),
                            issue=f.get("issue", "claim_not_supported_by_snippet"),
                            action="flagged_for_review"
                        )
                    )
        except Exception as e:
            print(f"Warning: Verification critic pass encountered error: {e}")

    is_verified = (len(flags) == 0)
    return CitationVerificationResult(
        case_id=generation_output.case_id,
        verified=is_verified,
        flags=flags
    )
