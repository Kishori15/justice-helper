# AGENTS.md
## JusticeHelper — Agent Working Rules

This file is read automatically at the start of every agent session in this
workspace (Antigravity, and any other AGENTS.md-compatible tool). It defines
how to work in this repo — not what to build. The "what" lives in `docs/`.

---

## 1. Required Reading (do this before any task)

Before writing, editing, or planning any code, read these files in `docs/`
in this order. They are the authoritative spec — do not deviate from them
without explicit approval from the project owner.

1. `docs/PRD.md` — product scope, user journey, functional requirements
2. `docs/ARCHITECTURE.md` — module design, tech stack, LLM call budget
3. `docs/PROJECT_STRUCTURE.md` — exact file/folder layout to follow
4. `docs/CORPUS.md` — legal corpus schema and curation rules
5. `docs/DATA_SCHEMA.md` — Case Object and all inter-module JSON schemas
6. `docs/PROMPTS.md` — exact system prompts for each LLM-calling stage
7. `docs/EVALUATION.md` — test methodology and success metrics

If any of these files is missing, out of date, or contradicts another,
stop and ask — do not guess which one is correct.

---

## 2. Hard Constraints (never violate without asking first)

- **Non-agentic pipeline.** The system executes each pipeline stage once,
  in a fixed order (`ARCHITECTURE.md` §2, §5). Never introduce autonomous
  planning loops, model-driven tool selection, or multi-step agent
  decision-making into the *application* itself. (This restriction is
  about the app JusticeHelper builds — it does not limit how you, the
  coding agent, plan and execute your own implementation work.)
- **LLM call budget: 3–5 calls per case.** Intake, rights/legal
  explanation, and drafts are each a single call; revisions are optional
  extra calls (`ARCHITECTURE.md` §4.1). The evidence checklist is a local,
  non-LLM lookup (`ARCHITECTURE.md` §2.6a, `PROMPTS.md` §4) — never turn it
  back into an LLM call without flagging that it breaks the budget.
- **Citation grounding is non-negotiable.** Every legal claim the system
  generates must cite a `snippet_id` that exists in that case's
  `retrieved_passage_ids` (`DATA_SCHEMA.md` §5, §8). Never loosen the
  "cite only from retrieved passages" instruction in `PROMPTS.md` §3 to
  fix a fluency, refusal, or citation-count problem — the fix is better
  retrieval or corpus content, not a looser generation prompt
  (`PROMPTS.md` §6).
- **Provider strategy is fixed.** Gemini is the primary LLM (with
  optional key rotation); a second provider (e.g., Groq/Together) is
  wired in only as a fallback on Gemini errors or `429` responses — never
  as an offline/default option (`ARCHITECTURE.md` §4, §4.1).
- **Retrieval/embedding/reranker stack is fixed.** `sentence-transformers`
  + `bge-small-en-v1.5` for embeddings, `faiss-cpu` for the vector index,
  `rank-bm25` for keyword search, `bge-reranker-base` for re-ranking
  (`ARCHITECTURE.md` §4). Don't substitute a different library or model
  without asking.
- **Schemas are exact.** Every JSON object produced or consumed by any
  module must match `DATA_SCHEMA.md` field-for-field — names, types,
  nesting. Don't add, rename, or drop fields without updating the doc
  first and confirming with the project owner.
- **Prompts are exact.** Use the system prompts in `PROMPTS.md` verbatim
  for each LLM call. If a prompt needs to change, propose the change and
  update `PROMPTS.md` (and log it per `PROMPTS.md` §6) — don't silently
  rewrite a prompt inline in code.
- **Corpus content must be traceable.** Never fabricate or paraphrase-fill
  a legal corpus entry from general knowledge. Every `text` field in
  `data/corpus/*.jsonl` must come from an official source cited in `url`
  (`CORPUS.md` §6). If you don't have verified source text, add a clearly
  marked placeholder and flag it for the project owner's review — do not
  invent plausible-sounding statute text.
- **Scope is fixed.** Only the five issue types in `PRD.md` §5
  (`not_delivered`, `wrong_item`, `defective`, `refund_not_received`,
  `refund_delayed`). Don't expand into other consumer-law domains.

---

## 3. File Layout

Follow `docs/PROJECT_STRUCTURE.md` exactly — file names, folder structure,
and the mapping between code files and doc sections (e.g., `retrieval.py`
implements `ARCHITECTURE.md` §2.4). If a task seems to require a new file
or module not listed there, propose the addition and update
`PROJECT_STRUCTURE.md` rather than adding it silently.

---

## 4. Workflow Expectations

- **Plan before coding.** For any non-trivial task, produce a short
  implementation plan (what files you'll touch, in what order, and why)
  before writing code. Wait for confirmation on anything that isn't
  obviously low-risk.
- **Work in phases.** Follow the phase order implied by
  `PROJECT_STRUCTURE.md` (data layer → retrieval → backend API → frontend
  → evaluation harness) unless told otherwise. Don't jump ahead to a
  later phase while an earlier one is incomplete or unreviewed.
- **Surface assumptions.** If you make an assumption to keep moving,
  state it explicitly in your response rather than burying it silently
  in code or leaving it undocumented.
- **Don't add dependencies** beyond what's listed in `ARCHITECTURE.md` §4
  without asking first.
- **Keep docs and code in sync.** If an implementation detail forces a
  deviation from `docs/`, update the relevant doc in the same change —
  don't let code and spec drift apart.

---

## 5. When to Ask a Clarifying Question Instead of Guessing

Stop and ask the project owner, rather than choosing a default, when:

- A requirement is genuinely ambiguous or not covered by any file in `docs/`.
- Two documents appear to conflict with each other.
- A task would require violating one of the hard constraints in §2.
- You're about to fabricate content that should instead come from a real,
  verifiable source (legal text, citations, statistics).
- A design choice has real trade-offs the docs don't resolve (e.g., which
  Gemini model tier to use for which call — flagged as an open question in
  `docs/PRD.md` §14).

Do not ask about things the docs already answer — read `docs/` first.

---

## 6. Environment

- Python 3.11+
- Backend: FastAPI (`uvicorn`), Pydantic for schema validation
- Frontend: Streamlit
- Package management: `pip` with a `requirements.txt` (or split
  `requirements-backend.txt` / `requirements-frontend.txt`) — not
  poetry/conda unless the project owner says otherwise
- Local run commands are listed in `docs/PROJECT_STRUCTURE.md` §9

---

## 7. Non-Goals for Agent Behavior

- Do not build any live integration with e-Daakhil, NCH, or platform
  grievance APIs — drafts are for user copy/export only (`PRD.md` §2, §13).
- Do not add authentication, multi-user accounts, or persistent
  cross-session case history — out of scope (`DATA_SCHEMA.md` §9).
- Do not set up CI/CD pipelines or containerization unless asked —
  evaluation and deployment are manual/periodic for this project's scope
  (`EVALUATION.md` §9, `PROJECT_STRUCTURE.md` §11).
