# PROJECT_STRUCTURE.md
## JusticeHelper — Repository Layout

This document defines the actual file/folder structure for the codebase. It maps directly onto the modules described in `ARCHITECTURE.md` §2, the tech stack in `ARCHITECTURE.md` §4, the corpus layout in `CORPUS.md` §5, and the evaluation harness in `EVALUATION.md`. Use this as the canonical layout when scaffolding the project — don't invent alternate module names or locations.

---

## 1. Top-Level Layout

```
justicehelper/
├── backend/                   # FastAPI app — RAG pipeline, LLM orchestration
├── frontend/                  # Streamlit app
├── data/                      # Legal corpus, indexes, case storage
├── eval/                      # Evaluation harness (EVALUATION.md)
├── docs/                      # This project's markdown specs (PRD.md, ARCHITECTURE.md, etc.)
├── tests/                     # Unit/integration tests
├── .env.example                # Template for API keys / config
├── requirements.txt            # Or split into backend/frontend requirements
├── README.md
└── CHANGELOG.md
```

---

## 2. Backend (`backend/`)

Maps directly to the modules in `ARCHITECTURE.md` §2.1–2.7.

```
backend/
├── main.py                    # FastAPI app, route registration
├── config.py                  # Env vars, Gemini key rotation list, fallback provider config, model names, paths
├── models.py                  # Pydantic schemas — mirrors DATA_SCHEMA.md exactly
│
├── routers/
│   ├── chat.py                 # POST /api/chat
│   ├── case.py                 # classify_issue, DELETE /api/case
│   ├── retrieve.py             # POST /api/retrieve
│   ├── generate.py             # generate_explanation, generate_drafts
│   └── export.py               # GET /api/export/pdf, /api/export/docx
│
├── intake.py                  # ARCHITECTURE.md §2.1 — extraction module (multi-turn, 3-round cap)
├── enrichment.py               # ARCHITECTURE.md §2.2 — query enrichment
├── corpus.py                  # ARCHITECTURE.md §2.3 — load/build corpus indexes
├── retrieval.py                # ARCHITECTURE.md §2.4 — hybrid retrieval (FAISS + BM25 + metadata filter)
├── reranker.py                  # ARCHITECTURE.md §2.5 — cross-encoder re-ranking + dedup
├── generation.py                # ARCHITECTURE.md §2.6 — grounded generation (rights, drafts)
├── verification.py              # ARCHITECTURE.md §2.7 — citation verification pass
│
├── llm_client.py                # Gemini client (primary, with key rotation) + fallback provider client (e.g. Groq/Together), behind a single interface
├── drafts.py                    # Draft templating (Jinja2) + assembly of GenerationOutput
├── checklist.py                  # ARCHITECTURE.md §2.6a — evidence checklist via local lookup table, no LLM call (PROMPTS.md §4)
├── export_pdf.py                 # weasyprint PDF rendering
├── export_docx.py                # python-docx DOCX generation
├── db.py                        # SQLite or JSON-file case storage (DATA_SCHEMA.md §1)
│
├── prompts/                     # System prompts, one file per PROMPTS.md LLM-calling section — loaded, not hardcoded inline
│   ├── intake_prompt.py         # PROMPTS.md §1
│   ├── enrichment_prompt.py     # PROMPTS.md §2
│   ├── generation_prompt.py     # PROMPTS.md §3
│   └── verification_prompt.py   # PROMPTS.md §5
│   # Note: no checklist_prompt.py — checklist generation is a local lookup (checklist.py), not an LLM prompt (PROMPTS.md §4)
│
└── templates/                   # Jinja2 templates for drafts and export HTML
    ├── email_draft.txt
    ├── complaint_draft.txt
    └── export_html.html
```

**Notes:**
- `prompts/` holds the exact text from `PROMPTS.md` as importable constants/functions — never inline a prompt string directly in `generation.py` or elsewhere. This keeps `PROMPTS.md` and code in sync; any prompt edit should update both.
- `models.py` should be generated/checked against `DATA_SCHEMA.md` directly — every Pydantic model name should map 1:1 to a schema section (e.g., `CaseObject`, `EnrichedQuery`, `RetrievalResult`, `GenerationOutput`, `VerificationResult`).
- `llm_client.py` wraps the Gemini SDK (primary, with optional key rotation) and a fallback provider SDK (e.g. Groq/Together) behind a single interface, as described in `ARCHITECTURE.md` §4.1, so the rest of the backend calls one consistent function and never needs to know which provider actually served a given request. The fallback is only invoked on Gemini errors or `429` responses.

---

## 3. Frontend (`frontend/`)

Maps to the seven UI sections implied by the user journey in `PRD.md` §6 and described in `ARCHITECTURE.md` §4.

```
frontend/
├── app.py                     # Streamlit entrypoint, page routing/session state
├── api_client.py                # Wraps requests/httpx calls to the FastAPI backend
├── config.py                    # Backend base URL, etc.
│
└── pages/
    ├── 1_new_case.py            # Home / New Case
    ├── 2_chat_intake.py          # "Tell" step — chat interface
    ├── 3_case_summary.py         # "Understand" step — editable extracted fields
    ├── 4_rights_and_basis.py     # "Retrieve" & "Explain" — rights summary + citations
    ├── 5_evidence_checklist.py   # "Collect Evidence" — checklist with how-tos
    ├── 6_drafts_review.py        # "Draft" & "Review" — email + NCH complaint, editable
    └── 7_export.py               # "Export" — PDF/DOCX download, delete case
```

---

## 4. Data (`data/`)

Matches `CORPUS.md` §5 exactly, extended with case storage.

```
data/
├── corpus/
│   ├── cpa2019.jsonl
│   ├── ecommerce_rules2020.jsonl
│   └── nch_guidelines.jsonl
│
├── index/
│   ├── faiss.index
│   ├── bm25_index.pkl
│   └── id_map.json
│
└── cases/                      # Only used if JSON-file case storage is chosen over SQLite
    └── {case_id}.json
```

If SQLite is used instead of JSON-file case storage, `data/cases/` is replaced by a single `data/justicehelper.db` file — pick one per `ARCHITECTURE.md` §4 and don't maintain both.

---

## 5. Evaluation (`eval/`)

Matches the harness described in `EVALUATION.md` §2 and §7.

```
eval/
├── test_cases/
│   ├── tc_01.json
│   ├── tc_02.json
│   └── ...                     # One file per test case, schema per EVALUATION.md §2.2
│
├── gold_retrieval.json          # Human-curated expected passage ids per test case (EVALUATION.md §3)
│
├── run_retrieval_eval.py        # Computes Precision@5 / Recall@5, naive-baseline comparison
├── run_groundedness_eval.py     # Runs generation + verification, scores grounded/overstated/fabricated
├── run_extraction_eval.py       # Compares extracted_fields vs. expected_critical_fields
│
└── results/
    └── {date}.md                # Report format from EVALUATION.md §7
```

---

## 6. Docs (`docs/`)

The specification files this project is built from — kept in the repo so code and spec never drift apart silently.

```
docs/
├── PRD.md
├── ARCHITECTURE.md
├── CORPUS.md
├── DATA_SCHEMA.md
├── PROMPTS.md
├── EVALUATION.md
└── PROJECT_STRUCTURE.md         # this file
```

---

## 7. Tests (`tests/`)

Standard unit/integration tests, separate from the evaluation harness in `eval/` (which tests model/pipeline *quality*, not code *correctness*).

```
tests/
├── test_models.py               # Pydantic schema validation (DATA_SCHEMA.md §8 rules)
├── test_corpus_loading.py        # Corpus JSONL parses correctly, index builds
├── test_retrieval.py             # Retrieval returns expected shape, filters apply correctly
├── test_verification.py          # Citation verification catches known-bad fixtures
└── test_api_routes.py            # FastAPI route request/response shape checks
```

---

## 8. Root-Level Files

```
.env.example
  GEMINI_API_KEY=
  GEMINI_API_KEYS=                 # optional comma-separated list, for key rotation
  FALLBACK_LLM_PROVIDER=groq        # groq | together
  FALLBACK_LLM_API_KEY=
  DB_PATH=data/justicehelper.db

requirements.txt          # or requirements-backend.txt / requirements-frontend.txt if split
README.md                 # setup, run instructions, project summary
CHANGELOG.md              # corpus updates, prompt version changes (per PROMPTS.md §6, CORPUS.md §7)
```

---

## 9. Run Commands (for reference)

```bash
# Backend
uvicorn backend.main:app --reload

# Frontend (separate terminal)
streamlit run frontend/app.py

# Build/refresh corpus indexes
python -m backend.corpus --rebuild-index

# Run evaluation
python eval/run_retrieval_eval.py
python eval/run_groundedness_eval.py
python eval/run_extraction_eval.py
```

---

## 10. Naming Rules (to keep code and docs in sync)

- Every file in `backend/` that implements a pipeline stage must be named after — and only after — the module it implements in `ARCHITECTURE.md` §2. Don't split or merge modules without updating `ARCHITECTURE.md` first.
- Every Pydantic model in `models.py` must have a name and field set traceable to a section in `DATA_SCHEMA.md`. If a field is added in code that isn't in `DATA_SCHEMA.md`, update the doc — not the other way around silently.
- Every prompt file in `backend/prompts/` must match its corresponding section in `PROMPTS.md` verbatim. A diff between the two is a bug.
- Corpus file names in `data/corpus/` must match those listed in `CORPUS.md` §5 exactly.

---

## 11. Non-Goals

- No CI/CD pipeline structure is defined here — out of scope per `EVALUATION.md` §9 (evaluation is manual/periodic for this project's scope).
- No multi-service/Docker layout is defined — this structure assumes local/single-VPS deployment per `ARCHITECTURE.md` §4. Containerization can be added later without changing the module layout above.
