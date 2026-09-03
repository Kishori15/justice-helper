# Product Requirements Document (PRD)
## JusticeHelper — AI-Assisted E-Commerce Refund Complaint Drafting Tool

**Version:** 1.0
**Status:** Draft for final-year project scoping
**Owner:** [Your Name]
**Last Updated:** August 2026

---

## 1. Summary

JusticeHelper is an AI-assisted tool that helps Indian consumers convert a plain-language description of an online shopping refund problem into a structured, source-grounded complaint draft — addressed to (1) the seller/platform grievance channel, and (2) the National Consumer Helpline (NCH) / consumer commission as an escalation path.

The system is scoped **exclusively to e-commerce refund disputes** and is built around a **modern, non-agentic Retrieval-Augmented Generation (RAG) pipeline** grounded in Indian consumer protection law.

---

## 2. Problem Statement

Indian consumers facing e-commerce refund issues (non-delivery, wrong item, defective product, delayed/partial refund) often:

- Don't know their legal rights under the Consumer Protection Act, 2019 and the Consumer Protection (E-Commerce) Rules, 2020.
- Don't know what evidence to collect or how to structure a complaint.
- Face friction writing a clear, effective grievance email or a formal NCH/consumer-commission complaint.

Existing options (NCH, e-Daakhil, Consumer VOICE/CORE, global tools like DoNotPay, corporate legal AI like Harvey) are either static/form-driven, not India-specific, not refund-specific, or built for legal professionals rather than consumers. There is no known AI system combining **Indian law + e-commerce refunds + retrieval-grounded, consumer-friendly drafting**.

---

## 3. Goals and Non-Goals

### Goals
- Let a consumer describe their refund issue in natural language (English/Hindi/Hinglish) and receive a structured case record.
- Ground all legal claims in retrieved, citable sections of Indian statutes/rules — no hallucinated law.
- Generate an evidence checklist tailored to the specific issue type.
- Generate two drafts: (a) a seller/platform grievance message, and (b) an NCH/consumer-commission-style complaint.
- Demonstrate a modern RAG architecture (hybrid retrieval, structured corpus, re-ranking, grounded generation, citation verification) as the core technical contribution.

### Non-Goals (explicitly out of scope)
- No agentic behavior — no autonomous planning, tool-calling loops, or multi-step agent orchestration. This is a retrieval + generation pipeline only.
- No replacements, warranty claims, service disputes, or offline-purchase disputes.
- No live filing/integration with e-Daakhil, NCH, or platform APIs (drafts are for user copy/export only).
- No legal advice or outcome guarantees — informational/drafting aid only.

---

## 4. Target Users

- Indian online shoppers who experienced a refund-related issue and don't know how to escalate it.
- Non-lawyers with low-to-moderate legal literacy; may write in Hinglish.
- Secondary audience: project evaluators / reviewers assessing technical depth of the RAG pipeline.

---

## 5. Scope: Supported Issue Types

1. Item not delivered
2. Wrong item delivered
3. Defective / damaged item
4. Refund initiated but not received
5. Refund partially credited or delayed beyond promised turnaround time (TAT)

---

## 6. User Journey

```
Tell → Understand → Retrieve → Explain → Collect Evidence → Draft → Review → Export
```

1. **Tell** — User describes the issue in free text (Hindi/English/Hinglish).
2. **Understand** — LLM extracts structured case fields (see Section 7).
3. **Retrieve** — RAG module fetches relevant legal passages based on issue type.
4. **Explain** — System presents a plain-language "Your Rights" summary with citations.
5. **Collect Evidence** — System shows an issue-specific evidence checklist with how-to tips.
6. **Draft** — System generates a seller/platform message and an NCH-style complaint draft.
7. **Review** — User edits the draft; optional human reviewer check for demo cases.
8. **Export** — User downloads as PDF/DOCX or copies text.

---

## 7. Functional Requirements

### 7.1 Case Intake & Structured Extraction
The system must extract the following fields from free-text input, asking follow-up questions only for missing critical fields:

- **Basic info:** name, contact (optional), city/state
- **Order info:** platform, order ID, order date, delivery date/status, product, price, payment mode, transaction ID
- **Issue details:** issue type (single/multi-select from Section 5), free-text description, expected resolution
- **Actions already taken:** prior contact with seller/platform, ticket/complaint IDs, dates and summaries
- **Desired outcome:** refund amount (full/partial), compensation, apology/explanation
- **Evidence available:** invoice, order confirmation, payment proof, chat logs, product photos (yes/no per item)

### 7.2 RAG Module (core requirement)
The RAG module must **not** be a naive "chunk + embed + top-k" pipeline. Required components:

| Stage | Requirement |
|---|---|
| Query understanding | Classify issue type, extract entities, generate a domain-specific search query from the enriched case data |
| Corpus structure | Legal corpus indexed as logical units (Act → Chapter → Section; Rule → Clause) with metadata: `source_type`, `title`, `section_number`, `topics`, `jurisdiction`, `url` |
| Retrieval | Hybrid: keyword/BM25 + vector similarity + metadata filtering (by issue type/topic) |
| Hierarchy | Section-level and chapter-level indexing to avoid fixed-size chunking cutting across legal structure |
| Re-ranking | Cross-encoder re-ranker (e.g., bge-reranker) to reduce 20–50 candidates to top 5–10, plus deduplication |
| Generation | LLM constrained to cite only retrieved passages; must not invent section numbers or provisions; must qualify unsupported claims as "general principles" |
| Output format | Structured JSON: claim ↔ citation ↔ source snippet ID |
| Verification (optional) | A second-pass check confirming every cited section exists in the retrieved set and is consistent with the claim |

### 7.3 Legal Corpus (content requirement)
Curated corpus limited to:
- Consumer Protection Act, 2019 (relevant sections — definitions, rights, redressal, unfair trade practice)
- Consumer Protection (E-Commerce) Rules, 2020 (duties of e-commerce entities, grievance officer, refund/return disclosures, timelines)
- National Consumer Helpline (NCH) guidelines and FAQs

Stored as JSONL/markdown with fields: `id`, `source_type`, `title`, `section_number`, `topics`, `text`, `url`.

### 7.4 Evidence Checklist Generation
Per issue type, generate a tailored checklist (see source doc for full per-type lists), covering: order confirmation, invoice, payment proof, prior communication, and issue-specific items (tracking screenshots, defect photos, refund-status screenshots, bank statements).

### 7.5 Draft Generation
Two outputs per case:
1. **Seller/platform message** — subject line, opener, chronological facts, brief legal basis (1–2 lines, cited), demand with deadline, enclosures list, closing. Two tone variants: polite first notice / firm second notice.
2. **NCH/consumer-commission-style complaint** — complainant details, opposite party details, jurisdiction hint, chronological facts, grounds of complaint (cited), relief sought, document list, verification clause. Clearly labeled "draft for reference only."

### 7.6 Export
PDF/DOCX export and copy-to-clipboard for both drafts.

---

## 8. Non-Functional Requirements

- **Groundedness:** Every legal claim in generated output must be traceable to a retrieved snippet; no fabricated section numbers or case law.
- **Language support:** Accept Hindi/English/Hinglish input; output primarily in plain English (bilingual is a stretch goal).
- **Privacy:** Store only minimal session data; provide a "delete my data" option.
- **Transparency:** UI should show which legal sections were retrieved/used for a given case.
- **Disclaimers:** Persistent, visible notice that outputs are informational/drafting aids, not legal advice, and do not guarantee outcomes.

---

## 9. System Architecture (MVP)

- **Frontend:** React/Next.js (or Flask/Django templates), mobile-friendly.
- **Backend:** Python (FastAPI/Flask/Django).
- **LLM:** Primary — Google Gemini API (with optional key rotation across multiple keys); Fallback — another provider (e.g., Groq or Together AI), invoked only on Gemini errors or rate-limit (429) responses. Used for extraction, generation, and structured output (function calling/JSON schema). See `ARCHITECTURE.md` §4.1 for per-case call budget and rate-limit strategy.
- **Retrieval:** Vector DB (FAISS/Chroma) + BM25/Elasticsearch/OpenSearch for hybrid search; cross-encoder reranker.
- **Data layer:** Curated legal corpus (JSONL/markdown), Jinja2/markdown templates for drafts, minimal session storage.

---

## 10. Evaluation Plan

- **Retrieval quality:** Manually verify retrieved sections are actually relevant for a test set of issue-type queries.
- **Groundedness:** % of generated legal claims that map to a retrieved citation vs. unsupported claims.
- **Extraction accuracy:** Compare extracted structured fields vs. ground truth on simulated/real cases.
- **Pilot:** 10–20 simulated or real refund cases; measure time saved and user-perceived usefulness.
- **End-to-end demo:** Raw text → structured case → legal explanation → checklist → drafts → export.

---

## 11. Related Work & Differentiation (summary)

| Category | Examples | Gap JusticeHelper fills |
|---|---|---|
| Govt/consumer portals | NCH, e-Daakhil, Consumer VOICE/CORE | Static forms/resources, not AI-driven or interactive |
| Global consumer legal automation | DoNotPay, robot-lawyer tools | Not India-specific, broad/shallow, form-driven not RAG |
| Corporate legal AI | Harvey, Anthropic Legal plugin-type tools | Built for professionals/enterprises, not individual consumers |

JusticeHelper's novelty: narrow India + e-commerce-refund domain focus, statute-aware hybrid RAG with citation-grounded generation, and an end-to-end evidence-to-draft consumer journey in plain language.

---

## 12. Risks & Limitations

- Legal accuracy risk if corpus is incomplete or law changes — mitigated by disclaimers and periodic corpus review.
- LLM extraction errors on messy Hinglish input — mitigated by follow-up questions for critical missing fields.
- No guarantee drafts will be accepted as-is by NCH/e-Daakhil — labeled as reference drafts only.
- Not a substitute for a qualified advocate — stated explicitly in UI.

---

## 13. Future Work (out of MVP scope)

- Hindi/bilingual output.
- Direct integration with e-Daakhil or platform grievance APIs (would introduce agentic behavior — deliberately deferred).
- Expansion to other consumer-dispute domains (warranty, service deficiency).
- Partnership with NGOs/consumer forums for real-world pilot.

---

## 14. Open Questions

- Which embedding model will be used (multilingual support needed if Hindi input/output is prioritized)?
- Where will the legal corpus be hosted/maintained, and how will updates to the Act/Rules be tracked?
- LLM provider is decided (Gemini primary, Groq/Together fallback — see `ARCHITECTURE.md` §4.1); remaining question is which specific Gemini model tier (e.g. Flash vs. Pro) to use for extraction/verification (cheaper, higher-volume) vs. generation (higher-stakes, citation-critical).
