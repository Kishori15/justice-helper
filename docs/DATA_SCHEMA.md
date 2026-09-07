# DATA_SCHEMA.md
## JusticeHelper — Case Data Model & Inter-Module Schemas

This document defines the data schemas that flow *through* the pipeline — the case record and the JSON objects passed between modules. For the legal corpus schema (the static reference data retrieval reads from), see `CORPUS.md`.

---

## 1. Case Object (canonical record)

This is the single source of truth for a user's case, built incrementally by the Intake module (`ARCHITECTURE.md` §2.1) and read/updated by every later stage. Persisted in SQLite or as `data/cases/{case_id}.json`.

```json
{
  "case_id": "c_2f8a1e",
  "created_at": "2026-08-25T10:15:00Z",
  "updated_at": "2026-08-25T10:22:00Z",
  "status": "draft_generated",
  "intake_round": 0,

  "basic_info": {
    "name": "string | null",
    "contact": "string | null",
    "city": "string | null",
    "state": "string | null"
  },

  "order_info": {
    "platform": "string",
    "order_id": "string | null",
    "order_date": "date | null",
    "delivery_date": "date | null",
    "delivery_status": "delivered | not_delivered | partially_delivered | unknown",
    "product_name": "string",
    "product_category": "string | null",
    "price_paid": "number",
    "payment_mode": "upi | card | net_banking | cod | other",
    "transaction_id": "string | null"
  },

  "issue": {
    "issue_type": "not_delivered | wrong_item | defective | refund_not_received | refund_delayed",
    "description": "string",
    "expected_resolution": "string"
  },

  "actions_taken": {
    "contacted_seller": "boolean",
    "contacted_platform_support": "boolean",
    "ticket_ids": ["string"],
    "communication_log": [
      {"date": "date", "channel": "chat | email | call", "summary": "string"}
    ]
  },

  "desired_outcome": {
    "refund_type": "full | partial",
    "refund_amount": "number | null",
    "compensation_requested": "boolean",
    "compensation_amount": "number | null",
    "apology_requested": "boolean"
  },

  "evidence_available": {
    "invoice": "boolean",
    "order_confirmation": "boolean",
    "payment_proof": "boolean",
    "chat_logs": "boolean",
    "product_photos": "boolean"
  },

  "conversation": [
    {"role": "user | system", "text": "string", "timestamp": "datetime"}
  ],

  "retrieved_passage_ids": ["string"],
  "generation_output": "GenerationOutput object (see §5) | null"
}
```

### Field notes

- `status` tracks pipeline progress: `intake_in_progress → intake_completed → issue_classified → retrieved → generated → verified → exported`.
- `intake_round` tracks the number of clarifying follow-up turns asked so far (0 to 3).
- `issue_type` is strictly required before moving from `intake_completed` to `issue_classified`/`retrieved`.
- `retrieved_passage_ids` stores the exact `id` values (from `CORPUS.md` schema) used for this case — this is what makes the "show which sections were used" transparency requirement in the PRD auditable.
- Any field left `null`/`unknown` after intake should have triggered a follow-up question (`ARCHITECTURE.md` §2.1); only genuinely optional fields (e.g., `compensation_amount` when not requested) should stay null in a completed case.
- `evidence_available` is user self-reported at intake; it is not verified against actual uploaded files unless file upload is implemented.

---

## 2. Enriched Query Object

Produced by the Query Understanding & Enrichment module (`ARCHITECTURE.md` §2.2) from the Case Object. Not persisted long-term — passed directly into retrieval.

```json
{
  "case_id": "c_2f8a1e",
  "issue_type": "refund_delayed",
  "entities": {
    "platform": "Flipkart",
    "amount": 2499,
    "days_since_refund_initiated": 12
  },
  "search_query": "CPA 2019 refund delay e-commerce rules grievance officer timeline",
  "topic_filter": ["refund", "complaint_timeline", "grievance_officer"]
}
```

- `topic_filter` is derived from the issue-type → topic mapping table in `CORPUS.md` §4 — it is looked up, not generated freely by the LLM.

---

## 3. Retrieval Result (candidate + re-ranked passages)

Output of hybrid retrieval (`ARCHITECTURE.md` §2.4) and, after scoring, of re-ranking (§2.5).

```json
{
  "case_id": "c_2f8a1e",
  "candidates": [
    {
      "id": "ecomm2020_rule4_2",
      "retrieval_score": 0.82,
      "retrieval_source": "vector | keyword | both",
      "text": "...",
      "title": "Rule 4(2) — Grievance Officer",
      "section_number": "Rule 4(2)",
      "source_type": "rule",
      "url": "https://..."
    }
  ],
  "reranked": [
    {
      "id": "ecomm2020_rule4_2",
      "rerank_score": 0.94
    }
  ]
}
```

- `candidates` is the ~20–50 item hybrid result set; `reranked` is the trimmed top 5–10 that actually gets passed to generation.
- Fields in each candidate mirror the corpus entry schema in `CORPUS.md` §3 — this object is a retrieval-time projection of those entries, not a separate data model.

---

## 4. Evidence Checklist Object

Produced by a local, non-LLM lookup (`ARCHITECTURE.md` §2.6a) that runs alongside — not as part of — the LLM generation call. Keyed by `issue_type`.

```json
{
  "case_id": "c_2f8a1e",
  "checklist": [
    {
      "item": "Refund status screenshot from platform",
      "how_to": "Go to Your Orders → select order → Track Refund",
      "applies_to": ["refund_not_received", "refund_delayed"],
      "checked": false
    },
    {
      "item": "Bank statement showing no credit",
      "how_to": "Download statement for the period since refund was initiated",
      "applies_to": ["refund_not_received", "refund_delayed"],
      "checked": false
    }
  ]
}
```

- `applies_to` lets the same checklist item be reused across issue types instead of duplicating entries per type.
- `checked` is toggled by the user in the Review UI; it does not affect generation, only UI state.

---

## 5. Generation Output Object

Produced by the Grounded Generation module (`ARCHITECTURE.md` §2.6). This is the schema enforced via the LLM's JSON-mode/function-calling constraint — the model must not deviate from it.

```json
{
  "case_id": "c_2f8a1e",
  "rights_summary": "string — plain-language explanation",
  "legal_basis": [
    {
      "claim": "string — the specific right or obligation being asserted",
      "citation": "Consumer Protection Act, 2019, Sec 2(7)",
      "snippet_id": "cpa2019_sec2_7"
    }
  ],
  "draft_email": {
    "tone": "polite_first_notice | firm_second_notice",
    "subject": "string",
    "body": "string"
  },
  "draft_nch_complaint": {
    "complainant_details": "string",
    "opposite_party_details": "string",
    "jurisdiction_note": "string",
    "facts": "string",
    "grounds": "string — cites legal_basis entries",
    "relief_sought": "string",
    "enclosures": ["string"],
    "verification_clause": "string"
  },
  "disclaimer": "Draft for reference only. Please verify details and adapt to the actual NCH/e-Daakhil form before filing."
}
```

- Every `snippet_id` in `legal_basis` **must** correspond to an `id` present in `retrieved_passage_ids` on the Case Object for that request — this invariant is exactly what the Citation Verification module (`ARCHITECTURE.md` §2.7) checks.
- `disclaimer` is a fixed string, not LLM-generated, inserted by the backend regardless of model output.

---

## 6. Citation Verification Result

Output of the optional verification pass (`ARCHITECTURE.md` §2.7).

```json
{
  "case_id": "c_2f8a1e",
  "verified": true,
  "flags": [
    {
      "claim": "string",
      "citation": "string",
      "issue": "citation_not_in_retrieved_set | claim_not_supported_by_snippet",
      "action": "flagged_for_review | auto_removed"
    }
  ]
}
```

- If `flags` is non-empty, the Review UI must surface the flagged claim(s) to the user rather than silently presenting them as verified fact.

---

## 7. API Request/Response Shapes

These map directly onto the FastAPI endpoints in `ARCHITECTURE.md` and use the objects defined above.

| Endpoint | Request | Response |
|---|---|---|
| `POST /api/chat` | `{ case_id, message }` | `{ reply, updated_case_summary: CaseObject, intake_round: int, is_intake_complete: bool, follow_up_question: string | null }` |
| `POST /api/classify_issue` | `{ case_id, user_text }` | `{ issue_type, extracted_fields }` (partial Case Object) |
| `POST /api/retrieve` | `{ case_id, issue_type, query }` | `RetrievalResult` (§3) |
| `POST /api/generate_explanation` | `{ case_id }` | `{ rights_summary, legal_basis }` (subset of §5) |
| `POST /api/generate_drafts` | `{ case_id }` | `GenerationOutput` (§5) |
| `GET /api/export/pdf?case_id=` | — | PDF file (`application/pdf`) |
| `GET /api/export/docx?case_id=` | — | DOCX file |
| `DELETE /api/case?case_id=` | — | `{ deleted: true }` |

---

## 8. Validation Rules (summary)

- `issue_type` must be one of the five enum values — no free text.
- `price_paid`, `refund_amount`, `compensation_amount` must be non-negative numbers.
- `order_date` ≤ `delivery_date` (if both present) unless `delivery_status = "not_delivered"`.
- Every `snippet_id` referenced anywhere in `GenerationOutput` must exist in `retrieved_passage_ids`.
- `case_id` is immutable once created; all objects above are keyed by it for traceability across the pipeline.

---

## 9. Non-Goals

- This schema does not model multi-user accounts, authentication, or long-term case history beyond a single session/export — out of scope per the PRD's minimal-storage requirement.
- No schema versioning system is defined yet; if the Case Object schema changes, migration handling is deferred to `CHANGELOG.md` once the project has persisted data worth migrating.
