import httpx

from app.services.g2b_bid_sync_service import BidPublicInfoSyncOperationError
from app.services.sync_logging import build_sync_failure_message, classify_sync_failure


def test_classify_sync_failure_for_http_status_error() -> None:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError(
        "service unavailable", request=request, response=response
    )

    info = classify_sync_failure(exc)

    assert info.category == "api_http"
    assert info.status_code == 503


def test_build_sync_failure_message_for_retryable_bid_sync_error() -> None:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(429, request=request)
    cause = httpx.HTTPStatusError("rate limited", request=request, response=response)
    exc = BidPublicInfoSyncOperationError(
        operation_name="getBidPblancListInfoServc",
        cause=cause,
        retry_count=2,
    )

    message = build_sync_failure_message(exc)

    assert "operation=getBidPblancListInfoServc" in message
    assert "failure_category=api_http" in message
    assert "retry_count=2" in message
    assert "status_code=429" in message


def test_build_sync_failure_message_for_browser_runtime_error() -> None:
    message = build_sync_failure_message(
        RuntimeError("playwright context closed unexpectedly")
    )

    assert "failure_category=browser_session" in message
    assert "exception_type=RuntimeError" in message
