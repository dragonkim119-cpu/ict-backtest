from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.telegram import get_threshold, is_configured, send_message


# ── is_configured ──────────────────────────────────────────────────

def test_not_configured_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert is_configured() is False


def test_not_configured_when_only_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert is_configured() is False


def test_configured_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")
    assert is_configured() is True


# ── get_threshold ──────────────────────────────────────────────────

def test_default_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_ALERT_THRESHOLD", raising=False)
    assert get_threshold() == 5


def test_custom_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_ALERT_THRESHOLD", "6")
    assert get_threshold() == 6


# ── send_message ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_skips_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    result = await send_message("hello")
    assert result is False


@pytest.mark.asyncio
async def test_send_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.telegram.httpx.AsyncClient", return_value=mock_client):
        result = await send_message("test alert")

    assert result is True
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["json"]["chat_id"] == "456"
    assert "test alert" in call_kwargs.kwargs["json"]["text"]


@pytest.mark.asyncio
async def test_send_returns_false_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.telegram.httpx.AsyncClient", return_value=mock_client):
        result = await send_message("test alert")

    assert result is False


@pytest.mark.asyncio
async def test_send_returns_false_on_raise_for_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(side_effect=Exception("401 Unauthorized"))
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.telegram.httpx.AsyncClient", return_value=mock_client):
        result = await send_message("test alert")

    assert result is False


# ── run_checklist integration: graceful None on missing data ───────

def test_run_checklist_returns_none_when_no_data(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.api.checklist import run_checklist
    result = run_checklist("BTCUSDT", "1h", "4h")
    assert result is None
