from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, SyncJobLog
from app.sync_bid_detail_enrichment import main as sync_bid_detail_enrichment_main


def test_detail_enrichment_cli_records_completed_operation_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000888-000",
                bid_no="R26BK00000888",
                bid_seq="000",
                title="상세 보강 대상",
            )
        )
        session.commit()

    class StubClient:
        def fetch_bid_detail_list(
            self,
            operation_name: str,
            *,
            bid_ntce_no: str,
            page_no: int = 1,
            num_of_rows: int = 100,
        ) -> list[dict[str, Any]]:
            _ = (operation_name, bid_ntce_no, page_no, num_of_rows)
            return []

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_detail_enrichment.engine", engine)
    monkeypatch.setattr("app.sync_bid_detail_enrichment.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_bid_detail_enrichment.G2BBidPublicInfoClient", StubClient
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_detail_enrichment",
            "--bid-id",
            "R26BK00000888-000",
            "--operation",
            "getBidPblancListInfoLicenseLimit",
        ],
    )

    sync_bid_detail_enrichment_main()

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "bid_detail_enrichment"
    assert logs[0].status == "completed"
    assert logs[0].target == "R26BK00000888-000"
    assert (
        logs[0].message
        == "operations=getBidPblancListInfoLicenseLimit selection_mode=targeted processed 1 bids, fetched 0 items"
    )


def test_detail_enrichment_cli_records_failure_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000889-000",
                bid_no="R26BK00000889",
                bid_seq="000",
                title="상세 보강 대상",
            )
        )
        session.commit()

    class FailingClient:
        def fetch_bid_detail_list(
            self,
            operation_name: str,
            *,
            bid_ntce_no: str,
            page_no: int = 1,
            num_of_rows: int = 100,
        ) -> list[dict[str, Any]]:
            _ = (operation_name, bid_ntce_no, page_no, num_of_rows)
            raise RuntimeError("mock detail enrichment failure")

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_bid_detail_enrichment.engine", engine)
    monkeypatch.setattr("app.sync_bid_detail_enrichment.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_bid_detail_enrichment.G2BBidPublicInfoClient", FailingClient
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "app.sync_bid_detail_enrichment",
            "--bid-id",
            "R26BK00000889-000",
            "--operation",
            "getBidPblancListInfoLicenseLimit",
        ],
    )

    try:
        sync_bid_detail_enrichment_main()
    except RuntimeError as exc:
        assert "mock detail enrichment failure" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "bid_detail_enrichment"
    assert logs[0].status == "failed"
    assert logs[0].target == "R26BK00000889-000"
    assert "operations=getBidPblancListInfoLicenseLimit" in logs[0].message
    assert "selection_mode=targeted" in logs[0].message
    assert "failure_category=unexpected" in logs[0].message
    assert "exception_type=RuntimeError" in logs[0].message
