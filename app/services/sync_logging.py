from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.services.g2b_bid_sync_service import BidPublicInfoSyncOperationError
from app.services.retry import RetryableOperationError


@dataclass(frozen=True, slots=True)
class SyncFailureInfo:
    category: str
    exception_type: str
    detail: str
    retry_count: int | None = None
    status_code: int | None = None
    operation_name: str | None = None


def build_sync_failure_message(exc: Exception) -> str:
    info = classify_sync_failure(exc)
    parts = [
        f"failure_category={info.category}",
        f"exception_type={info.exception_type}",
    ]
    if info.operation_name:
        parts.insert(0, f"operation={info.operation_name}")
    if info.retry_count is not None:
        parts.append(f"retry_count={info.retry_count}")
    if info.status_code is not None:
        parts.append(f"status_code={info.status_code}")
    parts.append(f"detail={info.detail}")
    return " ".join(parts)


def classify_sync_failure(exc: Exception) -> SyncFailureInfo:
    if isinstance(exc, BidPublicInfoSyncOperationError):
        return SyncFailureInfo(
            category=_category_for_exception(exc.cause),
            exception_type=type(exc.cause).__name__,
            detail=str(exc.cause),
            retry_count=exc.retry_count,
            status_code=exc.status_code,
            operation_name=exc.operation_name,
        )
    if isinstance(exc, RetryableOperationError):
        return SyncFailureInfo(
            category=_category_for_exception(exc.cause),
            exception_type=type(exc.cause).__name__,
            detail=str(exc.cause),
            retry_count=exc.retry_count,
            status_code=exc.status_code,
            operation_name=exc.operation_name,
        )

    status_code = (
        exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
    )
    return SyncFailureInfo(
        category=_category_for_exception(exc),
        exception_type=type(exc).__name__,
        detail=str(exc),
        status_code=status_code,
    )


def _category_for_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "api_timeout"
    if isinstance(exc, httpx.HTTPStatusError):
        return "api_http"

    exception_name = type(exc).__name__
    detail = str(exc).lower()
    if exception_name == "TimeoutError":
        return "browser_timeout"
    if "session" in detail or "login" in detail or "context" in detail:
        return "browser_session"
    if "selector" in detail or "dom" in detail:
        return "browser_dom"
    if "playwright" in detail or exception_name in {"Error", "TargetClosedError"}:
        return "browser_runtime"
    return "unexpected"
