from datetime import datetime

from sqlmodel import Session

from app.models import Bid, BidDetail, BidVersionChange


def seed_bid_version_chain(
    session: Session,
    *,
    bid_no: str = "R26BK99990001",
) -> dict[str, str]:
    original_id = f"{bid_no}-000"
    revision_id = f"{bid_no}-001"
    cancellation_id = f"{bid_no}-002"

    session.add(
        Bid(
            bid_id=original_id,
            bid_no=bid_no,
            bid_seq="000",
            title="통합 유지보수 용역",
            category="용역",
            notice_org="조달청",
            demand_org="한국지능정보원",
            posted_at=datetime(2026, 3, 10, 9, 0),
            closed_at=datetime(2026, 3, 18, 14, 0),
            last_changed_at=datetime(2026, 3, 10, 9, 0),
        )
    )
    session.add(
        BidDetail(
            bid_id=original_id,
            description_text="원공고 본문",
            detail_url=f"https://example.com/bids/{original_id}",
        )
    )

    session.add(
        Bid(
            bid_id=revision_id,
            bid_no=bid_no,
            bid_seq="001",
            title="통합 유지보수 용역 정정공고",
            category="용역",
            notice_org="조달청",
            demand_org="한국지능정보원",
            posted_at=datetime(2026, 3, 12, 10, 30),
            closed_at=datetime(2026, 3, 20, 14, 0),
            last_changed_at=datetime(2026, 3, 12, 10, 30),
        )
    )
    session.add(
        BidDetail(
            bid_id=revision_id,
            description_text="정정공고 본문",
            detail_url=f"https://example.com/bids/{revision_id}",
        )
    )
    session.add(
        BidVersionChange(
            change_id=f"{revision_id}:001",
            bid_id=revision_id,
            bid_no=bid_no,
            bid_seq="001",
            change_data_div_name="입찰공고",
            change_item_name="공고명",
            before_value="통합 유지보수 용역",
            after_value="통합 유지보수 용역 정정공고",
            changed_at="2026-03-12 10:30",
            rbid_no="000",
            source_api_name="getBidPblancListInfoChgHstryServc",
        )
    )
    session.add(
        BidVersionChange(
            change_id=f"{revision_id}:002",
            bid_id=revision_id,
            bid_no=bid_no,
            bid_seq="001",
            change_data_div_name="입찰공고",
            change_item_name="입찰마감일",
            before_value="2026-03-18 14:00",
            after_value="2026-03-20 14:00",
            changed_at="2026-03-12 10:31",
            rbid_no="000",
            source_api_name="getBidPblancListInfoChgHstryServc",
        )
    )

    session.add(
        Bid(
            bid_id=cancellation_id,
            bid_no=bid_no,
            bid_seq="002",
            title="통합 유지보수 용역 취소공고",
            category="용역",
            notice_org="조달청",
            demand_org="한국지능정보원",
            status="archived",
            posted_at=datetime(2026, 3, 13, 8, 45),
            closed_at=datetime(2026, 3, 20, 14, 0),
            last_changed_at=datetime(2026, 3, 13, 8, 45),
        )
    )
    session.add(
        BidDetail(
            bid_id=cancellation_id,
            description_text="취소공고 본문",
            detail_url=f"https://example.com/bids/{cancellation_id}",
        )
    )
    session.add(
        BidVersionChange(
            change_id=f"{cancellation_id}:001",
            bid_id=cancellation_id,
            bid_no=bid_no,
            bid_seq="002",
            change_data_div_name="입찰공고",
            change_item_name="공고상태",
            before_value="정정공고",
            after_value="취소공고",
            changed_at="2026-03-13 08:45",
            rbid_no="000",
            source_api_name="getBidPblancListInfoChgHstryServc",
        )
    )
    session.commit()

    return {
        "bid_no": bid_no,
        "original_bid_id": original_id,
        "revision_bid_id": revision_id,
        "cancellation_bid_id": cancellation_id,
    }


def seed_rebid_bid(
    session: Session,
    *,
    bid_no: str = "R26BK99990002",
) -> str:
    rebid_id = f"{bid_no}-001"
    session.add(
        Bid(
            bid_id=rebid_id,
            bid_no=bid_no,
            bid_seq="001",
            title="통합 유지보수 용역 재공고",
            category="용역",
            notice_org="조달청",
            demand_org="한국지능정보원",
            notice_version_type="rebid",
            version_reason="유찰로 인한 재공고",
            posted_at=datetime(2026, 3, 14, 9, 0),
            closed_at=datetime(2026, 3, 22, 14, 0),
            last_changed_at=datetime(2026, 3, 14, 9, 0),
        )
    )
    session.add(
        BidDetail(
            bid_id=rebid_id,
            description_text="재공고 본문",
            detail_url=f"https://example.com/bids/{rebid_id}",
        )
    )
    session.commit()
    return rebid_id
