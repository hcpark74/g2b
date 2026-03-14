from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidVersionChange, SyncJobLog
from app.services.g2b_bid_change_history_service import G2BBidChangeHistoryService
from app.sync_bid_change_history import main as sync_bid_change_history_main


class FakeBidChangeHistoryClient:
    def __init__(self, responses: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = responses

    def fetch_bid_change_history(
        self, operation_name: str, **_: Any
    ) -> list[dict[str, Any]]:
        return self.responses.get(operation_name, [])


def test_sync_change_history_persists_bid_version_changes() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK10000001-001",
                bid_no="R26BK10000001",
                bid_seq="001",
                title="정정공고",
                category="용역",
            )
        )
        session.commit()

    client = FakeBidChangeHistoryClient(
        {
            "getBidPblancListInfoChgHstryServc": [
                {
                    "bidNtceNo": "R26BK10000001",
                    "bidNtceOrd": "1",
                    "chgItemNm": "공고명",
                    "chgBfCn": "원공고명",
                    "chgAfCn": "정정공고명",
                    "chgDt": "2026-03-14 09:10:00",
                }
            ]
        }
    )

    with Session(engine) as session:
        result = G2BBidChangeHistoryService(
            session=session, client=client
        ).sync_change_history(bid_ids=["R26BK10000001-001"])

    with Session(engine) as session:
        rows = session.exec(select(BidVersionChange)).all()

    assert result.processed_bid_ids == ["R26BK10000001-001"]
    assert result.fetched_item_count == 1
    assert len(rows) == 1
    assert rows[0].change_item_name == "공고명"
    assert rows[0].before_value == "원공고명"
    assert rows[0].after_value == "정정공고명"
    assert rows[0].source_api_name == "getBidPblancListInfoChgHstryServc"


def test_sync_change_history_cli_records_completed_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK10000002-000",
                bid_no="R26BK10000002",
                bid_seq="000",
                title="원공고",
                category="물품",
            )
        )
        session.commit()

    class StubClient:
        def fetch_bid_change_history(
            self, operation_name: str, **_: Any
        ) -> list[dict[str, Any]]:
            return [
                {
                    "bidNtceNo": "R26BK10000002",
                    "bidNtceOrd": "0",
                    "chgItemNm": "입찰마감일",
                    "chgBfCn": "2026-03-20",
                    "chgAfCn": "2026-03-22",
                }
            ]

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_change_history.engine", engine)
    monkeypatch.setattr("app.sync_bid_change_history.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_bid_change_history.G2BBidPublicInfoClient", StubClient
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_change_history",
            "--bid-id",
            "R26BK10000002-000",
        ],
    )

    sync_bid_change_history_main()

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()
        rows = session.exec(select(BidVersionChange)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "bid_change_history_sync"
    assert logs[0].status == "completed"
    assert logs[0].target == "R26BK10000002-000"
    assert logs[0].message == "processed 1 bids, fetched 1 items"
    assert len(rows) == 1
