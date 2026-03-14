from typing import Any

import httpx
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidDetail, SyncJobLog
from app.services.g2b_bid_sync_service import (
    BidPublicInfoSyncOperationError,
    G2BBidPublicInfoSyncService,
)
from app.sync_bid_public_info import main as sync_bid_public_info_main


class FakeBidPublicInfoClient:
    def __init__(self, responses: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = responses

    def fetch_bid_list(self, operation_name: str, **_: Any) -> list[dict[str, Any]]:
        return self.responses.get(operation_name, [])


def test_sync_bid_notices_persists_bids_and_raw_payload() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    client = FakeBidPublicInfoClient(
        {
            "getBidPblancListInfoServc": [
                {
                    "bidNtceNo": "R26BK00000123",
                    "bidNtceOrd": "1",
                    "bidNtceNm": "AI 상담 시스템 유지보수",
                    "ntceInsttNm": "조달청",
                    "dminsttNm": "한국지능정보원",
                    "bidNtceDt": "2026-03-13 09:00:00",
                    "bidClseDt": "2026-03-20 18:00",
                    "presmptPrce": "120,000,000",
                    "opengDt": "2026-03-20 19:00",
                    "bidNtceDtlUrl": "https://example.com/bids/123",
                }
            ]
        }
    )

    with Session(engine) as session:
        service = G2BBidPublicInfoSyncService(session=session, client=client)
        result = service.sync_bid_notices(
            inqry_bgn_dt="202603130000",
            inqry_end_dt="202603132359",
            operations=("getBidPblancListInfoServc",),
        )

    with Session(engine) as session:
        bid = session.get(Bid, "R26BK00000123-001")
        bid_detail = session.get(BidDetail, "R26BK00000123-001")
        bids = session.exec(select(Bid)).all()

    assert result.fetched_count == 1
    assert result.upserted_count == 1
    assert result.bid_ids == ["R26BK00000123-001"]
    assert len(bids) == 1
    assert bid is not None
    assert bid.title == "AI 상담 시스템 유지보수"
    assert bid.category == "용역"
    assert bid.notice_org == "조달청"
    assert bid.demand_org == "한국지능정보원"
    assert bid.budget_amount == 120000000
    assert bid.source_api_name == "getBidPblancListInfoServc"
    assert bid.last_synced_at is not None
    assert bid_detail is not None
    assert bid_detail.description_text is None
    assert bid_detail.detail_url == "https://example.com/bids/123"
    assert '"bidNtceNo": "R26BK00000123"' in (bid_detail.raw_api_data or "")


def test_sync_bid_notices_updates_existing_bid_without_duplicate_insert() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    initial_client = FakeBidPublicInfoClient(
        {
            "getBidPblancListInfoThng": [
                {
                    "bidNtceNo": "R26BK00000456",
                    "bidNtceOrd": "0",
                    "bidNtceNm": "초기 공고명",
                    "presmptPrce": "10,000",
                }
            ]
        }
    )
    update_client = FakeBidPublicInfoClient(
        {
            "getBidPblancListInfoThng": [
                {
                    "bidNtceNo": "R26BK00000456",
                    "bidNtceOrd": "0",
                    "bidNtceNm": "수정된 공고명",
                    "presmptPrce": "12,000",
                }
            ]
        }
    )

    with Session(engine) as session:
        G2BBidPublicInfoSyncService(
            session=session, client=initial_client
        ).sync_bid_notices(
            inqry_bgn_dt="202603130000",
            inqry_end_dt="202603132359",
            operations=("getBidPblancListInfoThng",),
        )

    with Session(engine) as session:
        G2BBidPublicInfoSyncService(
            session=session, client=update_client
        ).sync_bid_notices(
            inqry_bgn_dt="202603130000",
            inqry_end_dt="202603132359",
            operations=("getBidPblancListInfoThng",),
        )

    with Session(engine) as session:
        bids = session.exec(select(Bid)).all()
        bid = session.get(Bid, "R26BK00000456-000")

    assert len(bids) == 1
    assert bid is not None
    assert bid.title == "수정된 공고명"
    assert bid.budget_amount == 12000
    assert bid.category == "물품"


def test_sync_bid_notices_sets_version_normalization_fields() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    client = FakeBidPublicInfoClient(
        {
            "getBidPblancListInfoServc": [
                {
                    "bidNtceNo": "R26BK00000777",
                    "bidNtceOrd": "0",
                    "bidNtceNm": "원공고",
                },
                {
                    "bidNtceNo": "R26BK00000777",
                    "bidNtceOrd": "1",
                    "bidNtceNm": "정정공고",
                    "chgRsn": "마감일 정정",
                },
                {
                    "bidNtceNo": "R26BK00000777",
                    "bidNtceOrd": "2",
                    "bidNtceNm": "취소공고",
                    "bidNtceCnclYn": "Y",
                    "bidNtceCnclRsn": "사업 취소",
                },
            ]
        }
    )

    with Session(engine) as session:
        service = G2BBidPublicInfoSyncService(session=session, client=client)
        service.sync_bid_notices(
            inqry_bgn_dt="202603130000",
            inqry_end_dt="202603132359",
            operations=("getBidPblancListInfoServc",),
        )

    with Session(engine) as session:
        original = session.get(Bid, "R26BK00000777-000")
        revision = session.get(Bid, "R26BK00000777-001")
        cancellation = session.get(Bid, "R26BK00000777-002")

    assert original is not None
    assert revision is not None
    assert cancellation is not None
    assert original.notice_version_type == "original"
    assert original.parent_bid_id is None
    assert original.is_latest_version is False
    assert original.is_effective_version is True
    assert revision.notice_version_type == "revision"
    assert revision.parent_bid_id == "R26BK00000777-000"
    assert revision.is_latest_version is False
    assert revision.is_effective_version is True
    assert revision.version_reason == "마감일 정정"
    assert cancellation.notice_version_type == "cancellation"
    assert cancellation.parent_bid_id == "R26BK00000777-001"
    assert cancellation.is_latest_version is True
    assert cancellation.is_effective_version is False
    assert cancellation.version_reason == "사업 취소"


def test_sync_cli_records_completed_operation_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    class StubClient:
        def fetch_bid_list(self, operation_name: str, **_: Any) -> list[dict[str, Any]]:
            return [
                {
                    "bidNtceNo": "R26BK00000999",
                    "bidNtceOrd": "1",
                    "bidNtceNm": "운영로그 검증 공고",
                }
            ]

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_public_info.engine", engine)
    monkeypatch.setattr("app.sync_bid_public_info.init_db", lambda: None)
    monkeypatch.setattr("app.sync_bid_public_info.G2BBidPublicInfoClient", StubClient)
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_public_info",
            "--begin",
            "202603130000",
            "--end",
            "202603132359",
            "--operation",
            "getBidPblancListInfoServc",
        ],
    )

    sync_bid_public_info_main()

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "bid_public_info_sync"
    assert logs[0].status == "completed"
    assert logs[0].target == "getBidPblancListInfoServc"
    assert "fetched 1 bids, upserted 1 bids" == logs[0].message


def test_sync_cli_records_failed_operation_details(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    class FailingClient:
        def fetch_bid_list(self, operation_name: str, **_: Any) -> list[dict[str, Any]]:
            if operation_name == "getBidPblancListInfoThng":
                raise RuntimeError("mock upstream timeout")
            return []

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_public_info.engine", engine)
    monkeypatch.setattr("app.sync_bid_public_info.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_bid_public_info.G2BBidPublicInfoClient", FailingClient
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_public_info",
            "--begin",
            "202603130000",
            "--end",
            "202603132359",
            "--operation",
            "getBidPblancListInfoThng",
        ],
    )

    try:
        sync_bid_public_info_main()
    except RuntimeError as exc:
        assert "mock upstream timeout" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].target == "getBidPblancListInfoThng"
    assert logs[0].message == (
        "operation=getBidPblancListInfoThng "
        "failure_category=unexpected "
        "exception_type=RuntimeError "
        "retry_count=0 "
        "detail=mock upstream timeout"
    )


def test_sync_cli_records_http_status_code_in_failure_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    class FailingHttpClient:
        def fetch_bid_list(self, operation_name: str, **_: Any) -> list[dict[str, Any]]:
            request = httpx.Request("GET", f"https://example.com/{operation_name}")
            response = httpx.Response(503, request=request)
            raise httpx.HTTPStatusError(
                "service unavailable", request=request, response=response
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_public_info.engine", engine)
    monkeypatch.setattr("app.sync_bid_public_info.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_bid_public_info.G2BBidPublicInfoClient", FailingHttpClient
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_public_info",
            "--begin",
            "202603130000",
            "--end",
            "202603132359",
            "--operation",
            "getBidPblancListInfoServc",
        ],
    )

    try:
        sync_bid_public_info_main()
    except BidPublicInfoSyncOperationError as exc:
        assert exc.status_code == 503
        assert isinstance(exc.cause, httpx.HTTPStatusError)
    else:
        raise AssertionError("BidPublicInfoSyncOperationError was not raised")

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].target == "getBidPblancListInfoServc"
    assert logs[0].message == (
        "operation=getBidPblancListInfoServc "
        "failure_category=api_http "
        "exception_type=HTTPStatusError "
        "retry_count=0 "
        "status_code=503 "
        "detail=service unavailable"
    )
