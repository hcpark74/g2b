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


def test_bids_page_renders(client: TestClient) -> None:
    response = client.get("/bids")

    assert response.status_code == 200
    assert "입찰 공고 목록" in response.text
    assert "현재 조건 결과 3건" in response.text


def test_bid_drawer_partial_renders(client: TestClient) -> None:
    response = client.get("/partials/bids/R26BK00000001-000/drawer")

    assert response.status_code == 200
    assert "공고일반" in response.text
    assert "자격/제한" in response.text
    assert "타임라인" in response.text
