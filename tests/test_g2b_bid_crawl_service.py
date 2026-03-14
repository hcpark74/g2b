import json

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Attachment, Bid, BidDetail
from app.services.g2b_bid_crawl_service import G2BBidCrawlService
from app.services.g2b_bid_page_crawler import CrawledAttachment, CrawledBidPage


class FakeBidPageCrawler:
    def crawl_bid_page(self, detail_url: str) -> CrawledBidPage:
        assert detail_url == "https://example.com/bids/R26BK00000001-000"
        return CrawledBidPage(
            page_title="상세 페이지",
            detail_html="<div>본문</div>",
            text_summary="크롤링 요약",
            attachments=[
                CrawledAttachment(
                    name="제안요청서.pdf", url="https://example.com/file1.pdf"
                ),
                CrawledAttachment(
                    name="과업지시서.hwp", url="https://example.com/file2.hwp"
                ),
            ],
        )


def test_bid_crawl_service_updates_crawl_data_and_attachments() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000001-000",
                bid_no="R26BK00000001",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000001-000",
                detail_url="https://example.com/bids/R26BK00000001-000",
            )
        )
        session.commit()

    with Session(engine) as session:
        result = G2BBidCrawlService(
            session=session, crawler=FakeBidPageCrawler()
        ).crawl_bids(bid_ids=["R26BK00000001-000"])

    with Session(engine) as session:
        bid_detail = session.get(BidDetail, "R26BK00000001-000")
        attachments = session.exec(
            select(Attachment).order_by(Attachment.attachment_id)
        ).all()

    assert result.processed_bid_ids == ["R26BK00000001-000"]
    assert result.attachment_count == 2
    assert bid_detail is not None
    assert bid_detail.description_text == "크롤링 요약"
    assert bid_detail.detail_hash is not None
    assert json.loads(bid_detail.crawl_data or "{}")["page_title"] == "상세 페이지"
    assert json.loads(bid_detail.crawl_data or "{}")["text_summary"] == "크롤링 요약"
    assert [item.name for item in attachments] == ["제안요청서.pdf", "과업지시서.hwp"]
    assert all(item.source == "playwright_detail" for item in attachments)
    assert all(item.content_hash for item in attachments)


def test_bid_crawl_service_replaces_removed_playwright_attachments() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000002-000",
                bid_no="R26BK00000002",
                bid_seq="000",
                title="크롤링 대상",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000002-000",
                detail_url="https://example.com/bids/R26BK00000001-000",
            )
        )
        session.add(
            Attachment(
                attachment_id="R26BK00000002-000:crawl:1",
                bid_id="R26BK00000002-000",
                name="이전첨부.pdf",
                source="playwright_detail",
                download_url="https://example.com/old.pdf",
            )
        )
        session.commit()

    with Session(engine) as session:
        G2BBidCrawlService(session=session, crawler=FakeBidPageCrawler()).crawl_bids(
            bid_ids=["R26BK00000002-000"]
        )

    with Session(engine) as session:
        attachments = session.exec(
            select(Attachment).where(Attachment.bid_id == "R26BK00000002-000")
        ).all()

    assert [item.name for item in attachments] == ["제안요청서.pdf", "과업지시서.hwp"]
