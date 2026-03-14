from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    Attachment,
    Bid,
    BidDetail,
    BidLicenseLimit,
    BidParticipationRegion,
    BidPurchaseItem,
)
from app.services.g2b_bid_detail_enrichment_service import G2BBidDetailEnrichmentService


class FakeBidDetailClient:
    def __init__(self, responses: dict[str, list[dict[str, str]]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def fetch_bid_detail_list(
        self,
        operation_name: str,
        *,
        bid_ntce_no: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]:
        _ = (bid_ntce_no, page_no, num_of_rows)
        self.calls.append((operation_name, bid_ntce_no))
        response = self.responses.get(operation_name, [])
        if isinstance(response, dict):
            return response.get(bid_ntce_no, [])
        return response


def test_detail_enrichment_persists_license_regions_and_attachments() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000123-000",
                bid_no="R26BK00000123",
                bid_seq="000",
                title="테스트 공고",
                category="용역",
            )
        )
        session.commit()

    client = FakeBidDetailClient(
        {
            "getBidPblancListInfoLicenseLimit": [
                {"licnsNm": "소프트웨어사업자(컴퓨터관련서비스사업)"}
            ],
            "getBidPblancListInfoPrtcptPsblRgn": [{"prtcptPsblRgnNm": "전국"}],
            "getBidPblancListInfoEorderAtchFileInfo": [
                {
                    "atchFileNm": "과업지시서.pdf",
                    "atchFileUrl": "https://example.com/files/1",
                    "fileTypeNm": "PDF",
                }
            ],
        }
    )

    with Session(engine) as session:
        result = G2BBidDetailEnrichmentService(
            session=session, client=client
        ).enrich_bids(
            bid_ids=["R26BK00000123-000"],
            operations=(
                "getBidPblancListInfoLicenseLimit",
                "getBidPblancListInfoPrtcptPsblRgn",
                "getBidPblancListInfoEorderAtchFileInfo",
            ),
        )

    with Session(engine) as session:
        license_limits = session.exec(select(BidLicenseLimit)).all()
        regions = session.exec(select(BidParticipationRegion)).all()
        attachments = session.exec(select(Attachment)).all()

    assert result.processed_bid_ids == ["R26BK00000123-000"]
    assert result.fetched_item_count == 3
    assert [item.license_name for item in license_limits] == [
        "소프트웨어사업자(컴퓨터관련서비스사업)"
    ]
    assert [item.region_name for item in regions] == ["전국"]
    assert attachments[0].name == "과업지시서.pdf"
    assert attachments[0].source == "getBidPblancListInfoEorderAtchFileInfo"
    assert attachments[0].content_hash is not None


def test_detail_enrichment_replaces_existing_items_for_same_source() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000456-000",
                bid_no="R26BK00000456",
                bid_seq="000",
                title="테스트 공고",
            )
        )
        session.add(
            Attachment(
                attachment_id="old-1",
                bid_id="R26BK00000456-000",
                name="이전 첨부",
                source="getBidPblancListInfoEorderAtchFileInfo",
                download_url="https://example.com/old",
            )
        )
        session.commit()

    client = FakeBidDetailClient(
        {
            "getBidPblancListInfoEorderAtchFileInfo": [
                {
                    "atchFileNm": "새 첨부",
                    "atchFileUrl": "https://example.com/new",
                }
            ]
        }
    )

    with Session(engine) as session:
        G2BBidDetailEnrichmentService(session=session, client=client).enrich_bids(
            bid_ids=["R26BK00000456-000"],
            operations=("getBidPblancListInfoEorderAtchFileInfo",),
        )

    with Session(engine) as session:
        attachments = session.exec(select(Attachment).order_by(Attachment.name)).all()

    assert [item.name for item in attachments] == ["새 첨부"]


def test_detail_enrichment_persists_eorder_attachment_fields() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000999-000",
                bid_no="R26BK00000999",
                bid_seq="000",
                title="이발주 첨부 공고",
            )
        )
        session.commit()

    client = FakeBidDetailClient(
        {
            "getBidPblancListInfoEorderAtchFileInfo": [
                {
                    "eorderAtchFileNm": "제안요청서.hwp",
                    "eorderAtchFileUrl": "https://example.com/eorder/1",
                    "eorderDocDivNm": "제안요청서",
                }
            ]
        }
    )

    with Session(engine) as session:
        G2BBidDetailEnrichmentService(session=session, client=client).enrich_bids(
            bid_ids=["R26BK00000999-000"],
            operations=("getBidPblancListInfoEorderAtchFileInfo",),
        )

    with Session(engine) as session:
        attachments = session.exec(select(Attachment)).all()

    assert len(attachments) == 1
    assert attachments[0].name == "제안요청서.hwp"
    assert attachments[0].download_url == "https://example.com/eorder/1"
    assert attachments[0].file_type == "제안요청서"


def test_detail_enrichment_persists_purchase_items() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000789-000",
                bid_no="R26BK00000789",
                bid_seq="000",
                title="물품 공고",
                category="물품",
            )
        )
        session.commit()

    client = FakeBidDetailClient(
        {
            "getBidPblancListInfoThngPurchsObjPrdct": [
                {
                    "prdctClsfcNo": "4214252301",
                    "prdctClsfcNoNm": "구급용소모품세트",
                    "purchsQty": "1식",
                    "dlvrCndtnNm": "수요기관희망장소입고도",
                }
            ]
        }
    )

    with Session(engine) as session:
        G2BBidDetailEnrichmentService(session=session, client=client).enrich_bids(
            bid_ids=["R26BK00000789-000"],
            operations=("getBidPblancListInfoThngPurchsObjPrdct",),
        )

    with Session(engine) as session:
        purchase_items = session.exec(select(BidPurchaseItem)).all()

    assert len(purchase_items) == 1
    assert purchase_items[0].item_code == "4214252301"
    assert purchase_items[0].item_name == "구급용소모품세트"
    assert purchase_items[0].quantity == "1식"


def test_detail_enrichment_targeted_selection_only_processes_matching_bids() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK10000001-000",
                bid_no="R26BK10000001",
                bid_seq="000",
                title="관심 공고",
                is_favorite=True,
                created_at=now - timedelta(days=30),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK10000002-000",
                bid_no="R26BK10000002",
                bid_seq="000",
                title="최근 변경 공고",
                last_changed_at=now - timedelta(days=1),
                created_at=now - timedelta(days=30),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK10000003-000",
                bid_no="R26BK10000003",
                bid_seq="000",
                title="오래된 수집완료 공고",
                status="collected",
                created_at=now - timedelta(days=30),
            )
        )
        session.commit()

    client = FakeBidDetailClient({"getBidPblancListInfoLicenseLimit": []})

    with Session(engine) as session:
        result = G2BBidDetailEnrichmentService(
            session=session, client=client
        ).enrich_bids(
            operations=("getBidPblancListInfoLicenseLimit",),
            selection_mode="targeted",
            recent_days=7,
        )

    assert result.processed_bid_ids == ["R26BK10000001-000", "R26BK10000002-000"]


def test_detail_enrichment_falls_back_to_unified_notice_number() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK20000001-000",
                bid_no="R26BK20000001",
                bid_seq="000",
                title="통합공고 fallback 테스트",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK20000001-000",
                raw_api_data='{"bidNtceNo":"R26BK20000001","untyNtceNo":"UNIFIED-2001"}',
            )
        )
        session.commit()

    client = FakeBidDetailClient(
        {
            "getBidPblancListInfoPrtcptPsblRgn": {
                "R26BK20000001": [],
                "UNIFIED-2001": [{"prtcptPsblRgnNm": "서울특별시"}],
            }
        }
    )

    with Session(engine) as session:
        result = G2BBidDetailEnrichmentService(
            session=session, client=client
        ).enrich_bids(
            bid_ids=["R26BK20000001-000"],
            operations=("getBidPblancListInfoPrtcptPsblRgn",),
        )

    with Session(engine) as session:
        regions = session.exec(select(BidParticipationRegion)).all()

    assert result.fetched_item_count == 1
    assert client.calls == [
        ("getBidPblancListInfoPrtcptPsblRgn", "R26BK20000001"),
        ("getBidPblancListInfoPrtcptPsblRgn", "UNIFIED-2001"),
    ]
    assert [item.region_name for item in regions] == ["서울특별시"]
