from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidDetail, SyncJobLog
from app.sync_phase2_batch import main as sync_phase2_batch_main


def test_phase2_batch_cli_records_completed_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00002001-000",
                bid_no="R26BK00002001",
                bid_seq="000",
                title="배치 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00002001-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    class StubDetailClient:
        def fetch_bid_detail_list(
            self, operation_name: str, **_: Any
        ) -> list[dict[str, Any]]:
            return []

        def fetch_bid_change_history(
            self, operation_name: str, **_: Any
        ) -> list[dict[str, Any]]:
            return []

        def close(self) -> None:
            return None

    class StubContractClient:
        def fetch_contract_process(self, **_: Any) -> list[dict[str, Any]]:
            return []

        def close(self) -> None:
            return None

    class StubIndustryClient:
        def fetch_industry_base_law(self, **_: Any) -> list[dict[str, Any]]:
            return []

        def close(self) -> None:
            return None

    class StubCrawler:
        def crawl_bid_page(self, detail_url: str):
            from app.services.g2b_bid_page_crawler import CrawledBidPage

            return CrawledBidPage(
                page_title="t",
                detail_html="<div></div>",
                text_summary="s",
                attachments=[],
            )

    monkeypatch.setattr("app.sync_phase2_batch.engine", engine)
    monkeypatch.setattr("app.sync_phase2_batch.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BBidPublicInfoClient", StubDetailClient
    )
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BContractProcessClient", StubContractClient
    )
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BIndustryInfoClient", StubIndustryClient
    )
    monkeypatch.setattr("app.sync_phase2_batch.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_phase2_batch", "--bid-id", "R26BK00002001-000"]
    )

    sync_phase2_batch_main()

    with Session(engine) as session:
        log = session.exec(select(SyncJobLog)).first()

    assert log is not None
    assert log.job_type == "phase2_batch_sync"
    assert log.status == "completed"
    assert "processed 1 bids" in log.message
    assert "change_history_items=0" in log.message
    assert "reference_items=0" in log.message


def test_phase2_batch_cli_records_failure_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00002002-000",
                bid_no="R26BK00002002",
                bid_seq="000",
                title="배치 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00002002-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    class StubDetailClient:
        def fetch_bid_detail_list(
            self, operation_name: str, **_: Any
        ) -> list[dict[str, Any]]:
            return []

        def fetch_bid_change_history(
            self, operation_name: str, **_: Any
        ) -> list[dict[str, Any]]:
            return []

        def close(self) -> None:
            return None

    class FailingContractClient:
        def fetch_contract_process(self, **_: Any) -> list[dict[str, Any]]:
            raise RuntimeError("mock batch failure")

        def close(self) -> None:
            return None

    class StubIndustryClient:
        def fetch_industry_base_law(self, **_: Any) -> list[dict[str, Any]]:
            return []

        def close(self) -> None:
            return None

    class StubCrawler:
        def crawl_bid_page(self, detail_url: str):
            from app.services.g2b_bid_page_crawler import CrawledBidPage

            return CrawledBidPage(
                page_title="t",
                detail_html="<div></div>",
                text_summary="s",
                attachments=[],
            )

    monkeypatch.setattr("app.sync_phase2_batch.engine", engine)
    monkeypatch.setattr("app.sync_phase2_batch.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BBidPublicInfoClient", StubDetailClient
    )
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BContractProcessClient", FailingContractClient
    )
    monkeypatch.setattr(
        "app.sync_phase2_batch.G2BIndustryInfoClient", StubIndustryClient
    )
    monkeypatch.setattr("app.sync_phase2_batch.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_phase2_batch", "--bid-id", "R26BK00002002-000"]
    )

    try:
        sync_phase2_batch_main()
    except RuntimeError as exc:
        assert "mock batch failure" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")

    with Session(engine) as session:
        log = session.exec(select(SyncJobLog)).first()

    assert log is not None
    assert log.job_type == "phase2_batch_sync"
    assert log.status == "failed"
    assert "failure_category=unexpected" in log.message
