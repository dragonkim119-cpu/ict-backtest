from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backtest import router as backtest_router
from app.api.candles import router as candles_router
from app.api.checklist import router as checklist_router
from app.api.ingest import router as ingest_router
from app.api.patterns import router as patterns_router
from app.api.ws import router as ws_router

app = FastAPI(title="ICT Backtest API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candles_router, prefix="/api")
app.include_router(patterns_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
app.include_router(backtest_router, prefix="/api")
app.include_router(checklist_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
