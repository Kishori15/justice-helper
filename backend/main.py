"""
FastAPI Application Entrypoint for JusticeHelper.
Implements ARCHITECTURE.md and PROJECT_STRUCTURE.md §2.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.corpus import corpus_store
from backend.db import init_db
from backend.routers import case, chat, export, generate, retrieve


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and load corpus index into memory
    print("JusticeHelper Backend starting up...")
    init_db()
    try:
        corpus_store.load()
        print("Corpus store and indexes loaded successfully.")
    except Exception as e:
        print(f"Notice: Corpus store index initialization pending: {e}")
    yield
    print("JusticeHelper Backend shutting down.")


app = FastAPI(
    title="JusticeHelper Backend API",
    description="AI-assisted Indian E-Commerce Refund Complaint Drafting Tool API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Streamlit or web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(chat.router)
app.include_router(case.router)
app.include_router(retrieve.router)
app.include_router(generate.router)
app.include_router(export.router)


@app.get("/")
def root():
    return {
        "app": "JusticeHelper",
        "version": "1.0.0",
        "description": "AI-Assisted E-Commerce Refund Complaint Drafting Tool API",
        "status": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    from backend.config import BACKEND_HOST, BACKEND_PORT
    uvicorn.run("backend.main:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
