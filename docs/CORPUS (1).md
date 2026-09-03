# CORPUS.md
## JusticeHelper — Legal Corpus Design

This document defines what goes into the legal corpus, how it's structured, and how it's maintained. The corpus is the ground-truth source for every citation JusticeHelper's generation module produces — nothing outside this corpus should ever be cited as law.

---

## 1. Scope

The corpus is **deliberately narrow**, matching the project's e-commerce-refund-only scope (see `PRD.md`). It is not a general Indian consumer-law database.

### Included sources

| Source | What's included | Why |
|---|---|---|
| **Consumer Protection Act, 2019** | Selected sections only: definitions (e.g., "consumer," "unfair trade practice," "deficiency"), consumer rights, redressal mechanisms | Statutory basis for rights and grounds of complaint |
| **Consumer Protection (E-Commerce) Rules, 2020** | Duties of e-commerce entities, grievance officer requirements, refund/return/cancellation disclosure obligations, complaint timelines | Directly governs e-commerce refund conduct |
| **National Consumer Helpline (NCH) guidelines/FAQs** | How to file a complaint, documents typically required, common refund scenarios and suggested steps | Practical, procedural guidance consumers actually need |

### Explicitly excluded

- Full text of either Act/Rules (only refund-relevant sections are curated).
- Case law / tribunal judgments (out of scope — avoids the system implying precedent it can't verify).
- Any other consumer-protection domain (warranty, service deficiency, offline purchases).
- Any source not officially published by the government or NCH (no blogs, law-firm summaries, or forum posts as primary corpus entries — external commentary may be linked in `url` metadata only if directly relevant, never treated as authoritative text).

---

## 2. Structural Principle

Naive RAG chunks documents into fixed-size blocks (e.g., 512 tokens) regardless of legal structure. This corpus instead preserves the **actual logical units** of the source documents:

```
Act        → Chapter → Section → Sub-section (if needed)
Rules      → Rule → Clause
Guidelines → Topic/Page section
```

Each logical unit becomes exactly one corpus entry. A unit is never split mid-section, and unrelated sections are never merged into one entry.

Two indexing levels are maintained (see `ARCHITECTURE.md` §2.3):
- **Unit-level** (section/rule/clause) — used for precise citation.
- **Group-level** (chapter/rule-group) — used only as supplementary parent context when a unit-level entry is too short to interpret alone.

---

## 3. Entry Schema

Each corpus entry is a single JSON object, one per line in the relevant `.jsonl` file.

```json
{
  "id": "cpa2019_sec2_7",
  "source_type": "act",
  "source_name": "Consumer Protection Act, 2019",
  "title": "Section 2(7) — Definition of Consumer",
  "section_number": "Sec 2(7)",
  "parent_id": "cpa2019_chapter1",
  "topics": ["consumer_definition", "rights"],
  "jurisdiction": "India",
  "url": "https://consumeraffairs.nic.in/...",
  "text": "\"consumer\" means any person who buys any goods for a consideration...",
  "last_verified": "2026-08-01"
}
```

### Field definitions

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Stable unique identifier. Convention: `{source_short}_{unit}` e.g. `ecomm2020_rule4_2`, `nch_faq_refund_delay`. Never reused or renumbered once published — generation output cites this directly. |
| `source_type` | enum | Yes | One of `act`, `rule`, `guideline`. Drives retrieval filtering. |
| `source_name` | string | Yes | Full human-readable name of the source document, used in generated citations. |
| `title` | string | Yes | Short descriptive title of this unit (used in UI and citation display). |
| `section_number` | string | Yes | The official section/rule number as it would appear in the source (e.g., "Sec 2(7)", "Rule 4(2)"). For guidelines without formal numbering, use a stable slug instead (e.g., "NCH-FAQ-3"). |
| `parent_id` | string \| null | No | ID of the group-level (chapter/rule-group) entry this unit belongs to, for hierarchical context retrieval. Null for group-level entries themselves. |
| `topics` | string[] | Yes | Controlled vocabulary tags (see §4) used for metadata filtering by issue type. |
| `jurisdiction` | string | Yes | Always `"India"` for this project; kept explicit for future extensibility. |
| `url` | string | Yes | Direct link to the official source page (gov.in domains where available). Shown to the user as a citation link. |
| `text` | string | Yes | The verbatim (or lightly cleaned) text of this unit. This is what gets embedded and what the generation module is constrained to. |
| `last_verified` | date | Yes | Date this entry was last checked against the official source. Used to flag stale entries (see §6). |

---

## 4. Controlled Topic Vocabulary

`topics` values are drawn from a fixed list so that issue-type → topic filtering (see `ARCHITECTURE.md` §2.4) is reliable. Initial vocabulary:

- `consumer_definition`
- `rights`
- `unfair_trade_practice`
- `deficiency_in_service`
- `redressal_mechanism`
- `ecommerce_entity_duties`
- `grievance_officer`
- `refund`
- `return_cancellation_policy`
- `complaint_timeline`
- `evidence_documentation`
- `jurisdiction_filing`

New topics should be added deliberately and documented here — not invented ad hoc during data entry — so retrieval filters stay predictable.

### Issue type → topic mapping (used by the retrieval module)

| Issue type | Relevant topics |
|---|---|
| `not_delivered` | `deficiency_in_service`, `refund`, `complaint_timeline` |
| `wrong_item` | `deficiency_in_service`, `unfair_trade_practice`, `refund` |
| `defective` | `deficiency_in_service`, `refund`, `return_cancellation_policy` |
| `refund_not_received` | `refund`, `grievance_officer`, `complaint_timeline` |
| `refund_delayed` | `refund`, `complaint_timeline`, `grievance_officer` |

This table is the concrete implementation of the "metadata filters" step described in `ARCHITECTURE.md`.

---

## 5. File Layout

```
data/
  corpus/
    cpa2019.jsonl              # Consumer Protection Act, 2019 — curated sections
    ecommerce_rules2020.jsonl  # Consumer Protection (E-Commerce) Rules, 2020
    nch_guidelines.jsonl       # NCH guidance/FAQ content
  index/
    faiss.index                # persisted vector index (built from all .jsonl above)
    bm25_index.pkl              # persisted BM25 index
    id_map.json                  # maps FAISS/BM25 internal indices → corpus `id`
```

Indexes in `data/index/` are build artifacts, not source-of-truth — they are regenerated from `data/corpus/*.jsonl` whenever the corpus changes (see §7).

---

## 6. Curation Process

1. **Source**: Pull section/rule text only from official government sources (e.g., consumeraffairs.nic.in, egazette, NCH portal).
2. **Segment**: Manually split into logical units per §2 — one entry per section/rule/clause relevant to e-commerce refunds.
3. **Tag**: Assign `source_type`, `topics` (from the controlled vocabulary in §4), and `parent_id`.
4. **Verify**: Cross-check the copied `text` against the official source for exact wording; record `last_verified`.
5. **Review pass**: A second person (or a second read on a different day) checks that no section was mis-numbered, mis-tagged, or paraphrased inaccurately.
6. **Commit**: Add/update the entry in the relevant `.jsonl` file; rebuild indexes.

No entry should be added to the corpus purely from memory or an LLM's summary of the law — every `text` field must be traceable to an official source at the `url` given.

---

## 7. Update & Versioning Policy

- The Consumer Protection Act, 2019 and E-Commerce Rules, 2020 are stable but not immutable — rules have been amended before (e.g., 2021, 2023 amendments) and NCH guidance is updated periodically.
- On each corpus review (recommended: before any project milestone/demo), re-verify `last_verified` dates against the official source. Entries older than **6 months** should be flagged for re-verification in `CHANGELOG.md`.
- Any change to an entry's `text` or `section_number` requires a new `id` only if the underlying legal provision has materially changed (e.g., renumbered section); otherwise update in place and bump `last_verified`.
- Index rebuilds (FAISS + BM25) must happen atomically after any corpus edit — the retrieval module should never run against a corpus file and index pair that are out of sync.

---

## 8. Non-Goals for This Corpus

- Not a substitute for the full text of the Act/Rules — always link to the official source (`url`) for anything beyond the curated excerpt.
- Not a legal opinion or interpretation layer — entries store the law as published, not commentary on how it applies to a specific case (that inference happens in the generation module, constrained to cite these entries).
- Not designed to scale to other legal domains without revisiting the topic vocabulary and source list above.
