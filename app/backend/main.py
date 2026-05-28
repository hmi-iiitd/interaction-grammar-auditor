"""
FastAPI backend for the Interaction Contract Auditor.
"""

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure modules are importable
sys.path.insert(0, str(Path(__file__).parent))

from routers import scenarios, audit, qa, reports, authoring
from config import get_settings

app = FastAPI(
    title="Interaction Contract Auditor API",
    description="LLM-assisted interface for HRI auditing pipeline",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scenarios.router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(qa.router, prefix="/api/qa", tags=["Q&A"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(authoring.router, prefix="/api/authoring", tags=["Authoring"])


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "dataset_root": settings.dataset_root,
        "llm_model": settings.llm_model,
    }
