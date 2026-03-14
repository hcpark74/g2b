import json
from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, BidDetail, ContractProcessIntegration, TimelineStageSnapshot
from app.services.g2b_contract_process_service import G2BContractProcessService


class FakeContractProcessClient:
    def __init__(
        self, responses: dict[tuple[str, int, str], list[dict[str, str]]]
    ) -> None:
        self.responses = responses

    def fetch_contract_process(
        self,
        *,
        operation_name: str,
        inqry_div: int,
        value: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, str]]:
        _ = (page_no, num_of_rows)
        return self.responses.get((operation_name, inqry_div, value), [])


def test_contract_process_service_uses_bid_notice_number_first() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000111-000",
                bid_no="R26BK00000111",
                bid_seq="000",
                title="타임라인 대상",
                category="용역",
                posted_at=datetime(2026, 3, 13, 9, 0),
                closed_at=datetime(2026, 3, 20, 18, 0),
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000111-000",
                raw_api_data=json.dumps(
                    {"bfSpecRgstNo": "BF-1", "orderPlanNo": "PLAN-1"}
                ),
            )
        )
        session.commit()

    client = FakeContractProcessClient(
        {
            ("getCntrctProcssIntgOpenServc", 1, "R26BK00000111"): [
                {
                    "bidwinrCmpnyNm": "우수기업",
                    "sucsfbidAmt": "100000000",
                    "cntrctNo": "CN-123",
                    "cntrctNm": "유지보수 계약",
                    "cntrctDate": "2026-03-25",
                }
            ]
        }
    )

    with Session(engine) as session:
        result = G2BContractProcessService(
            session=session, client=client
        ).enrich_timelines(bid_ids=["R26BK00000111-000"])

    with Session(engine) as session:
        integrations = session.exec(select(ContractProcessIntegration)).all()
        snapshots = session.exec(select(TimelineStageSnapshot)).all()

    assert result.processed_bid_ids == ["R26BK00000111-000"]
    assert result.fetched_item_count == 1
    assert integrations[0].inqry_div == 1
    assert integrations[0].award_company == "우수기업"
    assert len(snapshots) == 3
    assert snapshots[1].stage == "개찰/낙찰"
    assert snapshots[1].status == "완료"
    assert snapshots[2].number == "CN-123"


def test_contract_process_service_falls_back_to_auxiliary_keys() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00000222-000",
                bid_no="R26BK00000222",
                bid_seq="000",
                title="보조 키 대상",
                category="물품",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000222-000",
                raw_api_data=json.dumps(
                    {"bfSpecRgstNo": "BF-222", "prcrmntReqNo": "REQ-222"}
                ),
            )
        )
        session.commit()

    client = FakeContractProcessClient(
        {
            ("getCntrctProcssIntgOpenThng", 2, "BF-222"): [
                {"bidwinrCmpnyNm": "대체조회 업체"}
            ]
        }
    )

    with Session(engine) as session:
        result = G2BContractProcessService(
            session=session, client=client
        ).enrich_timelines(bid_ids=["R26BK00000222-000"])

    with Session(engine) as session:
        integration = session.exec(select(ContractProcessIntegration)).first()

    assert result.fetched_item_count == 1
    assert integration is not None
    assert integration.inqry_div == 2
    assert integration.source_key == "BF-222"
