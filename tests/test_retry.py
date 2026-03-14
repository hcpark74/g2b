import httpx

from app.services.retry import RetryPolicy, RetryableOperationError, run_with_retry


def test_run_with_retry_succeeds_after_transient_failure() -> None:
    state = {"count": 0}

    def flaky() -> str:
        state["count"] += 1
        if state["count"] == 1:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError("temporary", request=request, response=response)
        return "ok"

    result = run_with_retry(
        operation_name="test",
        func=flaky,
        policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
        should_retry=lambda exc: isinstance(exc, httpx.HTTPStatusError),
    )

    assert result == "ok"
    assert state["count"] == 2


def test_run_with_retry_raises_retryable_operation_error() -> None:
    def always_fail() -> str:
        raise TimeoutError("browser timed out")

    try:
        run_with_retry(
            operation_name="crawl",
            func=always_fail,
            policy=RetryPolicy(max_attempts=2, backoff_seconds=0),
            should_retry=lambda exc: isinstance(exc, TimeoutError),
        )
    except RetryableOperationError as exc:
        assert exc.operation_name == "crawl"
        assert exc.retry_count == 1
        assert isinstance(exc.cause, TimeoutError)
    else:
        raise AssertionError("RetryableOperationError was not raised")
