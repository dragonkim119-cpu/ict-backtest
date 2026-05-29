from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.telegram import get_threshold, is_configured, send_message

router = APIRouter()


class TelegramStatus(BaseModel):
    configured: bool
    threshold: int


class TestResult(BaseModel):
    sent: bool
    message: str


@router.get("/telegram/status", response_model=TelegramStatus)
def telegram_status() -> TelegramStatus:
    return TelegramStatus(configured=is_configured(), threshold=get_threshold())


@router.post("/telegram/test", response_model=TestResult)
async def telegram_test() -> TestResult:
    sent = await send_message("\U0001f514 ICT Backtest: Test message")
    return TestResult(
        sent=sent,
        message="Message sent successfully" if sent else "Telegram not configured or send failed",
    )
