import importlib
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_module(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


@pytest.fixture
def empty_sqlmodel_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "empty-state.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    db_module = _reload_module("app.db")
    db_module.init_db()
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


def test_bids_page_shows_empty_state_when_no_bids(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/bids")

    assert response.status_code == 200
    assert "표시할 공고가 없습니다." in response.text


def test_bids_page_shows_filtered_empty_state_when_filters_applied(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/bids?q=없는공고")

    assert response.status_code == 200
    assert "조건에 맞는 공고가 없습니다. 필터를 조정해보세요." in response.text


def test_favorites_page_shows_empty_state_when_no_favorites(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/favorites")

    assert response.status_code == 200
    assert "표시할 관심 공고가 없습니다." in response.text


def test_operations_page_shows_empty_state_when_no_logs(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/operations")

    assert response.status_code == 200
    assert "표시할 작업 이력이 없습니다." in response.text


def test_prespecs_page_shows_empty_state_when_no_items(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/prespecs")

    assert response.status_code == 200
    assert "표시할 사전 탐색 항목이 없습니다." in response.text


def test_prespecs_page_shows_empty_state_when_filters_remove_all_items(
    empty_sqlmodel_client: TestClient,
) -> None:
    response = empty_sqlmodel_client.get("/prespecs?q=없는항목&stage=사전규격")

    assert response.status_code == 200
    assert "표시할 사전 탐색 항목이 없습니다." in response.text
