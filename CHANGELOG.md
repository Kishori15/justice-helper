# Changelog

All notable changes to JusticeHelper's legal corpus, system prompts, schemas, and architecture are documented here per `PROMPTS.md` §6 and `CORPUS.md` §7.

## [Unreleased] - 2026-09-01
### Added
- Canonical specification docs organized in `docs/` (`PRD.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`, `CORPUS.md`, `DATA_SCHEMA.md`, `PROMPTS.md`, `EVALUATION.md`).
- Initial repository scaffolding matching `docs/PROJECT_STRUCTURE.md`.
- Verbatim system prompts in `backend/prompts/` matching `docs/PROMPTS.md`.
- Curated Indian legal corpus for e-commerce refund disputes (`cpa2019.jsonl`, `ecommerce_rules2020.jsonl`, `nch_guidelines.jsonl`).
- Pydantic data schemas mirroring `docs/DATA_SCHEMA.md`.
