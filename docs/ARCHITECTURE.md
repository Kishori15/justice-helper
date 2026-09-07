# ARCHITECTURE.md
## JusticeHelper — System Architecture

**Scope:** Indian e-commerce refund disputes only.
**Core principle:** Modern, non-agentic RAG. Every component below is a fixed pipeline stage — no autonomous planning, no tool-calling loops, no multi-step agent decisions.

---

## 1. High-Level Flow

```
User (Hindi/English/Hinglish text)
        │
        ▼
[1] Intake & Structured Extraction
        │
        ▼
[2] Query Understanding & Enrichment
        │
        ▼
[3] Hybrid Retrieval (keyword + vector + metadata)
        │
        ▼
[4] Re-ranking & Deduplication
        │
        ▼
[5] Grounded Generation (rights summary + drafts)
        │
        ▼
[6] Citation Verification (optional second pass)
        │
        ▼
[7] Review UI → Export (PDF/DOCX)
```

Each numbered stage corresponds to a module below. Data flows strictly forward; no stage calls back into an earlier one autonomously. (Evidence checklist assembly runs alongside stage [5] as a local, non-LLM lookup — see §2.6a.)

---

## 2. Component Breakdown

### 2.1 Intake & Structured Extraction Module
**Input:** Raw user text (Hindi/English/Hinglish), conversational follow-ups.
**Output:** Structured case object (JSON).

- Multi-turn conversational extraction (function-calling / JSON-schema constrained output) maps free text into the case schema across 1 to 4 turns: basic info, order info, issue type, actions taken, desired outcome, evidence availability (see `DATA_SCHEMA.md`).
- CRITICAL fields are: `issue_type`, `platform`, `product_name`, `price_paid`.
- If any critical fields are missing after a user message, the module generates a single, natural, conversational follow-up question asking for all remaining missing critical fields together.
- Clarifying follow-up rounds are capped at a maximum of 3 rounds. If all critical fields are obtained earlier, intake completes immediately. If fields remain missing after 3 rounds, the module sets `follow_up_question` to `null`, updates status to `intake_completed`, and transitions to the Case Summary screen for manual completion.
- This module owns all conversational state for a session; it does not touch the legal corpus.

### 2.2 Query Understanding & Enrichment Module
**Input:** Structured case object.
**Output:** Enriched retrieval query object.

- Classifies issue type into one of the five supported categories (not_delivered, wrong_item, defective, refund_not_received, refund_delayed).
- Extracts entities relevant to retrieval (platform, refund status, days elapsed).
- Generates a domain-specific search string in English (e.g., "refund delay e-commerce rules grievance officer timeline"), regardless of the input language.
- Output schema:
```json
{
  "issue_type": "refund_delayed",
  "entities": {"platform": "Flipkart", "days_since_refund_initiated": 12},
  "search_query": "CPA 2019 refund delay e-commerce rules grievance officer timeline"
}
```
- This is a single deterministic preprocessing call — not an agent decision loop.

### 2.3 Legal Corpus & Indexing Layer
**Static data layer**, built once and updated periodically (not at query time).

- **Sources:** Consumer Protection Act 2019 (selected sections), Consumer Protection (E-Commerce) Rules 2020, NCH guidelines/FAQs.
- **Structure:** Each law is decomposed into logical units (Act → Chapter → Section; Rules → Rule → Clause) rather than fixed-size text chunks.
- **Indexing levels:**
  - Section-level index — for precise citation.
  - Chapter/group-level index — for parent context when a section is too short to stand alone.
- **Storage:**
  - Vector DB (FAISS or Chroma) — embeddings per unit.
  - Keyword index (BM25 via Elasticsearch/OpenSearch, or an in-memory BM25 implementation) — for exact term/section-number matches.
  - Metadata store — `source_type`, `title`, `section_number`, `topics`, `jurisdiction`, `url`, attached to every unit in both indexes.
- See `CORPUS.md` for the full schema and source list.

### 2.4 Hybrid Retrieval Module
**Input:** Enriched query object from 2.2.
**Output:** ~20–50 candidate passages.

- Runs three retrieval signals in parallel:
  1. Keyword/BM25 search on `title`, `section_number`, `topics`.
  2. Vector similarity search on the embedded `search_query`.
  3. Metadata filter by `issue_type` → mapped `topics` (e.g., `refund_delayed` → `["refund", "ecommerce", "grievance", "timeline"]`).
- Combines results via reciprocal rank fusion (or weighted scoring) into a single ranked candidate list.
- No agentic query rewriting loop — one retrieval pass per case.

### 2.5 Re-ranking & Deduplication Module
**Input:** Candidate passages from 2.4.
**Output:** Top 5–10 high-quality passages.

- Cross-encoder re-ranker (e.g., bge-reranker or ms-marco-style model) scores each (enriched query, candidate passage) pair.
- Deduplication removes near-identical passages, preferring the most complete version of a section.
- Output is the final, small evidence set passed to generation — this is what gets cited.

### 2.6 Grounded Generation Module
**Input:** Structured case object (2.1) + top passages (2.5).
**Output:** Structured JSON containing rights summary, claim-to-citation mapping, and both drafts.

- System prompt enforces:
  - Use only the provided passages for legal claims.
  - Cite `section_number` + `source_type` for every legal claim.
  - Never invent section numbers, rules, or case names.
  - Fall back to "general consumer protection principles suggest..." when a claim isn't directly supported.
- Output schema (illustrative):
```json
{
  "rights_summary": "...",
  "legal_basis": [
    {"claim": "...", "citation": "Consumer Protection Act, 2019, Sec 2(7)", "snippet_id": "DOC1"}
  ],
  "draft_email": "...",
  "draft_nch_complaint": "..."
}
```

### 2.6a Evidence Checklist Module (non-LLM)
**Input:** `issue_type` (from 2.1/2.2), `order_info.platform`.
**Output:** Checklist object (`DATA_SCHEMA.md` §4).

- Runs alongside 2.6, not as part of the LLM generation call. A fixed lookup table maps each `issue_type` to a predefined set of checklist items (order confirmation, invoice, payment proof, prior communication, plus issue-specific items like tracking screenshots or refund-status screenshots), each with a pre-written `how_to` string.
- Platform-specific phrasing (e.g., naming "Flipkart" in a how-to step) is done via simple string substitution, not generation.
- Kept out of the LLM budget deliberately — checklist content is enumerable and doesn't need generation. See `PROMPTS.md` §4 for the full rationale and lookup design.

### 2.7 Citation Verification Module (optional, non-agentic)
**Input:** Generation output (2.6) + the same top passages (2.5).
**Output:** Verified output, or flags on unsupported claims.

- A second LLM pass (a "critic," not an agent) checks:
  - Does every cited `section_number` actually appear in the passed-in passage set?
  - Is the claim text consistent with the cited snippet?
- Flags mismatches for UI display or removal. This module does not re-trigger retrieval or take further action — it only validates.

### 2.8 Review & Export Module
- Presents rights summary, evidence checklist, and both drafts in the UI with inline citations (linking to `url` in metadata).
- User edits drafts directly.
- Export to PDF/DOCX (templated via Jinja2/markdown → document conversion) or copy-to-clipboard.

---

## 3. Data Flow Summary

| Stage | Reads | Writes | Calls LLM? |
|---|---|---|---|
| 2.1 Intake | User text | Structured case JSON | Yes (1–4 calls: 1 initial extraction + up to 3 multi-turn follow-ups) |
| 2.2 Query enrichment | Case JSON | Enriched query JSON | Yes (classification/rewrite) |
| 2.3 Corpus/index | — (static) | — | No |
| 2.4 Hybrid retrieval | Enriched query, indexes | Candidate passages | No |
| 2.5 Re-ranking | Candidates | Top-N passages | No (cross-encoder, not generative) |
| 2.6 Generation | Case JSON + top passages | Rights summary, citations, drafts | Yes (generation) |
| 2.6a Evidence checklist | `issue_type`, platform | Checklist object | No (local lookup) |
| 2.7 Verification | Generation output + top passages | Verified/flagged output | Yes (critic pass) |
| 2.8 Review/export | Verified output | PDF/DOCX/clipboard | No |

---

## 4. Technology Stack (MVP)

This is an all-Python, laptop-runnable stack. Only the LLM calls leave the machine (to Gemini); all retrieval (embeddings, vector search, BM25, re-ranking) runs locally.

| Layer | Choice |
|---|---|
| Frontend | `streamlit` — chat UI, case-summary forms, rights/citations view, evidence checklist, draft review, export buttons |
| Backend | `fastapi` + `uvicorn`, `pydantic` for schema validation |
| LLM (primary) | Google **Gemini API** via `google-generativeai` SDK, with optional key rotation across multiple Gemini API keys to spread quota — issue classification/extraction (JSON mode), grounded generation, optional verification pass |
| LLM (fallback) | Another provider (e.g., **Groq** or **Together AI**) called only on Gemini errors or `429` rate-limit responses — same prompts, same JSON schema, swapped in behind `llm_client.py`'s single interface |
| Embeddings | `sentence-transformers` with `BAAI/bge-small-en-v1.5` (or a multilingual variant, e.g. `bge-m3`, if Hindi support is prioritized) |
| Vector DB | `faiss-cpu` (`IndexFlatIP` or `IndexHNSW`), index persisted to disk |
| Keyword search | `rank-bm25` (or `whoosh`) — lightweight in-process BM25 |
| Re-ranker | `sentence-transformers` cross-encoder — `BAAI/bge-reranker-base` (or `-large` if RAM allows) |
| Templates | `jinja2` for email/complaint draft templates and export HTML |
| Export | `weasyprint` (HTML → PDF), `python-docx` (DOCX) |
| Case/session storage | `sqlite3` (single `cases` table: `case_id`, `created_at`, `user_name`, `structured_data`, `conversation`, `retrieved_passage_ids`, `drafts`), or plain JSON files under `data/cases/{case_id}.json` for a simpler demo setup — either way, deletable per case |

**Notes:**
- Gemini is the primary LLM provider for the main demo. A second provider (Groq/Together, or similar) is wired in only as an error/rate-limit fallback — not for offline use — so the system keeps working if Gemini quota is exhausted mid-demo.
- The legal corpus is stored as JSONL (see `CORPUS.md`), loaded and indexed (FAISS + BM25) once at startup, with an in-memory `passage_id → passage_doc` lookup used by the retrieval and generation modules.
- Development runs as two local processes: `uvicorn main:app --reload` (backend) and `streamlit run app.py` (frontend, `http://localhost:8501`), communicating over `requests`/`httpx`. For deployment beyond a laptop demo, Streamlit can move to Streamlit Cloud (or the same VPS behind Nginx) while FastAPI + the retrieval stack run on a small VPS.
- 8 GB RAM is sufficient with the "small" model variants listed above; swap in the "large"/multilingual variants only if hardware allows.

### 4.1 LLM API Usage & Rate-Limit Strategy

Per complaint case, JusticeHelper makes **3–8 LLM API calls** (depending on clarification turns), not one per pipeline stage:

1. **Intake** — classify issue type and extract structured fields across 1–4 conversational turns (1 initial extraction + up to 3 clarifying follow-up turns; `PROMPTS.md` §1).
2. **Rights/legal explanation** — generate the grounded rights summary and legal basis in a single call.
3. **Drafts** — generate both the email draft and the formal NCH complaint draft together in a single call.
4–5. **Optional** — extra calls only if the user requests a revision/regeneration of a draft.

Everything else in the pipeline — retrieval, re-ranking, evidence checklist assembly, and export — runs on **local open-source models and algorithms** (embeddings, FAISS, BM25, cross-encoder reranker), not the LLM API, and does not count against LLM rate limits.

To stay within free-tier limits during demos:
- **Batching:** related sub-tasks (e.g., rights summary + legal basis) are combined into one call rather than issued separately.
- **Caching:** LLM outputs are cached per `case_id`; re-rendering the UI or re-viewing a case does not trigger new calls.
- **Fallback on error only:** the system calls the fallback provider (Groq/Together) only when Gemini returns an error or a `429` response — never as a default or offline substitute — using the same prompts and JSON schema so output format stays consistent regardless of which provider served the call.

This keeps token usage and request count low enough that a single user case will not hit free-tier limits under normal demo conditions.

---

## 5. Why This Is Not Agentic

Every module above executes **exactly once per case**, in a fixed order, with no component deciding whether to call another module, retry, or take an independent action. There is no planner, no tool-selection step, and no loop where the LLM decides what to do next. Contrast with agentic RAG, which would let the model iteratively decide to re-query, call external tools, or re-plan retrieval steps mid-conversation. JusticeHelper deliberately avoids this to keep the system predictable, auditable, and scoped to a drafting/informational tool rather than an autonomous actor.

---

## 6. Extension Points (deferred, not built in MVP)

- Bilingual (Hindi) generation output.
- Swapping the static pipeline order for a conditional one (e.g., skip retrieval if issue type is unclear) — still non-agentic if implemented as a fixed if/else, not a model-driven decision.
- Direct API integration with e-Daakhil or platform grievance systems (would need careful re-scoping, as this starts to introduce action-taking behavior).
