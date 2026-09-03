# EVALUATION.md
## JusticeHelper — Evaluation Plan

This document defines how JusticeHelper is tested: what's measured, how test cases are built, and how results should be reported. It operationalizes `PRD.md` §10 and gives concrete checks against the grounding guarantees defined in `PROMPTS.md` and `DATA_SCHEMA.md`.

---

## 1. What We're Trying to Prove

Three claims made elsewhere in the docs need evidence, not just design intent:

1. **Retrieval is actually relevant** — the hybrid retrieval + re-ranking pipeline (`ARCHITECTURE.md` §2.4–2.5) surfaces the right legal passages for a given issue.
2. **Generation is actually grounded** — every legal claim in the output traces to a retrieved passage (`PROMPTS.md` §3, `DATA_SCHEMA.md` §5), with no fabricated sections.
3. **Extraction is actually accurate** — free-text Hinglish/English input is correctly converted into the structured Case Object (`DATA_SCHEMA.md` §1).

Everything below is organized around these three claims, plus an end-to-end usability check.

---

## 2. Test Set Construction

### 2.1 Synthetic + real case mix
- Build **20–30 test cases** spanning all five issue types (`not_delivered`, `wrong_item`, `defective`, `refund_not_received`, `refund_delayed`), roughly 4–6 per type.
- Mix sources:
  - Simulated cases written to resemble realistic user messages (varying completeness, tone, and language mix).
  - A subset (aim for 5–10) from real or reported refund experiences (friends, family, public forum descriptions rewritten to remove identifying details) for authenticity.
- Vary input style deliberately: pure English, pure Hindi (if multilingual intake is being tested), and Hinglish — since this is a stated differentiator in `PRD.md` and `Novelty & Related Work`.
- Include a few deliberately **ambiguous or incomplete** cases (e.g., missing price, unclear issue type) to test the follow-up-question behavior in `PROMPTS.md` §1.

### 2.2 Test case format
Store each test case as a fixture file so runs are repeatable:

```json
{
  "test_id": "tc_07",
  "raw_input": "order abhi tak nahi aaya, 8 din ho gaye, Flipkart se liya tha t-shirt...",
  "expected_issue_type": "not_delivered",
  "expected_critical_fields": {
    "platform": "Flipkart",
    "product_name": "t-shirt",
    "issue_type": "not_delivered"
  },
  "expected_relevant_topics": ["deficiency_in_service", "refund", "complaint_timeline"],
  "notes": "Hinglish input, no price mentioned — should trigger follow-up for price_paid"
}
```

Keep these under `eval/test_cases/*.json` (or similar), separate from production code, so the set can grow over time without touching the app.

---

## 3. Retrieval Quality

**Goal:** confirm the hybrid retrieval + re-ranking step (not the LLM) is doing its job.

### Method
- For each test case, run only the retrieval pipeline (§2.2–2.5 in `ARCHITECTURE.md`) and record the top 5 reranked passage `id`s.
- Manually label each returned passage as **Relevant** or **Not Relevant** to the case's issue type, using human judgment against the corpus (`CORPUS.md`).
- Maintain a small **gold set**: for each test case, a human-curated list of the `id`s that *should* be retrieved (built once, reused across runs).

### Metrics
| Metric | Definition | Target |
|---|---|---|
| Precision@5 | Relevant passages / 5 returned | ≥ 0.7 |
| Recall@5 (vs. gold set) | Gold passages found in top 5 / total gold passages | ≥ 0.8 |
| Zero-relevant-result rate | % of test cases where none of the top 5 are relevant | 0 (flag any occurrence for corpus/retrieval review) |

### Comparison baseline
Also run a **naive baseline** (fixed-size chunking, vector-only top-k, no re-ranking) on the same test set and report the metrics above side by side. This substantiates the "modern RAG beats naive RAG" claim from the source design docs rather than asserting it.

---

## 4. Groundedness of Generated Output

**Goal:** verify the core promise — no fabricated law.

### Method
For each test case's `GenerationOutput` (`DATA_SCHEMA.md` §5):

1. For every entry in `legal_basis`, check:
   - Does `snippet_id` exist in that case's `retrieved_passage_ids`? *(This is exactly what the Citation Verification module in `PROMPTS.md` §5 automates — run it, then spot-check its output manually on a sample.)*
   - Does the `claim` text accurately reflect what the cited passage says (no overstatement, no contradiction)?
2. Score each claim: **Grounded**, **Overstated**, or **Fabricated**.

### Metrics
| Metric | Definition | Target |
|---|---|---|
| Grounded-claim rate | Grounded claims / total legal claims made | ≥ 95% |
| Fabrication rate | Fabricated claims / total legal claims made | 0% (any fabrication is a release blocker) |
| Auto-verifier agreement | % of cases where the automated Citation Verification pass (§5 in `PROMPTS.md`) agrees with human labeling | ≥ 90% (tracks whether the verifier itself is reliable enough to trust at scale) |

Any fabricated claim found should be logged with the exact prompt/model/corpus version (see `PROMPTS.md` §6) so it's reproducible and traceable to a fix.

---

## 5. Extraction Accuracy

**Goal:** confirm free-text → structured Case Object mapping works, including on Hinglish input.

### Method
- Compare `extracted_fields` output against `expected_critical_fields` in each test case fixture.
- Field-by-field exact/near match (e.g., "Flipkart" vs "flipkart.com" counts as match; date parsing tolerance ±0 days).
- Separately check: did the system correctly trigger a `follow_up_question` when a critical field (`issue_type`, `product_name`, `price_paid`, `platform`) was genuinely missing from input, and correctly *not* ask when it wasn't?

### Metrics
| Metric | Definition | Target |
|---|---|---|
| Critical-field accuracy | Correct critical fields / total critical fields across test set | ≥ 90% |
| issue_type classification accuracy | Correct issue_type / total test cases | ≥ 90% (this one matters most — it drives retrieval filtering) |
| Follow-up precision/recall | Correctly triggered vs. missed/unnecessary follow-ups | Report both; no hard target yet (qualitative review in early testing) |
| Hinglish subset accuracy | Same metrics, computed only on the Hinglish-input subset | Report separately — expect this to lag pure-English accuracy initially |

---

## 6. End-to-End Pilot

**Goal:** usability and perceived value, not just component correctness.

### Method
- Run 10–20 full sessions (simulated or real users) through the entire flow: Tell → Understand → Retrieve → Explain → Collect Evidence → Draft → Review → Export.
- Collect for each session:
  - Time from first message to exported draft.
  - Whether the user needed to manually correct >1 field in the case summary.
  - Whether the user edited the generated drafts, and roughly how much (light wording tweaks vs. substantial rewrite).
  - A short satisfaction rating (1–5) and one open comment.

### Metrics
| Metric | Definition | Target |
|---|---|---|
| Median time-to-draft | Minutes from first input to both drafts generated | Report as baseline (no fixed target for MVP) |
| Manual correction rate | % sessions needing >1 field correction | ≤ 30% |
| Heavy-edit rate | % sessions where user substantially rewrote a draft | Report as baseline; investigate generation quality if > 40% |
| Average satisfaction | Mean of 1–5 ratings | ≥ 3.5 |

---

## 7. Reporting Format

After each evaluation run, produce a short results record (can live in `eval/results/{date}.md`):

```
## Eval run: 2026-09-10
- Corpus version: (last_verified dates / CHANGELOG.md ref)
- Prompt version: PROMPTS.md §3 v2 (2026-09-01)
- Test set: 26 cases (eval/test_cases/)

Retrieval: Precision@5 = 0.81, Recall@5 = 0.85, zero-relevant = 0
Groundedness: grounded = 96%, fabricated = 0%, overstated = 4%
Extraction: critical-field accuracy = 88%, issue_type accuracy = 92%
Hinglish subset: critical-field accuracy = 79%

Notable failures:
- tc_14: fabricated citation to a non-existent "Sec 14(3)" — logged, root cause: retrieval missed the correct passage due to keyword mismatch, model filled gap. Action: add synonym to CORPUS.md topic tagging.
```

Keeping this format consistent across runs makes it possible to plot trend lines (e.g., extraction accuracy over successive prompt versions) for the project report/demo.

---

## 8. What "Passing" Means for the Project Demo

For a final-year project demo, the bar is not production-grade accuracy — it's **demonstrable, honest evaluation**:

- Show the naive-vs-modern-RAG retrieval comparison (§3) as the core technical evidence for the project's central claim.
- Show at least one worked example end-to-end with the retrieved passages, citations, and both drafts visible (ties to the "transparency" requirement in `PRD.md` §8).
- Be upfront about failure cases found during evaluation (§7) rather than only showing successes — this strengthens the "Limitations" section of the report and is expected of a well-run evaluation, not a weakness to hide.

---

## 9. Non-Goals

- No claim of statistical significance is being made — sample sizes here (20–30 cases) are for directional evidence and demo purposes, not a publishable benchmark.
- No automated regression test suite is assumed to run in CI for this project's scope; evaluation runs are manual/periodic (before milestones), tracked via the reporting format in §7.
- Legal correctness beyond "matches the curated corpus" is not evaluated here — that's a corpus curation concern (`CORPUS.md` §6), not a generation evaluation concern.
