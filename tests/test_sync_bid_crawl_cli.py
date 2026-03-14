from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidDetail, SyncJobLog
from app.sync_bid_crawl import main as sync_bid_crawl_main


class StubCrawler:
    def crawl_bid_page(self, detail_url: str):
        from app.services.g2b_bid_page_crawler import CrawledAttachment, CrawledBidPage

        return CrawledBidPage(
            page_title="상세 페이지",
            detail_html="<div>본문</div>",
            text_summary=f"summary:{detail_url}",
            attachments=[
                CrawledAttachment(name="첨부.pdf", url="https://example.com/file.pdf")
            ],
        )


def test_bid_crawl_cli_records_completed_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000123-000",
                bid_no="R26BK00000123",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000123-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    monkeypatch.setattr("app.sync_bid_crawl.engine", engine)
    monkeypatch.setattr("app.sync_bid_crawl.init_db", lambda: None)
    monkeypatch.setattr("app.sync_bid_crawl.G2BBidPageCrawler", StubCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_bid_crawl", "--bid-id", "R26BK00000123-000"]
    )

    sync_bid_crawl_main()

    with Session(engine) as session:
        log = session.exec(select(SyncJobLog)).first()

    assert log is not None
    assert log.job_type == "bid_page_crawl"
    assert log.status == "completed"


def test_bid_crawl_cli_records_failure_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000124-000",
                bid_no="R26BK00000124",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000124-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    class FailingCrawler:
        def crawl_bid_page(self, detail_url: str):
            raise RuntimeError(f"crawl failed: {detail_url}")

    monkeypatch.setattr("app.sync_bid_crawl.engine", engine)
    monkeypatch.setattr("app.sync_bid_crawl.init_db", lambda: None)
    monkeypatch.setattr("app.sync_bid_crawl.G2BBidPageCrawler", FailingCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_bid_crawl", "--bid-id", "R26BK00000124-000"]
    )

    try:
        sync_bid_crawl_main()
    except RuntimeError:
        pass
    else:
        raise AssertionError("RuntimeError was not raised")

    with Session(engine) as session:
        log = session.exec(select(SyncJobLog)).first()

    assert log is not None
    assert log.job_type == "bid_page_crawl"
    assert log.status == "failed"
    assert "failure_category=unexpected" in log.message
    assert "exception_type=RuntimeError" in log.message


def test_bid_crawl_cli_classifies_timeout_and_dom_failures(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000125-000",
                bid_no="R26BK00000125",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000125-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    class TimeoutCrawler:
        def crawl_bid_page(self, detail_url: str):
            raise TimeoutError(f"timeout: {detail_url}")

    monkeypatch.setattr("app.sync_bid_crawl.engine", engine)
    monkeypatch.setattr("app.sync_bid_crawl.init_db", lambda: None)
    monkeypatch.setattr("app.sync_bid_crawl.G2BBidPageCrawler", TimeoutCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_bid_crawl", "--bid-id", "R26BK00000125-000"]
    )

    try:
        sync_bid_crawl_main()
    except Exception:
        pass

    with Session(engine) as session:
        timeout_log = session.exec(select(SyncJobLog)).all()[-1]

    assert timeout_log is not None
    assert "failure_category=browser_timeout" in timeout_log.message

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000126-000",
                bid_no="R26BK00000126",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000126-000", detail_url="https://example.com/detail"
            )
        )
        session.commit()

    class DomCrawler:
        def crawl_bid_page(self, detail_url: str):
            raise RuntimeError(f"selector not found in dom: {detail_url}")

    monkeypatch.setattr("app.sync_bid_crawl.G2BBidPageCrawler", DomCrawler)
    monkeypatch.setattr(
        "sys.argv", ["app.sync_bid_crawl", "--bid-id", "R26BK00000126-000"]
    )

    try:
        sync_bid_crawl_main()
    except Exception:
        pass

    with Session(engine) as session:
        dom_log = session.exec(select(SyncJobLog)).all()[-1]

    assert dom_log is not None
    assert "failure_category=browser_dom" in dom_log.message
