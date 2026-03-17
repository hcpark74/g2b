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
    assert "현재 조건 결과 3건" in response.text


def test_bid_drawer_partial_renders(client: TestClient) -> None:
    response = client.get("/partials/bids/R26BK00000001-000/drawer")

    assert response.status_code == 200
    assert "공고일반" in response.text
    assert "자격/제한" in response.text
    assert "타임라인" in response.text
