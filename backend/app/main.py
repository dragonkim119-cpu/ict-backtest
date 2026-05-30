from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.api.backtest import router as backtest_router  # noqa: E402
from app.api.candles import router as candles_router  # noqa: E402
from app.api.checklist import router as checklist_router  # noqa: E402
from app.api.ingest import router as ingest_router  # noqa: E402
from app.api.journal import router as journal_router  # noqa: E402
from app.api.patterns import router as patterns_router  # noqa: E402
from app.api.telegram import router as telegram_router  # noqa: E402
from app.api.turtle import router as turtle_router  # noqa: E402
from app.api.ws import router as ws_router  # noqa: E402

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
app.include_router(journal_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(turtle_router, prefix="/api")
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
