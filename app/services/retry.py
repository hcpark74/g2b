from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar

import httpx


T = TypeVar("T")


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 1.0


class RetryableOperationError(RuntimeError):
    def __init__(
        self,
        *,
        operation_name: str,
        cause: Exception,
        retry_count: int,
    ) -> None:
        self.operation_name = operation_name
        self.cause = cause
        self.retry_count = retry_count
        self.status_code = self._extract_status_code(cause)
        super().__init__(str(cause))

    def _extract_status_code(self, cause: Exception) -> int | None:
        if isinstance(cause, httpx.HTTPStatusError):
            return cause.response.status_code
        return None


def run_with_retry(
    *,
    operation_name: str,
    func: Callable[[], T],
    policy: RetryPolicy,
    should_retry: Callable[[Exception], bool],
) -> T:
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            if attempt >= policy.max_attempts or not should_retry(exc):
                raise RetryableOperationError(
                    operation_name=operation_name,
                    cause=exc,
                    retry_count=attempt - 1,
                ) from exc
            if policy.backoff_seconds > 0:
                time.sleep(policy.backoff_seconds * attempt)
    assert last_exc is not None
    raise RetryableOperationError(
        operation_name=operation_name,
        cause=last_exc,
        retry_count=max(policy.max_attempts - 1, 0),
    )
