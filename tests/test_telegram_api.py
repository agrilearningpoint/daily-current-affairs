"""Regression tests for pipeline.telegram_api.

Locks in:
- the published-ledger idempotency check now uses a real helper
  (store.is_job_published) instead of the missing is_job_published attribute,
- the sendDocument file handle is always closed (no leak),
- HTTP failures are classified retryable vs permanent,
- an unreadable ledger fails CLOSED (never risks a duplicate upload).

Fully offline: requests.post is stubbed.
"""
import pytest

import pipeline.store as store
import pipeline.telegram_api as tg


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = {"ok": True, "result": {"message_id": 11}} if payload is None else payload
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-not-real")


def test_send_document_closes_file_handle(monkeypatch, tmp_path):
    pdf = tmp_path / "edition.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    captured = {}

    def fake_post(url, data=None, files=None, timeout=None):
        captured["handle"] = files["document"][1]
        return FakeResponse()

    monkeypatch.setattr(tg.requests, "post", fake_post)
    message_id = tg.send_document("@chan", str(pdf), "caption", job_id=None)
    assert message_id == 11
    assert captured["handle"].closed is True, "file handle leaked after upload"


def test_send_document_skips_when_already_published(monkeypatch, tmp_path):
    pdf = tmp_path / "edition.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    calls = []
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: calls.append(1) or FakeResponse())

    def already(job_id):
        return True

    monkeypatch.setattr(tg, "_already_published", already)
    with pytest.raises(tg.TelegramPermanent):
        tg.send_document("@chan", str(pdf), "caption", job_id="daily_2026-10-05")
    assert calls == [], "no upload may happen for an already-published edition"


def test_unreadable_ledger_fails_closed(monkeypatch):
    def boom(job_id):
        raise RuntimeError("ledger unreadable")

    monkeypatch.setattr(store, "is_job_published", boom)
    # If the ledger cannot be read we must assume "published" (no duplicate send).
    assert tg._already_published("daily_2026-10-05") is True


def test_already_published_uses_store_helper(monkeypatch):
    monkeypatch.setattr(store, "is_job_published", lambda job_id: job_id == "daily_x")
    assert tg._already_published("daily_x") is True
    assert tg._already_published("daily_y") is False


def test_rate_limit_is_retryable_with_retry_after():
    resp = FakeResponse(status_code=429, payload={"ok": False, "parameters": {"retry_after": 7}})
    with pytest.raises(tg.TelegramRetryable) as excinfo:
        tg._raise_for_response("sendDocument", resp)
    assert excinfo.value.retry_after == 7


def test_bad_request_is_permanent():
    resp = FakeResponse(status_code=400, payload={"ok": False, "description": "chat not found"})
    with pytest.raises(tg.TelegramPermanent):
        tg._raise_for_response("sendDocument", resp)


def test_server_error_is_retryable():
    resp = FakeResponse(status_code=503, payload=ValueError("html gateway page"))
    with pytest.raises(tg.TelegramRetryable):
        tg._raise_for_response("sendDocument", resp)


def test_missing_token_is_permanent(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(tg.TelegramPermanent):
        tg._token()


def test_ok_response_returns_result():
    resp = FakeResponse(payload={"ok": True, "result": {"message_id": 5}})
    assert tg._raise_for_response("sendMessage", resp) == {"message_id": 5}
