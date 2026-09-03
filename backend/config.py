"""
Configuration settings for JusticeHelper backend.
Loads environment variables and sets defaults for LLM providers, models, paths, and DB.
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_gemini_keys_str = os.getenv("GEMINI_API_KEYS", "")
GEMINI_API_KEYS: List[str] = [k.strip() for k in _gemini_keys_str.split(",") if k.strip()]
if GEMINI_API_KEY and GEMINI_API_KEY not in GEMINI_API_KEYS:
    GEMINI_API_KEYS.insert(0, GEMINI_API_KEY)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

FALLBACK_LLM_PROVIDER = os.getenv("FALLBACK_LLM_PROVIDER", "groq").lower()  # groq | together
FALLBACK_LLM_API_KEY = os.getenv("FALLBACK_LLM_API_KEY", "")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama-3.3-70b-versatile")

# Retrieval & Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")

# Paths
DATA_DIR = BASE_DIR / "data"
CORPUS_DIR = DATA_DIR / "corpus"
INDEX_DIR = DATA_DIR / "index"
FAISS_INDEX_PATH = INDEX_DIR / "faiss.index"
BM25_INDEX_PATH = INDEX_DIR / "bm25_index.pkl"
ID_MAP_PATH = INDEX_DIR / "id_map.json"

DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "justicehelper.db")))

# Server & Network
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")
