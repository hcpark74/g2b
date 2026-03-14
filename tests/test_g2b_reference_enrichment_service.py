from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidLicenseLimit, BidReferenceInfo
from app.services.g2b_reference_enrichment_service import G2BReferenceEnrichmentService


class FakeReferenceClient:
    def __init__(self, responses: dict[str, list[dict[str, Any]]]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch_industry_base_law(
        self,
        *,
        industry_name: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]:
        _ = (page_no, num_of_rows)
        self.calls.append(industry_name)
        return self.responses.get(industry_name, [])


def test_reference_enrichment_persists_reference_rows() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(bid_id="R26BK30000001-000", bid_no="R26BK30000001", title="참조 대상")
        )
        session.add(
            BidLicenseLimit(
                bid_id="R26BK30000001-000",
                license_name="정보통신공사업",
                source_api_name="getBidPblancListInfoLicenseLimit",
            )
        )
        session.commit()

    client = FakeReferenceClient(
        {
            "정보통신공사업": [
                {"indstrytyCd": "INFO-1", "lawNm": "정보통신공사업법"},
                {"indstrytyCd": "INFO-2", "lawNm": "정보통신공사업 시행령"},
            ]
        }
    )

    with Session(engine) as session:
        result = G2BReferenceEnrichmentService(
            session=session, client=client
        ).enrich_bids(
            bid_ids=["R26BK30000001-000"],
            num_of_rows=50,
        )

    with Session(engine) as session:
        rows = session.exec(select(BidReferenceInfo)).all()

    assert result.processed_bid_ids == ["R26BK30000001-000"]
    assert result.fetched_item_count == 2
    assert client.calls == ["정보통신공사업"]
    assert [row.reference_key for row in rows] == ["INFO-1", "INFO-2"]
    assert rows[0].reference_name == "정보통신공사업"
    assert all(row.source_api_name == "industryBaseLaw" for row in rows)


def test_reference_enrichment_replaces_existing_rows() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(bid_id="R26BK30000002-000", bid_no="R26BK30000002", title="참조 대상")
        )
        session.add(
            BidLicenseLimit(bid_id="R26BK30000002-000", license_name="소프트웨어사업자")
        )
        session.add(
            BidReferenceInfo(
                bid_id="R26BK30000002-000",
                reference_key="OLD",
                reference_name="소프트웨어사업자",
                source_api_name="industryBaseLaw",
            )
        )
        session.commit()

    client = FakeReferenceClient(
        {"소프트웨어사업자": [{"indstrytyCd": "NEW", "lawNm": "소프트웨어진흥법"}]}
    )

    with Session(engine) as session:
        G2BReferenceEnrichmentService(session=session, client=client).enrich_bids(
            bid_ids=["R26BK30000002-000"]
        )

    with Session(engine) as session:
        rows = session.exec(select(BidReferenceInfo)).all()

    assert len(rows) == 1
    assert rows[0].reference_key == "NEW"
