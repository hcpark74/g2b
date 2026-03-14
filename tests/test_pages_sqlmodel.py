import importlib
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Bid, BidDetail, ContractProcessIntegration, SyncJobLog
from tests.bid_version_fixtures import seed_bid_version_chain, seed_rebid_bid


def _reload_module(name: str):
    module = importlib.import_module(name)
    return importlib.reload(module)


@pytest.fixture
def sqlmodel_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "sqlmodel-test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    _reload_module("app.db")
    seed_module = _reload_module("app.seed_bids")
    seed_module.seed_bids()
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def auto_backend_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "auto-backend-test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "auto")
    monkeypatch.setenv("DEBUG", "false")

    _reload_module("app.config")
    _reload_module("app.db")
    seed_module = _reload_module("app.seed_bids")
    seed_module.seed_bids()
    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def operations_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "operations-test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "auto")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        session.add(
            SyncJobLog(
                job_type="bid_public_info_sync",
                target="getBidPblancListInfoServc",
                status="completed",
                started_at=datetime(2026, 3, 13, 6, 0),
                finished_at=datetime(2026, 3, 13, 6, 4),
                message="fetched 4 bids, upserted 4 bids",
            )
        )
        session.add(
            SyncJobLog(
                job_type="bid_public_info_sync",
                target="getBidPblancListInfoThng",
                status="failed",
                started_at=datetime(2026, 3, 13, 4, 10),
                finished_at=datetime(2026, 3, 13, 4, 11),
                message="operation=getBidPblancListInfoThng exception_type=RuntimeError retry_count=0 status_code=503 detail=temporary http error",
            )
        )
        session.commit()

    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


@pytest.fixture
def operations_batch_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "operations-batch-test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "auto")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        session.add(
            SyncJobLog(
                job_type="phase2_batch_sync",
                target="R26BK01387837-000",
                status="completed",
                started_at=datetime(2026, 3, 14, 2, 12),
                finished_at=datetime(2026, 3, 14, 2, 13),
                message="selection_mode=targeted processed 1 bids detail_items=0 contract_items=1 crawl_attachments=1",
            )
        )
        session.commit()

    main_module = _reload_module("app.main")

    with TestClient(main_module.app) as client:
        yield client


def test_sqlmodel_bids_page_renders(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/bids")

    assert response.status_code == 200
    assert "입찰 공고 목록" in response.text
    assert "전체 3건" in response.text
    assert "마지막 동기화: 2026-03-13 10:00" in response.text


def test_sqlmodel_drawer_uses_summary_text_without_detail_link(
    sqlmodel_client: TestClient,
) -> None:
    response = sqlmodel_client.get("/partials/bids/R26BK00000001-000/drawer")

    assert response.status_code == 200
    assert "본문 요약" in response.text
    assert "나라장터 상세 페이지 열기" not in response.text


def test_sqlmodel_drawer_prefers_crawled_summary_and_excerpt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "crawl-drawer.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        session.add(
            Bid(
                bid_id="R26BK90000002-000",
                bid_no="R26BK90000002",
                bid_seq="000",
                title="크롤링 반영 공고",
                category="용역",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK90000002-000",
                description_text="기존 요약",
                detail_url="https://example.com/detail",
                crawl_data='{"page_title":"상세 페이지","text_summary":"크롤링 추출 요약","attachments":[]}',
            )
        )
        session.commit()

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get("/partials/bids/R26BK90000002-000/drawer")

    assert response.status_code == 200
    assert "크롤링 추출 요약" in response.text
    assert "크롤링 추출 본문" in response.text
    assert "기존 요약" not in response.text


def test_sqlmodel_results_page_uses_contract_process_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "results-sqlmodel.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        session.add(
            Bid(
                bid_id="R26BK90000001-000",
                bid_no="R26BK90000001",
                bid_seq="000",
                title="사후 분석 대상 공고",
                category="용역",
                notice_org="조달청",
                demand_org="한국지능정보원",
            )
        )
        session.add(
            ContractProcessIntegration(
                bid_id="R26BK90000001-000",
                inqry_div=1,
                source_key="R26BK90000001",
                award_company="우수기업",
                award_amount="100000000",
                contract_no="CN-9001",
                contract_name="통합 유지보수 계약",
                contract_date="2026-03-25",
            )
        )
        session.commit()

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get("/results")

    assert response.status_code == 200
    assert "사후 분석 대상 공고" in response.text
    assert "우수기업" in response.text
    assert "100000000" in response.text
    assert "2026-03-25" in response.text


def test_sqlmodel_favorites_page_renders_seeded_favorites(
    sqlmodel_client: TestClient,
) -> None:
    response = sqlmodel_client.get("/favorites")

    assert response.status_code == 200
    assert "관심 공고" in response.text
    assert "R26BK00000001-000" in response.text
    assert "R26BK00000003-000" in response.text


def test_sqlmodel_pages_use_display_bid_no_policy(sqlmodel_client: TestClient) -> None:
    bids_response = sqlmodel_client.get("/bids")
    favorites_response = sqlmodel_client.get("/favorites")

    assert bids_response.status_code == 200
    assert favorites_response.status_code == 200
    assert "R26BK00000001-000" in bids_response.text
    assert "R26BK00000001-000" in favorites_response.text


def test_favorites_page_reuses_filter_bar_and_filters_by_query(
    sqlmodel_client: TestClient,
) -> None:
    response = sqlmodel_client.get("/favorites?q=신기")

    assert response.status_code == 200
    assert 'action="/favorites"' in response.text
    assert 'hx-get="/partials/favorites/table"' in response.text
    assert 'value="신기"' in response.text
    assert "R26BK00000003-000" in response.text
    assert "R26BK00000001-000" not in response.text


def test_favorites_partial_filters_by_status(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/partials/favorites/table?status=favorite")

    assert response.status_code == 200
    assert "R26BK00000003-000" in response.text
    assert "R26BK00000001-000" not in response.text


def test_sqlmodel_bid_drawer_partial_renders(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/partials/bids/R26BK00000001-000/drawer")

    assert response.status_code == 200
    assert "공고일반" in response.text
    assert "자격/제한" in response.text
    assert "참조 기준정보" in response.text
    assert "업종코드:" in response.text
    assert "원천 API:" in response.text
    assert "정보통신공사업법" in response.text
    assert "타임라인" in response.text


def test_sqlmodel_timeline_partial_renders(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/partials/bids/R26BK00000001-000/timeline-inline")

    assert response.status_code == 200
    assert "입찰공고" in response.text
    assert "R26BK00000001-000" in response.text


def test_sqlmodel_drawer_renders_version_fixture_bid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "version-drawer.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        ids = seed_bid_version_chain(session, bid_no="R26BK90000123")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get(f"/partials/bids/{ids['cancellation_bid_id']}/drawer")

    assert response.status_code == 200
    assert ids["cancellation_bid_id"] in response.text
    assert "통합 유지보수 용역 취소공고" in response.text


def test_sqlmodel_bids_page_prefers_latest_effective_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "version-list.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        ids = seed_bid_version_chain(session, bid_no="R26BK90000999")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get("/bids")

    assert response.status_code == 200
    assert ids["revision_bid_id"] in response.text
    assert ids["cancellation_bid_id"] not in response.text
    assert "정정공고" in response.text
    assert (
        "현재 보고 있는 공고는 검토 기준이 되는 최신 유효 차수입니다." in response.text
    )


def test_sqlmodel_drawer_shows_version_badges_and_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "version-drawer-history.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        ids = seed_bid_version_chain(session, bid_no="R26BK90000888")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get(f"/partials/bids/{ids['cancellation_bid_id']}/drawer")

    assert response.status_code == 200
    assert "취소공고" in response.text
    assert "버전 이력" in response.text
    assert ids["original_bid_id"] in response.text
    assert ids["revision_bid_id"] in response.text
    assert "검토 기준" in response.text
    assert "공고 차수 상태" in response.text
    assert "취소 공고 게시" in response.text
    assert "공고상태" in response.text
    assert "데이터구분 입찰공고 / 재입찰번호 000" in response.text
    assert "정정공고" in response.text
    assert 'class="selected-row fw-semibold"' in response.text
    assert "최신 유효 차수 보기" in response.text
    assert ids["revision_bid_id"] in response.text
    assert f'hx-get="/partials/bids/{ids["revision_bid_id"]}/drawer"' in response.text
    assert (
        "최신 차수부터 정렬됩니다. 다른 행을 클릭하면 해당 차수 상세로 이동합니다."
        in response.text
    )


def test_sqlmodel_timeline_partial_shows_revision_or_cancellation_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "version-timeline.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        ids = seed_bid_version_chain(session, bid_no="R26BK90000777")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get(
            f"/partials/bids/{ids['cancellation_bid_id']}/timeline-inline"
        )

    assert response.status_code == 200
    assert "공고 버전" in response.text
    assert "취소 공고 게시" in response.text
    assert "공고상태" in response.text
    assert "데이터구분 입찰공고" in response.text
    assert "재입찰번호 000" in response.text


def test_sqlmodel_drawer_shows_rebid_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "rebid-drawer.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        rebid_id = seed_rebid_bid(session, bid_no="R26BK90000555")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get(f"/partials/bids/{rebid_id}/drawer")

    assert response.status_code == 200
    assert "재공고" in response.text
    assert (
        "현재 보고 있는 공고는 재공고 차수입니다. 이전 유찰 이력과 재공고 사유를 함께 확인하세요."
        in response.text
    )
    assert "재공고 게시" in response.text


def test_auto_backend_prefers_seeded_sqlmodel_data(
    auto_backend_client: TestClient,
) -> None:
    response = auto_backend_client.get("/bids")

    assert response.status_code == 200
    assert "입찰 공고 목록" in response.text
    assert "R26BK00000001-000" in response.text
    assert "전남소방본부 구급소모품 구매" in response.text
    assert "마지막 동기화: 2026-03-13 10:00" in response.text


def test_sqlmodel_bids_page_filters_by_query_string(
    sqlmodel_client: TestClient,
) -> None:
    response = sqlmodel_client.get("/bids?q=구급소모품")

    assert response.status_code == 200
    assert "전남소방본부 구급소모품 구매" in response.text
    assert (
        "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역" not in response.text
    )


def test_sqlmodel_bids_page_filters_favorites_only(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/bids?favorites=1")

    assert response.status_code == 200
    assert "R26BK00000001-000" in response.text
    assert "R26BK00000003-000" in response.text
    assert "R26BK00000002-000" not in response.text


def test_bids_filter_bar_preserves_query_params(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get(
        "/bids?q=구급소모품&status=collected&favorites=1&include_versions=1"
    )

    assert response.status_code == 200
    assert 'value="구급소모품"' in response.text
    assert '<option value="collected" selected>' in response.text
    assert 'id="favorites-only"' in response.text
    assert 'id="include-versions"' in response.text
    assert "checked" in response.text


def test_favorites_page_hides_version_filter(sqlmodel_client: TestClient) -> None:
    response = sqlmodel_client.get("/favorites")

    assert response.status_code == 200
    assert 'id="favorites-only"' not in response.text
    assert 'id="include-versions"' not in response.text
    assert "현재는 키워드, 상태 필터를 지원합니다." in response.text


def test_sqlmodel_bids_page_can_include_historical_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "version-filter.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BID_DATA_BACKEND", "sqlmodel")
    monkeypatch.setenv("DEBUG", "false")

    db_module = _reload_module("app.db")
    _reload_module("app.models")
    db_module.init_db()

    with Session(db_module.engine) as session:
        ids = seed_bid_version_chain(session, bid_no="R26BK90000666")

    main_module = _reload_module("app.main")
    with TestClient(main_module.app) as client:
        response = client.get("/bids?include_versions=1")

    assert response.status_code == 200
    assert ids["original_bid_id"] in response.text
    assert ids["revision_bid_id"] in response.text
    assert ids["cancellation_bid_id"] in response.text


def test_operations_page_prefers_db_logs(operations_client: TestClient) -> None:
    response = operations_client.get("/operations")

    assert response.status_code == 200
    assert "bid_public_info_sync" in response.text
    assert "getBidPblancListInfoServc" in response.text
    assert "마지막 동기화: 2026-03-13 06:04" in response.text
    assert "조회" in response.text
    assert "4건" in response.text
    assert "반영" in response.text
    assert "오퍼레이션" in response.text
    assert "예외" in response.text
    assert "재시도" in response.text
    assert "HTTP" in response.text
    assert "상세" in response.text
    assert "temporary" in response.text


def test_operations_page_filters_failed_status(operations_client: TestClient) -> None:
    response = operations_client.get("/operations?status=failed")

    assert response.status_code == 200
    assert "getBidPblancListInfoThng" in response.text
    assert "temporary" in response.text
    assert "getBidPblancListInfoServc" not in response.text
    assert "fetched 4 bids, upserted 4 bids" not in response.text


def test_operations_page_filters_by_job_type(operations_client: TestClient) -> None:
    response = operations_client.get("/operations?job_type=bid_public_info_sync")

    assert response.status_code == 200
    assert "작업유형 필터" in response.text
    assert "bid_public_info_sync" in response.text


def test_operations_page_filters_by_status_and_job_type(
    operations_client: TestClient,
) -> None:
    response = operations_client.get(
        "/operations?status=failed&job_type=bid_public_info_sync"
    )

    assert response.status_code == 200
    assert "getBidPblancListInfoThng" in response.text
    assert "temporary" in response.text
    assert "getBidPblancListInfoServc" not in response.text


def test_operations_page_formats_phase2_batch_log(
    operations_batch_client: TestClient,
) -> None:
    response = operations_batch_client.get("/operations")

    assert response.status_code == 200
    assert "phase2_batch_sync" in response.text
    assert "선별모드" in response.text
    assert "targeted" in response.text
    assert "처리 공고" in response.text
    assert "1건" in response.text
    assert "상세 보강" in response.text
    assert "계약과정" in response.text
    assert "크롤링 첨부" in response.text
