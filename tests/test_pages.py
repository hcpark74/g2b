import importlib
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_module(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


@pytest.fixture
def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "pages-sample.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sample")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    _reload_module("app.db")
    _reload_module("app.models")
    _reload_module("app.admin_sync_router")
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as test_client:
        yield test_client


def test_search_home_renders(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "필요한 공고를 키워드로 바로 찾으세요." in response.text
    assert "통합 검색" in response.text
    assert "전체 현황" in response.text


def test_overview_page_renders(client: TestClient) -> None:
    response = client.get("/overview")

    assert response.status_code == 200
    assert "전체 현황" in response.text
    assert "운영 상태 요약" in response.text


def test_bids_page_renders(client: TestClient) -> None:
    response = client.get("/bids")

    assert response.status_code == 200
    assert "통합 검색 결과" in response.text
    assert "실시간 검색 결과" in response.text
    assert (
        "검색어 또는 기관 조건을 입력해 실시간 API 검색을 시작하세요." in response.text
    )


def test_bids_page_renders_live_api_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    main_module = importlib.import_module("app.main")

    class StubClient:
        def close(self) -> None:
            return None

        def fetch_bid_list(self, operation_name: str, **_: object):
            return [
                {
                    "bidNtceNo": "R26BK00000077",
                    "bidNtceOrd": "000",
                    "bidNtceNm": "AI 통합플랫폼 유지보수 용역",
                    "ntceInsttNm": "조달청",
                    "dminsttNm": "한국지능정보원",
                    "bidNtceDt": "202603130900",
                    "bidClseDt": "202603201800",
                    "opengDt": "202603201900",
                    "asignBdgtAmt": "120000000",
                    "bidNtceDtlUrl": "https://example.com/bids/77",
                }
            ]

    monkeypatch.setattr(main_module, "G2BBidPublicInfoClient", StubClient)

    response = client.get("/bids?q=AI")

    assert response.status_code == 200
    assert 'id="live-bids-search-form"' in response.text
    assert "/api/v1/search/bids?${params.toString()}" in response.text
    assert "if (shouldAutoload) runSearch()" in response.text
    assert "form.live-favorite-form" in response.text
    assert "/api/v1/jobs/${jobId}" in response.text
    assert "syncBadgeMarkup" in response.text
    assert "detail ${detailCount} / contract ${contractCount}" in response.text
    assert "state.metadata.error_reason" in response.text


def test_bid_drawer_partial_renders(client: TestClient) -> None:
    response = client.get("/partials/bids/R26BK00000001-000/drawer")

    assert response.status_code == 200
    assert "공고일반" in response.text
    assert "자격/제한" in response.text
    assert "타임라인" in response.text
