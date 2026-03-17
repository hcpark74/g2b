import importlib
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_module(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


@pytest.fixture
def public_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "public-api.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sample")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    _reload_module("app.db")
    _reload_module("app.models")
    _reload_module("app.admin_sync_router")
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def sqlmodel_public_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "public-sqlmodel.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    _reload_module("app.db")
    seed_module = _reload_module("app.seed_bids")
    seed_module.seed_bids()
    _reload_module("app.models")
    _reload_module("app.admin_sync_router")
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


def test_list_bids_api_returns_wrapped_json_payload(public_client: TestClient) -> None:
    response = public_client.get("/api/v1/bids")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["meta"]["total"] >= 3
    assert payload["meta"]["page"] == 1
    assert payload["meta"]["page_size"] == 20
    assert payload["meta"]["sort"] == "posted_at"
    assert payload["meta"]["order"] == "desc"
    assert payload["meta"]["favorites_only"] is False
    assert payload["data"]["items"][0]["bid_id"] == "R26BK00000002-000"


def test_live_search_bids_api_returns_external_results(
    public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    main_module = importlib.import_module("app.main")

    class StubClient:
        def close(self) -> None:
            return None

        def fetch_bid_list(self, operation_name: str, **_: object):
            return [
                {
                    "bidNtceNo": "R26BK55555555",
                    "bidNtceOrd": "000",
                    "bidNtceNm": "AI 플랫폼 통합 유지보수",
                    "ntceInsttNm": "조달청",
                    "dminsttNm": "한국지능정보원",
                    "bidNtceDt": "202603130900",
                    "bidClseDt": "202603201800",
                    "opengDt": "202603201900",
                    "asignBdgtAmt": "120000000",
                    "bidNtceDtlUrl": "https://example.com/live/55555555",
                }
            ]

    monkeypatch.setattr(main_module, "G2BBidPublicInfoClient", StubClient)

    response = public_client.get("/api/v1/search/bids", params={"q": "AI"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["meta"]["source"] == "external_api"
    assert payload["meta"]["search_query"] == "AI"
    assert payload["meta"]["total"] == 1
    assert payload["data"]["items"][0]["bid_id"] == "R26BK55555555-000"
    assert payload["data"]["items"][0]["title"] == "AI 플랫폼 통합 유지보수"


def test_live_search_bids_api_marks_existing_favorites(
    sqlmodel_public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    main_module = importlib.import_module("app.main")

    class StubClient:
        def close(self) -> None:
            return None

        def fetch_bid_list(self, operation_name: str, **_: object):
            return [
                {
                    "bidNtceNo": "R26BK00000001",
                    "bidNtceOrd": "000",
                    "bidNtceNm": "한국지능정보원 AI 데이터 서비스 플랫폼 구축",
                    "ntceInsttNm": "조달청",
                    "dminsttNm": "한국지능정보원",
                    "bidNtceDt": "202603121100",
                    "bidClseDt": "202603181500",
                    "opengDt": "202603181600",
                    "asignBdgtAmt": "1500000000",
                    "bidNtceDtlUrl": "https://example.com/live/1",
                }
            ]

    monkeypatch.setattr(main_module, "G2BBidPublicInfoClient", StubClient)

    response = sqlmodel_public_client.get("/api/v1/search/bids", params={"q": "AI"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["items"][0]["bid_id"] == "R26BK00000001-000"
    assert payload["data"]["items"][0]["favorite"] is True


def test_list_bids_api_filters_results(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"q": "구급소모품", "status": "수집완료", "favorites_only": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
        "search_query": "구급소모품",
        "keyword": "",
        "status": "수집완료",
        "favorites_only": False,
        "sort": "posted_at",
        "order": "desc",
    }
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000002-000"
    ]


def test_list_bids_api_supports_pagination(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"page": 2, "page_size": 1, "sort": "posted_at", "order": "desc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {
        "total": 3,
        "page": 2,
        "page_size": 1,
        "total_pages": 3,
        "search_query": "",
        "keyword": "",
        "status": "",
        "favorites_only": False,
        "sort": "posted_at",
        "order": "desc",
    }
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000001-000"
    ]


def test_list_bids_api_supports_sorting(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"sort": "budget_amount", "order": "asc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["sort"] == "budget_amount"
    assert payload["meta"]["order"] == "asc"
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000002-000",
        "R26BK00000001-000",
        "R26BK00000003-000",
    ]


def test_list_bids_api_filters_by_org_and_budget(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"org": "전라남도", "budget_min": 1000000000},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000003-000"
    ]


def test_list_bids_api_filters_by_keyword(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"keyword": "데이터서비스"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["keyword"] == "데이터서비스"
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000001-000"
    ]


def test_list_bids_api_filters_by_attachment_keyword(
    sqlmodel_public_client: TestClient,
) -> None:
    from sqlmodel import Session

    from app.db import engine
    from app.models import Attachment

    with Session(engine) as session:
        session.add(
            Attachment(
                attachment_id="attachment-keyword-1",
                bid_id="R26BK00000001-000",
                name="제안요청서.hwpx",
                source="getBidPblancListInfoEorderAtchFileInfo",
                download_url="https://example.com/rfp.hwpx",
            )
        )
        session.commit()

    response = sqlmodel_public_client.get(
        "/api/v1/bids",
        params={"keyword": "제안요청서"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000001-000"
    ]


def test_list_bids_api_filters_by_timeline_keyword(
    sqlmodel_public_client: TestClient,
) -> None:
    from sqlmodel import Session

    from app.db import engine
    from app.models import TimelineStageSnapshot

    with Session(engine) as session:
        session.add(
            TimelineStageSnapshot(
                bid_id="R26BK00000002-000",
                stage="개찰/낙찰",
                status="예정",
                number="없음",
                occurred_at="2026-03-20 11:00",
                meta="예정",
            )
        )
        session.commit()

    response = sqlmodel_public_client.get(
        "/api/v1/bids",
        params={"keyword": "예정"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000002-000"
    ]


def test_list_bids_api_filters_by_closed_date_range(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"closed_from": "2026-03-18 00:00", "closed_to": "2026-03-20 23:59"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["bid_id"] for item in payload["data"]["items"]] == [
        "R26BK00000002-000",
        "R26BK00000001-000",
    ]


def test_list_bids_api_validates_budget_range(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"budget_min": 100, "budget_max": 10},
    )

    assert response.status_code == 422


def test_list_bids_api_validates_closed_date_range(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids",
        params={"closed_from": "2026-03-20 00:00", "closed_to": "2026-03-18 00:00"},
    )

    assert response.status_code == 422


def test_list_bids_api_returns_404_wrapper_when_empty(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids", params={"q": "does-not-exist"})

    assert response.status_code == 404
    payload = response.json()
    assert payload == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BIDS_NOT_FOUND",
            "message": "조건에 맞는 공고를 찾을 수 없습니다.",
        },
    }


def test_get_bid_api_returns_wrapped_detail_payload(public_client: TestClient) -> None:
    response = public_client.get("/api/v1/bids/R26BK00000003-000")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert payload["data"]["bid_id"] == "R26BK00000003-000"
    assert payload["data"]["business_type"] == "공사"
    assert isinstance(payload["data"]["attachments"], list)
    assert (
        payload["data"]["qualification"]["reference_infos"][0]["name"] == "포장공사업"
    )
    assert payload["data"]["qualification"]["reference_infos"][0]["code"] == "CONS-101"
    assert (
        payload["data"]["qualification"]["reference_infos"][0]["law_name"]
        == "건설산업기본법"
    )


def test_get_bid_api_returns_404_wrapper_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids/missing-bid")

    assert response.status_code == 404
    payload = response.json()
    assert payload == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_update_bid_status_api_updates_bid_and_persists_in_sample_backend(
    public_client: TestClient,
) -> None:
    update_response = public_client.patch(
        "/api/v1/bids/R26BK00000002-000/status",
        json={"status": "reviewing"},
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["success"] is True
    assert updated_payload["data"]["bid_id"] == "R26BK00000002-000"
    assert updated_payload["data"]["status"] == "검토중"

    get_response = public_client.get("/api/v1/bids/R26BK00000002-000")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["status"] == "검토중"


def test_update_bid_status_api_returns_404_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.patch(
        "/api/v1/bids/missing-bid/status",
        json={"status": "reviewing"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_update_bid_status_api_validates_allowed_status(
    public_client: TestClient,
) -> None:
    response = public_client.patch(
        "/api/v1/bids/R26BK00000002-000/status",
        json={"status": "invalid-status"},
    )

    assert response.status_code == 422


def test_add_bid_favorite_api_updates_bid(public_client: TestClient) -> None:
    response = public_client.post("/api/v1/bids/R26BK00000002-000/favorite")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["favorite"] is True

    favorites_response = public_client.get(
        "/api/v1/bids", params={"favorites_only": True}
    )
    favorite_ids = [
        item["bid_id"] for item in favorites_response.json()["data"]["items"]
    ]
    assert "R26BK00000002-000" in favorite_ids


def test_remove_bid_favorite_api_updates_bid(public_client: TestClient) -> None:
    response = public_client.delete("/api/v1/bids/R26BK00000001-000/favorite")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["favorite"] is False


def test_bid_favorite_api_returns_404_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.post("/api/v1/bids/missing-bid/favorite")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_list_bid_attachments_api_returns_attachment_items(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids/R26BK00000001-000/attachments")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["bid_id"] == "R26BK00000001-000"
    assert payload["data"]["items"][0]["name"] == "입찰공고문.hwpx"
    assert payload["data"]["items"][0]["source"] == "공고첨부"


def test_list_bid_attachments_api_returns_404_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids/missing-bid/attachments")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_list_bid_timeline_api_returns_timeline_items(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids/R26BK00000001-000/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["bid_id"] == "R26BK00000001-000"
    assert payload["data"]["items"][0]["stage"] == "사전규격"
    assert payload["data"]["items"][1]["status"] == "진행중"


def test_list_bid_timeline_api_returns_404_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/bids/missing-bid/timeline")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_queue_bid_resync_api_returns_queued_job(public_client: TestClient) -> None:
    response = public_client.post("/api/v1/bids/R26BK00000001-000/resync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_type"] == "bid_resync"
    assert payload["target"] == "R26BK00000001-000"
    assert payload["status"] == "queued"
    assert payload["job_id"] >= 1


def test_queue_bid_resync_api_returns_404_for_missing_bid(
    public_client: TestClient,
) -> None:
    response = public_client.post("/api/v1/bids/missing-bid/resync")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BID_NOT_FOUND",
            "message": "해당 공고를 찾을 수 없습니다.",
        },
    }


def test_get_job_status_api_returns_queued_job(public_client: TestClient) -> None:
    queue_response = public_client.post("/api/v1/bids/R26BK00000001-000/resync")
    job_id = queue_response.json()["job_id"]

    response = public_client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["job_id"] == job_id
    assert payload["data"]["job_type"] == "bid_resync"
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["message"] == "sample backend resync completed"
    assert payload["data"]["metadata"]["steps"] == [
        {
            "name": "detail_enrichment",
            "status": "completed",
            "fetched_item_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][0]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][0]["finished_at"],
        },
        {
            "name": "contract_process",
            "status": "completed",
            "fetched_item_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][1]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][1]["finished_at"],
        },
        {
            "name": "crawl",
            "status": "completed",
            "attachment_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][2]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][2]["finished_at"],
        },
    ]
    assert all(step["started_at"] for step in payload["data"]["metadata"]["steps"])
    assert all(step["finished_at"] for step in payload["data"]["metadata"]["steps"])


def test_queue_bid_resync_api_runs_real_services_for_sqlmodel_backend(
    sqlmodel_public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail_calls: list[list[str]] = []
    contract_calls: list[list[str]] = []
    crawl_calls: list[list[str]] = []

    class StubClient:
        def close(self) -> None:
            return None

    class StubDetailService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(
            self,
            *,
            bid_ids: list[str] | None = None,
            operations=(),
            num_of_rows: int = 100,
            selection_mode: str = "targeted",
            recent_days: int = 7,
        ):
            _ = (operations, num_of_rows, selection_mode, recent_days)
            detail_calls.append(list(bid_ids or []))

            class Result:
                processed_bid_ids = list(bid_ids or [])
                fetched_item_count = 4

            return Result()

    class StubCrawler:
        pass

    class StubContractClient:
        def close(self) -> None:
            return None

    class StubContractService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(
            self, *, bid_ids: list[str] | None = None, num_of_rows: int = 100
        ):
            _ = num_of_rows
            contract_calls.append(list(bid_ids or []))

            class Result:
                processed_bid_ids = list(bid_ids or [])
                fetched_item_count = 3

            return Result()

    class StubCrawlService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            crawl_calls.append(list(bid_ids))

            class Result:
                processed_bid_ids = list(bid_ids)
                attachment_count = 2

            return Result()

    monkeypatch.setattr("app.main.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr("app.main.G2BBidDetailEnrichmentService", StubDetailService)
    monkeypatch.setattr("app.main.G2BContractProcessClient", StubContractClient)
    monkeypatch.setattr("app.main.G2BContractProcessService", StubContractService)
    monkeypatch.setattr("app.main.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr("app.main.G2BBidCrawlService", StubCrawlService)

    queue_response = sqlmodel_public_client.post(
        "/api/v1/bids/R26BK00000001-000/resync"
    )

    assert queue_response.status_code == 200
    job_id = queue_response.json()["job_id"]
    assert detail_calls == [["R26BK00000001-000"]]
    assert contract_calls == [["R26BK00000001-000"]]
    assert crawl_calls == [["R26BK00000001-000"]]

    status_response = sqlmodel_public_client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["message"] == (
        "processed 1 bids, fetched 4 detail items, fetched 3 contract items, stored 2 attachments"
    )
    assert payload["data"]["metadata"]["steps"] == [
        {
            "name": "detail_enrichment",
            "status": "completed",
            "fetched_item_count": 4,
            "started_at": payload["data"]["metadata"]["steps"][0]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][0]["finished_at"],
        },
        {
            "name": "contract_process",
            "status": "completed",
            "fetched_item_count": 3,
            "started_at": payload["data"]["metadata"]["steps"][1]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][1]["finished_at"],
        },
        {
            "name": "crawl",
            "status": "completed",
            "attachment_count": 2,
            "started_at": payload["data"]["metadata"]["steps"][2]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][2]["finished_at"],
        },
    ]
    assert all(step["started_at"] for step in payload["data"]["metadata"]["steps"])
    assert all(step["finished_at"] for step in payload["data"]["metadata"]["steps"])


def test_queue_bid_resync_api_records_failed_step_metadata(
    sqlmodel_public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubDetailService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(
            self,
            *,
            bid_ids: list[str] | None = None,
            operations=(),
            num_of_rows: int = 100,
            selection_mode: str = "targeted",
            recent_days: int = 7,
        ):
            _ = (bid_ids, operations, num_of_rows, selection_mode, recent_days)

            class Result:
                processed_bid_ids = ["R26BK00000001-000"]
                fetched_item_count = 4

            return Result()

    class StubCrawler:
        pass

    class StubContractClient:
        def close(self) -> None:
            return None

    class StubContractService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(
            self, *, bid_ids: list[str] | None = None, num_of_rows: int = 100
        ):
            _ = (bid_ids, num_of_rows)

            class Result:
                processed_bid_ids = ["R26BK00000001-000"]
                fetched_item_count = 3

            return Result()

    class FailingCrawlService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            _ = bid_ids
            raise RuntimeError("crawl exploded")

    monkeypatch.setattr("app.main.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr("app.main.G2BBidDetailEnrichmentService", StubDetailService)
    monkeypatch.setattr("app.main.G2BContractProcessClient", StubContractClient)
    monkeypatch.setattr("app.main.G2BContractProcessService", StubContractService)
    monkeypatch.setattr("app.main.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr("app.main.G2BBidCrawlService", FailingCrawlService)

    queue_response = sqlmodel_public_client.post(
        "/api/v1/bids/R26BK00000001-000/resync"
    )

    assert queue_response.status_code == 200
    job_id = queue_response.json()["job_id"]

    status_response = sqlmodel_public_client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["data"]["status"] == "failed"
    assert payload["data"]["metadata"]["failed_step"] == "crawl"
    assert payload["data"]["metadata"]["error_reason"] == "crawl exploded"
    assert payload["data"]["metadata"]["steps"] == [
        {
            "name": "detail_enrichment",
            "status": "completed",
            "fetched_item_count": 4,
            "started_at": payload["data"]["metadata"]["steps"][0]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][0]["finished_at"],
        },
        {
            "name": "contract_process",
            "status": "completed",
            "fetched_item_count": 3,
            "started_at": payload["data"]["metadata"]["steps"][1]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][1]["finished_at"],
        },
        {
            "name": "crawl",
            "status": "failed",
            "attachment_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][2]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][2]["finished_at"],
        },
    ]
    assert payload["data"]["metadata"]["steps"][2]["started_at"]
    assert payload["data"]["metadata"]["steps"][2]["finished_at"]


def test_queue_bid_resync_api_records_contract_step_failure(
    sqlmodel_public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubDetailService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(
            self,
            *,
            bid_ids: list[str] | None = None,
            operations=(),
            num_of_rows: int = 100,
            selection_mode: str = "targeted",
            recent_days: int = 7,
        ):
            _ = (bid_ids, operations, num_of_rows, selection_mode, recent_days)

            class Result:
                processed_bid_ids = ["R26BK00000001-000"]
                fetched_item_count = 4

            return Result()

    class StubContractClient:
        def close(self) -> None:
            return None

    class FailingContractService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(
            self, *, bid_ids: list[str] | None = None, num_of_rows: int = 100
        ):
            _ = (bid_ids, num_of_rows)
            raise RuntimeError("contract exploded")

    class StubCrawler:
        pass

    class StubCrawlService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            _ = bid_ids

            class Result:
                processed_bid_ids = list(bid_ids)
                attachment_count = 2

            return Result()

    monkeypatch.setattr("app.main.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr("app.main.G2BBidDetailEnrichmentService", StubDetailService)
    monkeypatch.setattr("app.main.G2BContractProcessClient", StubContractClient)
    monkeypatch.setattr("app.main.G2BContractProcessService", FailingContractService)
    monkeypatch.setattr("app.main.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr("app.main.G2BBidCrawlService", StubCrawlService)

    queue_response = sqlmodel_public_client.post(
        "/api/v1/bids/R26BK00000001-000/resync"
    )

    assert queue_response.status_code == 200
    job_id = queue_response.json()["job_id"]

    status_response = sqlmodel_public_client.get(f"/api/v1/jobs/{job_id}")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["data"]["status"] == "failed"
    assert payload["data"]["metadata"]["failed_step"] == "contract_process"
    assert payload["data"]["metadata"]["error_reason"] == "contract exploded"
    assert payload["data"]["metadata"]["steps"] == [
        {
            "name": "detail_enrichment",
            "status": "completed",
            "fetched_item_count": 4,
            "started_at": payload["data"]["metadata"]["steps"][0]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][0]["finished_at"],
        },
        {
            "name": "contract_process",
            "status": "failed",
            "fetched_item_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][1]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][1]["finished_at"],
        },
        {
            "name": "crawl",
            "status": "queued",
            "attachment_count": 0,
            "started_at": payload["data"]["metadata"]["steps"][2]["started_at"],
            "finished_at": payload["data"]["metadata"]["steps"][2]["finished_at"],
        },
    ]
    assert payload["data"]["metadata"]["steps"][1]["started_at"]
    assert payload["data"]["metadata"]["steps"][1]["finished_at"]
    assert payload["data"]["metadata"]["steps"][2]["started_at"] is None


def test_get_job_status_api_returns_404_for_missing_job(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/v1/jobs/999999")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "JOB_NOT_FOUND",
            "message": "해당 작업을 찾을 수 없습니다.",
        },
    }


def test_list_jobs_api_returns_latest_jobs(public_client: TestClient) -> None:
    first = public_client.post("/api/v1/bids/R26BK00000001-000/resync")
    second = public_client.post("/api/v1/bids/R26BK00000002-000/resync")

    assert first.status_code == 200
    assert second.status_code == 200

    response = public_client.get("/api/v1/jobs", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["meta"]["total"] == 2
    assert payload["meta"]["page"] == 1
    assert payload["meta"]["page_size"] == 2
    assert payload["meta"]["total_pages"] == 1
    assert [item["target"] for item in payload["data"]["items"]] == [
        "R26BK00000002-000",
        "R26BK00000001-000",
    ]


def test_list_jobs_api_supports_pagination(public_client: TestClient) -> None:
    public_client.post("/api/v1/bids/R26BK00000001-000/resync")
    public_client.post("/api/v1/bids/R26BK00000002-000/resync")

    response = public_client.get("/api/v1/jobs", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 2
    assert payload["meta"]["page"] == 2
    assert payload["meta"]["page_size"] == 1
    assert payload["meta"]["total_pages"] == 2
    assert len(payload["data"]["items"]) == 1


def test_list_jobs_api_supports_status_and_job_type_filters(
    sqlmodel_public_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubClient:
        def close(self) -> None:
            return None

    class StubDetailService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_bids(self, **kwargs):
            class Result:
                processed_bid_ids = [kwargs["bid_ids"][0]]
                fetched_item_count = 1

            return Result()

    class StubContractClient:
        def close(self) -> None:
            return None

    class StubContractService:
        def __init__(self, session, client) -> None:
            self.session = session
            self.client = client

        def enrich_timelines(self, **kwargs):
            class Result:
                processed_bid_ids = [kwargs["bid_ids"][0]]
                fetched_item_count = 1

            return Result()

    class StubCrawler:
        pass

    class FailingCrawlService:
        def __init__(self, session, crawler) -> None:
            self.session = session
            self.crawler = crawler

        def crawl_bids(self, *, bid_ids: list[str]):
            _ = bid_ids
            raise RuntimeError("crawl exploded")

    monkeypatch.setattr("app.main.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr("app.main.G2BBidDetailEnrichmentService", StubDetailService)
    monkeypatch.setattr("app.main.G2BContractProcessClient", StubContractClient)
    monkeypatch.setattr("app.main.G2BContractProcessService", StubContractService)
    monkeypatch.setattr("app.main.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr("app.main.G2BBidCrawlService", FailingCrawlService)

    queued = sqlmodel_public_client.post("/api/v1/bids/R26BK00000001-000/resync")
    assert queued.status_code == 200

    failed_response = sqlmodel_public_client.get(
        "/api/v1/jobs",
        params={
            "status": "failed",
            "job_type": "bid_resync",
            "page": 1,
            "page_size": 10,
        },
    )
    assert failed_response.status_code == 200
    payload = failed_response.json()
    assert payload["meta"]["total"] >= 1
    assert all(item["status"] == "failed" for item in payload["data"]["items"])
    assert all(item["job_type"] == "bid_resync" for item in payload["data"]["items"])


def test_list_jobs_api_supports_started_date_range(public_client: TestClient) -> None:
    public_client.post("/api/v1/bids/R26BK00000001-000/resync")

    response = public_client.get(
        "/api/v1/jobs",
        params={"started_from": "2020-01-01 00:00", "started_to": "2100-01-01 00:00"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] >= 1


def test_list_jobs_api_supports_finished_date_range(public_client: TestClient) -> None:
    public_client.post("/api/v1/bids/R26BK00000001-000/resync")

    response = public_client.get(
        "/api/v1/jobs",
        params={"finished_from": "2020-01-01 00:00", "finished_to": "2100-01-01 00:00"},
    )

    assert response.status_code == 200
    assert response.json()["meta"]["total"] >= 1


def test_list_jobs_api_supports_sorting(public_client: TestClient) -> None:
    public_client.post("/api/v1/bids/R26BK00000001-000/resync")
    public_client.post("/api/v1/bids/R26BK00000002-000/resync")

    response = public_client.get(
        "/api/v1/jobs",
        params={"sort": "started_at", "order": "asc", "page": 1, "page_size": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["total"] == 2
    assert [item["target"] for item in payload["data"]["items"]] == [
        "R26BK00000001-000",
        "R26BK00000002-000",
    ]


def test_list_jobs_api_is_exposed_in_openapi(public_client: TestClient) -> None:
    response = public_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/jobs" in schema["paths"]
    assert schema["paths"]["/api/v1/jobs"]["get"]["summary"] == "List jobs"
    parameter_names = [
        parameter["name"]
        for parameter in schema["paths"]["/api/v1/jobs"]["get"]["parameters"]
    ]
    assert parameter_names == [
        "page",
        "page_size",
        "sort",
        "order",
        "status",
        "job_type",
        "started_from",
        "started_to",
        "finished_from",
        "finished_to",
    ]
    sort_schema = schema["paths"]["/api/v1/jobs"]["get"]["parameters"][2]["schema"]
    order_schema = schema["paths"]["/api/v1/jobs"]["get"]["parameters"][3]["schema"]
    status_schema = schema["paths"]["/api/v1/jobs"]["get"]["parameters"][4]["schema"]
    job_type_schema = schema["paths"]["/api/v1/jobs"]["get"]["parameters"][5]["schema"]
    assert sort_schema["enum"] == ["started_at", "finished_at", "status"]
    assert order_schema["enum"] == ["asc", "desc"]
    assert status_schema["anyOf"][0]["enum"] == [
        "queued",
        "running",
        "completed",
        "failed",
    ]
    assert job_type_schema["anyOf"][0]["enum"] == [
        "bid_resync",
        "bid_public_info_sync",
        "bid_detail_enrichment",
        "contract_process_sync",
        "bid_page_crawl",
        "phase2_batch_sync",
    ]


def test_list_jobs_api_validates_filter_enums(public_client: TestClient) -> None:
    invalid_status = public_client.get("/api/v1/jobs", params={"status": "unknown"})
    invalid_job_type = public_client.get("/api/v1/jobs", params={"job_type": "unknown"})

    assert invalid_status.status_code == 422
    assert invalid_job_type.status_code == 422


def test_list_jobs_api_validates_started_date_range(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/jobs",
        params={"started_from": "2026-03-20 00:00", "started_to": "2026-03-18 00:00"},
    )

    assert response.status_code == 422


def test_list_jobs_api_validates_finished_date_range(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/jobs",
        params={"finished_from": "2026-03-20 00:00", "finished_to": "2026-03-18 00:00"},
    )

    assert response.status_code == 422


def test_export_bids_api_returns_csv(public_client: TestClient) -> None:
    response = public_client.get("/api/v1/bids/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="bids-export.csv"'
    )
    assert "bid_id,title,notice_org" in response.text
    assert "R26BK00000002-000" in response.text


def test_export_bids_api_applies_filters(public_client: TestClient) -> None:
    response = public_client.get(
        "/api/v1/bids/export",
        params={"keyword": "데이터서비스"},
    )

    assert response.status_code == 200
    assert "R26BK00000001-000" in response.text
    assert "R26BK00000002-000" not in response.text


def test_export_bids_api_returns_404_when_empty(public_client: TestClient) -> None:
    response = public_client.get("/api/v1/bids/export", params={"q": "does-not-exist"})

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "data": None,
        "meta": {},
        "error": {
            "code": "BIDS_NOT_FOUND",
            "message": "조건에 맞는 공고를 찾을 수 없습니다.",
        },
    }


def test_openapi_includes_public_bids_endpoints(public_client: TestClient) -> None:
    response = public_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/search/bids" in schema["paths"]
    assert "/api/v1/bids" in schema["paths"]
    assert "/api/v1/bids/export" in schema["paths"]
    assert "/api/v1/bids/{bid_id}" in schema["paths"]
    assert "/api/v1/bids/{bid_id}/status" in schema["paths"]
    assert "/api/v1/bids/{bid_id}/favorite" in schema["paths"]
    assert "/api/v1/bids/{bid_id}/attachments" in schema["paths"]
    assert "/api/v1/bids/{bid_id}/timeline" in schema["paths"]
    assert "/api/v1/bids/{bid_id}/resync" in schema["paths"]
    assert "/api/v1/jobs/{job_id}" in schema["paths"]
    assert (
        schema["paths"]["/api/v1/search/bids"]["get"]["summary"] == "Search live bids"
    )
    assert schema["paths"]["/api/v1/bids"]["get"]["summary"] == "List bids"
    assert schema["paths"]["/api/v1/bids/export"]["get"]["summary"] == "Export bids"
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}"]["get"]["summary"] == "Get bid detail"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/status"]["patch"]["summary"]
        == "Update bid status"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/favorite"]["post"]["summary"]
        == "Add bid favorite"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/favorite"]["delete"]["summary"]
        == "Remove bid favorite"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/attachments"]["get"]["summary"]
        == "List bid attachments"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/timeline"]["get"]["summary"]
        == "List bid timeline"
    )
    assert (
        schema["paths"]["/api/v1/bids/{bid_id}/resync"]["post"]["summary"]
        == "Queue bid resync"
    )
    assert (
        schema["paths"]["/api/v1/jobs/{job_id}"]["get"]["summary"] == "Get job status"
    )
