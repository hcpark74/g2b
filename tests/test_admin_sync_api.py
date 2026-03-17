import importlib
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import SyncJobLog


def _reload_module(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


@pytest.fixture
def admin_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "admin-sync.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("ADMIN_SYNC_TOKEN", "test-admin-token")

    _reload_module("app.config")
    db_module = _reload_module("app.db")
    _reload_module("app.models")
    _reload_module("app.cleanup_job_logs")
    _reload_module("app.admin_sync_router")
    db_module.init_db()
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


def _admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": "test-admin-token"}


def test_admin_sync_bid_public_info_returns_success_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def sync_bid_notices(
            self,
            *,
            inqry_bgn_dt: str,
            inqry_end_dt: str,
            operations: tuple[str, ...],
            num_of_rows: int,
        ):
            _ = (inqry_bgn_dt, inqry_end_dt, operations, num_of_rows)

            class Result:
                fetched_count = 3
                upserted_count = 2
                bid_ids = ["R26BK00000001-000", "R26BK00000002-000"]

            return Result()

    monkeypatch.setattr("app.admin_sync_router.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidPublicInfoSyncService", StubService
    )

    response = admin_client.post(
        "/admin/sync/bid-public-info",
        json={
            "begin": "202603120000",
            "end": "202603132359",
            "operations": ["getBidPblancListInfoServc"],
            "rows": 20,
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "bid_public_info_sync"
    assert payload["status"] == "completed"
    assert payload["fetched_count"] == 3
    assert payload["upserted_count"] == 2
    assert payload["bid_ids"] == ["R26BK00000001-000", "R26BK00000002-000"]


def test_admin_sync_bid_public_info_returns_failed_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class FailingService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def sync(self, **_: Any):
            raise RuntimeError("mock admin failure")

    monkeypatch.setattr("app.admin_sync_router.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidPublicInfoSyncService", FailingService
    )

    response = admin_client.post(
        "/admin/sync/bid-public-info",
        json={
            "begin": "202603120000",
            "end": "202603132359",
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "bid_public_info_sync"
    assert payload["status"] == "failed"
    assert payload["fetched_count"] == 0
    assert payload["upserted_count"] == 0
    assert "failure_category=unexpected" in payload["message"]


def test_admin_sync_failure_sends_slack_webhook(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []

    class StubClient:
        def close(self) -> None:
            return None

    class FailingService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def sync_bid_notices(self, **_: Any):
            raise RuntimeError("mock slack failure")

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> None:
        calls.append({"url": url, "json": json, "timeout": timeout})

    monkeypatch.setattr("app.admin_sync_router.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidPublicInfoSyncService", FailingService
    )
    monkeypatch.setattr(
        "app.services.operations_runtime.settings.ops_slack_webhook_url",
        "https://hooks.slack.test/services/example",
    )
    monkeypatch.setattr("app.services.operations_runtime.httpx.post", fake_post)

    response = admin_client.post(
        "/admin/sync/bid-public-info",
        json={
            "begin": "202603120000",
            "end": "202603132359",
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.slack.test/services/example"
    assert "bid_public_info_sync" in calls[0]["json"]["text"]
    assert "mock slack failure" in calls[0]["json"]["text"]


def test_admin_operations_lists_and_filters_logs(
    admin_client: TestClient,
) -> None:
    router_module = importlib.import_module("app.admin_sync_router")
    with Session(router_module.engine) as session:
        session.add(
            SyncJobLog(
                job_type="phase2_batch_sync",
                target="all-bids",
                status="completed",
                started_at=datetime(2026, 3, 14, 2, 12),
                finished_at=datetime(2026, 3, 14, 2, 13),
                message="selection_mode=targeted processed 1 bids detail_items=0 contract_items=1 crawl_attachments=1",
            )
        )
        session.add(
            SyncJobLog(
                job_type="bid_page_crawl",
                target="R26BK01387837-000",
                status="failed",
                started_at=datetime(2026, 3, 14, 2, 14),
                finished_at=datetime(2026, 3, 14, 2, 15),
                message="failure_category=browser_dom exception_type=RuntimeError detail=selector not found",
            )
        )
        session.commit()

    response = admin_client.get(
        "/admin/operations?status=failed&job_type=bid_page_crawl",
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["job_type"] == "bid_page_crawl"
    assert payload["items"][0]["status"] == "failed"


def test_admin_job_cleanup_supports_dry_run_and_delete(
    admin_client: TestClient,
) -> None:
    router_module = importlib.import_module("app.admin_sync_router")
    with Session(router_module.engine) as session:
        session.add(
            SyncJobLog(
                job_type="bid_resync",
                target="old-log",
                status="completed",
                started_at=datetime(2025, 1, 1, 0, 0),
                finished_at=datetime(2025, 1, 1, 0, 1),
                message="old",
            )
        )
        session.commit()

    dry_run_response = admin_client.post(
        "/admin/jobs/cleanup",
        json={
            "older_than_days": 30,
            "status": "completed",
            "job_type": "bid_resync",
            "dry_run": True,
        },
        headers=_admin_headers(),
    )

    assert dry_run_response.status_code == 200
    assert dry_run_response.json()["deleted_count"] == 1
    assert dry_run_response.json()["dry_run"] is True

    delete_response = admin_client.post(
        "/admin/jobs/cleanup",
        json={
            "older_than_days": 30,
            "status": "completed",
            "job_type": "bid_resync",
            "dry_run": False,
        },
        headers=_admin_headers(),
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_count"] == 1
    assert delete_response.json()["dry_run"] is False

    with Session(router_module.engine) as session:
        remaining = list(session.exec(select(SyncJobLog)).all())
    assert remaining == []


def test_admin_sync_bid_detail_enrichment_returns_success_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(self, **_: Any):
            class Result:
                processed_bid_ids = ["R26BK00001001-000"]
                fetched_item_count = 4

            return Result()

    monkeypatch.setattr("app.admin_sync_router.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidDetailEnrichmentService", StubService
    )

    response = admin_client.post(
        "/admin/sync/bid-detail-enrichment",
        json={
            "bid_ids": ["R26BK00001001-000"],
            "operations": ["getBidPblancListInfoLicenseLimit"],
            "selection_mode": "targeted",
            "recent_days": 7,
            "rows": 20,
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "bid_detail_enrichment"
    assert payload["status"] == "completed"
    assert payload["processed_bid_ids"] == ["R26BK00001001-000"]
    assert payload["fetched_item_count"] == 4


def test_admin_sync_contract_process_returns_success_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(self, **_: Any):
            class Result:
                processed_bid_ids = ["R26BK00001002-000"]
                fetched_item_count = 1

            return Result()

    monkeypatch.setattr("app.admin_sync_router.G2BContractProcessClient", StubClient)
    monkeypatch.setattr("app.admin_sync_router.G2BContractProcessService", StubService)

    response = admin_client.post(
        "/admin/sync/contract-process",
        json={"bid_ids": ["R26BK00001002-000"], "rows": 20},
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "contract_process_sync"
    assert payload["status"] == "completed"
    assert payload["processed_bid_ids"] == ["R26BK00001002-000"]
    assert payload["fetched_item_count"] == 1


def test_admin_sync_bid_crawl_returns_success_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubCrawler:
        def __init__(self, headless=None) -> None:
            self.headless = headless

    class StubService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            class Result:
                processed_bid_ids = bid_ids
                attachment_count = 2

            return Result()

    monkeypatch.setattr("app.admin_sync_router.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr("app.admin_sync_router.G2BBidCrawlService", StubService)

    response = admin_client.post(
        "/admin/sync/bid-crawl",
        json={"bid_ids": ["R26BK00001003-000"], "headless": True},
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "bid_page_crawl"
    assert payload["status"] == "completed"
    assert payload["processed_bid_ids"] == ["R26BK00001003-000"]
    assert payload["attachment_count"] == 2


def test_admin_sync_phase2_batch_returns_success_response(
    admin_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubDetailClient:
        def close(self) -> None:
            return None

    class StubContractClient:
        def close(self) -> None:
            return None

    class StubIndustryClient:
        def close(self) -> None:
            return None

    class StubCrawler:
        pass

    class StubDetailService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(self, **_: Any):
            class Result:
                processed_bid_ids = ["R26BK00001004-000"]
                fetched_item_count = 2

            return Result()

    class StubContractService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(self, **_: Any):
            class Result:
                fetched_item_count = 1

            return Result()

    class StubChangeHistoryService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def sync_change_history(self, **_: Any):
            class Result:
                fetched_item_count = 2

            return Result()

    class StubCrawlService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            class Result:
                attachment_count = 3

            return Result()

    class StubReferenceService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(self, **_: Any):
            class Result:
                fetched_item_count = 4

            return Result()

    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidPublicInfoClient", StubDetailClient
    )
    monkeypatch.setattr(
        "app.admin_sync_router.G2BContractProcessClient", StubContractClient
    )
    monkeypatch.setattr(
        "app.admin_sync_router.G2BIndustryInfoClient", StubIndustryClient
    )
    monkeypatch.setattr("app.admin_sync_router.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidDetailEnrichmentService", StubDetailService
    )
    monkeypatch.setattr(
        "app.admin_sync_router.G2BContractProcessService", StubContractService
    )
    monkeypatch.setattr(
        "app.admin_sync_router.G2BBidChangeHistoryService", StubChangeHistoryService
    )
    monkeypatch.setattr("app.admin_sync_router.G2BBidCrawlService", StubCrawlService)
    monkeypatch.setattr(
        "app.admin_sync_router.G2BReferenceEnrichmentService", StubReferenceService
    )

    response = admin_client.post(
        "/admin/sync/phase2-batch",
        json={
            "bid_ids": ["R26BK00001004-000"],
            "selection_mode": "targeted",
            "recent_days": 7,
            "rows": 20,
        },
        headers=_admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "phase2_batch_sync"
    assert payload["status"] == "completed"
    assert payload["processed_bid_ids"] == ["R26BK00001004-000"]
    assert payload["detail_items"] == 2
    assert payload["change_history_items"] == 2
    assert payload["contract_items"] == 1
    assert payload["crawl_attachments"] == 3
    assert payload["reference_items"] == 4


def test_admin_sync_requires_valid_token(admin_client: TestClient) -> None:
    missing_token_response = admin_client.get("/admin/operations")
    assert missing_token_response.status_code == 401

    invalid_token_response = admin_client.get(
        "/admin/operations",
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert invalid_token_response.status_code == 403
    assert invalid_token_response.json()["detail"] == "Invalid admin sync token"


def test_openapi_docs_expose_only_json_api_routes(admin_client: TestClient) -> None:
    docs_response = admin_client.get("/docs")
    assert docs_response.status_code == 200
    assert "조달 API 서비스 문서 포털" in docs_response.text
    assert "조달청_나라장터" in docs_response.text
    assert "입찰공고서비스" in docs_response.text
    assert "작업이력서비스" in docs_response.text
    assert "관리자동기화서비스" in docs_response.text
    assert "/docs/swagger?doc=g2b-bid-service" in docs_response.text
    assert "/docs/openapi/g2b-bid-service.json" in docs_response.text
    assert "/docs/openapi/g2b-job-service.json" in docs_response.text
    assert "/docs/openapi/g2b-admin-sync-service.json" in docs_response.text
    assert 'src="about:blank"' in docs_response.text

    openapi_response = admin_client.get("/openapi.json")
    assert openapi_response.status_code == 200

    schema = openapi_response.json()
    assert schema["info"]["title"] == "g2b"
    assert schema["info"]["version"] == "0.1.0"

    paths = set(schema["paths"].keys())
    assert paths == {
        "/api/v1/health",
        "/api/v1/search/bids",
        "/api/v1/bids",
        "/api/v1/bids/export",
        "/api/v1/bids/{bid_id}",
        "/api/v1/bids/{bid_id}/status",
        "/api/v1/bids/{bid_id}/favorite",
        "/api/v1/bids/{bid_id}/attachments",
        "/api/v1/bids/{bid_id}/timeline",
        "/api/v1/bids/{bid_id}/resync",
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
        "/admin/jobs/cleanup",
        "/admin/operations",
        "/admin/sync/bid-public-info",
        "/admin/sync/bid-detail-enrichment",
        "/admin/sync/contract-process",
        "/admin/sync/bid-crawl",
        "/admin/sync/phase2-batch",
    }


def test_health_api_returns_ok_when_database_is_available(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["database"] == "ok"
    assert payload["data"]["recent_failed_jobs"] == 0


def test_health_api_returns_degraded_when_latest_job_failed(
    admin_client: TestClient,
) -> None:
    main_module = importlib.import_module("app.main")
    with Session(main_module.engine) as session:
        session.add(
            SyncJobLog(
                job_type="bid_page_crawl",
                target="R26BK01387837-000",
                status="failed",
                started_at=datetime.now(),
                finished_at=datetime.now(),
                message="failure_category=browser_dom exception_type=RuntimeError detail=selector not found",
            )
        )
        session.commit()

    response = admin_client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "degraded"
    assert payload["data"]["recent_failed_jobs"] >= 1
    assert payload["data"]["latest_job"]["status"] == "failed"


def test_custom_doc_alias_renders_same_docs_shell(admin_client: TestClient) -> None:
    response = admin_client.get("/doc")

    assert response.status_code == 200
    assert "조달 API 서비스 문서 포털" in response.text
    assert 'src="about:blank"' in response.text


def test_docs_page_supports_doc_query_param(admin_client: TestClient) -> None:
    response = admin_client.get("/doc", params={"doc": "g2b-bid-service"})

    assert response.status_code == 200
    assert 'data-doc-id="g2b-bid-service"' in response.text
    assert 'class="docs-tree-button is-active"' in response.text
    assert "/api/v1/bids" in response.text
    assert "공공조달 데이터 조회 서비스 개발자" in response.text


def test_docs_page_rejects_unknown_doc_query_param(admin_client: TestClient) -> None:
    response = admin_client.get("/docs", params={"doc": "unknown"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Document not found"}


def test_filtered_docs_openapi_exposes_only_bids_tag(admin_client: TestClient) -> None:
    response = admin_client.get("/docs/openapi/g2b-bid-service.json")

    assert response.status_code == 200
    schema = response.json()
    assert set(schema["paths"].keys()) == {
        "/api/v1/search/bids",
        "/api/v1/bids",
        "/api/v1/bids/export",
        "/api/v1/bids/{bid_id}",
        "/api/v1/bids/{bid_id}/status",
        "/api/v1/bids/{bid_id}/favorite",
        "/api/v1/bids/{bid_id}/attachments",
        "/api/v1/bids/{bid_id}/timeline",
        "/api/v1/bids/{bid_id}/resync",
    }


def test_filtered_docs_openapi_exposes_only_jobs_tag(admin_client: TestClient) -> None:
    response = admin_client.get("/docs/openapi/g2b-job-service.json")

    assert response.status_code == 200
    schema = response.json()
    assert set(schema["paths"].keys()) == {
        "/api/v1/jobs",
        "/api/v1/jobs/{job_id}",
    }


def test_filtered_docs_openapi_exposes_only_admin_sync_tag(
    admin_client: TestClient,
) -> None:
    response = admin_client.get("/docs/openapi/g2b-admin-sync-service.json")

    assert response.status_code == 200
    schema = response.json()
    assert set(schema["paths"].keys()) == {
        "/admin/jobs/cleanup",
        "/admin/operations",
        "/admin/sync/bid-public-info",
        "/admin/sync/bid-detail-enrichment",
        "/admin/sync/contract-process",
        "/admin/sync/bid-crawl",
        "/admin/sync/phase2-batch",
    }


def test_swagger_embed_uses_filtered_openapi_url(admin_client: TestClient) -> None:
    response = admin_client.get("/docs/swagger", params={"doc": "g2b-bid-service"})

    assert response.status_code == 200
    assert "/docs/openapi/g2b-bid-service.json" in response.text
    assert "--docs-swagger-accent: #2168b4;" in response.text
    assert ".swagger-ui .topbar" in response.text


def test_openapi_admin_routes_include_error_examples(admin_client: TestClient) -> None:
    schema = admin_client.get("/openapi.json").json()

    bid_public_info_post = schema["paths"]["/admin/sync/bid-public-info"]["post"]
    unauthorized_example = bid_public_info_post["responses"]["401"]["content"][
        "application/json"
    ]["example"]
    forbidden_example = bid_public_info_post["responses"]["403"]["content"][
        "application/json"
    ]["example"]
    validation_example = bid_public_info_post["responses"]["422"]["content"][
        "application/json"
    ]["example"]

    assert unauthorized_example == {"detail": "Not authenticated"}
    assert forbidden_example == {"detail": "Invalid admin sync token"}
    assert validation_example["detail"][0]["loc"] == ["body", "begin"]
