# JusticeHelper

**AI-Assisted Indian E-Commerce Refund Complaint Drafting Tool**  
*A Modern, Non-Agentic RAG System Grounded in Indian Consumer Protection Law*

---

## 📌 Overview

JusticeHelper helps Indian consumers convert a plain-language description of an online shopping refund problem into structured, source-grounded complaint drafts addressed to:
1. **The Seller / Platform Grievance Officer** (Grievance Notice)
2. **The National Consumer Helpline (NCH) / Consumer Disputes Redressal Commission** (Escalation Draft)

Scoped **exclusively to Indian e-commerce refund disputes**:
- Item not delivered
- Wrong item delivered
- Defective / damaged item
- Refund initiated but not received
- Refund delayed beyond promised turnaround time (TAT)

---

## 🏛️ Architecture & Key Invariants

- **Non-Agentic Pipeline:** Sequential forward pipeline without autonomous planning loops or LLM tool-calling loops.
- **LLM Call Budget:** 3–5 calls per case (Intake $\to$ Rights Explanation $\to$ Draft Generation $\to$ Verification Critic).
- **Grounded Generation:** Every legal claim must cite an official statutory provision from the retrieved corpus (`CORPUS.md`).
- **Local Retrieval Stack:** `sentence-transformers` (`BAAI/bge-small-en-v1.5`), `faiss-cpu`, `rank-bm25`, and `BAAI/bge-reranker-base`.
- **Primary + Fallback Providers:** Google Gemini API (with key rotation support) + Groq / Together AI fallback on rate limits or errors.

---

## 🚀 Quickstart & Running Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and provide your Gemini / Groq API keys:
```bash
cp .env.example .env
```

### 3. Build/Refresh Legal Corpus Indexes
```bash
python -m backend.corpus --rebuild-index
```

### 4. Start the Backend API (FastAPI)
```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Start the Frontend (Streamlit)
In a separate terminal:
```bash
streamlit run frontend/app.py
```
Open `http://localhost:8501` in your browser.

---

## 🧪 Testing & Evaluation

### Run Unit & Integration Tests
```bash
python -m pytest tests/
```

### Run Evaluation Benchmarks
```bash
# 1. Retrieval Quality Benchmark (Precision@5, Recall@5 vs. naive baseline)
python eval/run_retrieval_eval.py

# 2. Groundedness Benchmark (Grounded claim rate, fabrication checks)
python eval/run_groundedness_eval.py

# 3. Extraction Accuracy Benchmark (Critical field matching & Hinglish performance)
python eval/run_extraction_eval.py
```

---

## 📁 Repository Layout

```
justicehelper/
├── backend/                   # FastAPI app, RAG modules, LLM orchestration
│   ├── main.py                # FastAPI entrypoint & lifespan
│   ├── config.py              # Environment configuration & model paths
│   ├── models.py              # Pydantic schemas mirroring DATA_SCHEMA.md
│   ├── intake.py              # Structured conversational extraction
│   ├── enrichment.py          # Query rewrite & topic mapping
│   ├── corpus.py              # Corpus indexing (FAISS + BM25)
│   ├── retrieval.py           # Hybrid retrieval (vector + keyword + topic)
│   ├── reranker.py            # Cross-encoder re-ranking & dedup
│   ├── generation.py          # Grounded rights & draft generation
│   ├── verification.py        # Citation verification critic
│   ├── checklist.py          # Non-LLM deterministic evidence checklist
│   ├── db.py                 # SQLite case persistence
│   ├── drafts.py             # Jinja2 draft rendering
│   ├── export_pdf.py         # PDF export (WeasyPrint / ReportLab)
│   ├── export_docx.py        # DOCX export (python-docx)
│   ├── prompts/              # Verbatim system prompts (PROMPTS.md)
│   ├── routers/              # API endpoints (chat, case, retrieve, generate, export)
│   └── templates/            # Jinja2 templates for drafts & HTML export
├── frontend/                  # Streamlit application
│   ├── app.py                # Main Streamlit app & navigation
│   ├── api_client.py         # Typed HTTP client calling FastAPI backend
│   ├── config.py             # Frontend configuration & branding
│   └── pages/                # Multi-page user journey (1 to 7)
├── data/
│   ├── corpus/               # Curated CPA 2019, E-Commerce Rules 2020, NCH JSONL
│   └── index/                # FAISS vector index, BM25 index, ID map
├── eval/                      # Evaluation suite & test fixtures
│   ├── test_cases/           # Test cases across 5 issue types
│   ├── gold_retrieval.json   # Expected gold passage IDs
│   ├── run_retrieval_eval.py # Retrieval precision/recall runner
│   ├── run_groundedness_eval.py
│   └── run_extraction_eval.py
├── docs/                      # Authoritative specification documents
└── tests/                     # Unit and integration test suite
```
