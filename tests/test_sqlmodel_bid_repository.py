from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    Attachment,
    Bid,
    BidDetail,
    BidLicenseLimit,
    BidParticipationRegion,
    BidPurchaseItem,
    BidReferenceInfo,
    ContractProcessIntegration,
    TimelineStageSnapshot,
)
from app.repositories.sqlmodel_bid_repository import SqlModelBidRepository
from tests.bid_version_fixtures import seed_bid_version_chain


def _make_repository() -> tuple[Session, SqlModelBidRepository]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    return session, SqlModelBidRepository(session)


def test_list_bids_orders_latest_posted_at_first() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000001-000",
                bid_no="R26BK00000001",
                bid_seq="000",
                title="older",
                posted_at=datetime(2026, 3, 10, 9, 0),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK00000002-000",
                bid_no="R26BK00000002",
                bid_seq="000",
                title="newer",
                posted_at=datetime(2026, 3, 11, 9, 0),
            )
        )
        session.commit()

        bids = repository.list_bids()

        assert [bid["bid_id"] for bid in bids] == [
            "R26BK00000002-000",
            "R26BK00000001-000",
        ]
    finally:
        session.close()


def test_get_bid_includes_detail_and_sorted_attachments() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000003-000",
                bid_no="R26BK00000003",
                bid_seq="000",
                title="attachment bid",
                category="용역",
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000003-000",
                description_text="상세 설명",
                detail_url="https://example.com/bids/R26BK00000003-000",
            )
        )
        session.add(
            Attachment(
                attachment_id="b-file",
                bid_id="R26BK00000003-000",
                name="B file",
                source="getBidPblancListInfoEorderAtchFileInfo",
            )
        )
        session.add(
            Attachment(
                attachment_id="a-file",
                bid_id="R26BK00000003-000",
                name="A file",
                source="getBidPblancListInfoEorderAtchFileInfo",
            )
        )
        session.add(
            BidLicenseLimit(
                bid_id="R26BK00000003-000",
                license_name="정보통신공사업",
            )
        )
        session.add(
            BidParticipationRegion(
                bid_id="R26BK00000003-000",
                region_name="서울특별시",
            )
        )
        session.add(
            BidReferenceInfo(
                bid_id="R26BK00000003-000",
                reference_key="INFO-001",
                reference_name="정보통신공사업",
                source_api_name="industryBaseLaw",
                raw_data='{"indstrytyCd":"INFO-001","lawNm":"정보통신공사업법"}',
            )
        )
        session.add(
            BidPurchaseItem(
                bid_id="R26BK00000003-000",
                item_name="데이터서비스",
                item_code="8111229901",
                quantity="1식",
                delivery_condition="현장 협의",
            )
        )
        session.add(
            TimelineStageSnapshot(
                bid_id="R26BK00000003-000",
                stage="개찰/낙찰",
                status="완료",
                number="우수기업",
                occurred_at="2026-03-21 10:00",
                meta="100000000",
            )
        )
        session.add(
            ContractProcessIntegration(
                bid_id="R26BK00000003-000",
                inqry_div=1,
                source_key="R26BK00000003",
                award_company="우수기업",
                award_amount="100000000",
                contract_no="CN-123",
                contract_name="유지보수 계약",
                contract_date="2026-03-25",
                collected_at="2026-03-21T10:00:00+00:00",
            )
        )
        session.commit()

        bid = repository.get_bid("R26BK00000003-000")

        assert bid["description_text"] == "상세 설명"
        assert bid["detail_url"] == "https://example.com/bids/R26BK00000003-000"
        assert bid["display_bid_no"] == "R26BK00000003-000"
        assert bid["qualification"]["license_limits"] == ["정보통신공사업"]
        assert bid["qualification"]["regions"] == ["서울특별시"]
        assert bid["qualification"]["reference_infos"] == [
            {
                "name": "정보통신공사업",
                "code": "INFO-001",
                "law_name": "정보통신공사업법",
                "source_api_name": "industryBaseLaw",
            }
        ]
        assert bid["business_info"]["public_procurement_cls"] == "데이터서비스"
        assert bid["timeline"][0]["stage"] == "개찰/낙찰"
        assert bid["timeline"][0]["number"] == "우수기업"
        assert bid["history"][0]["item"] == "낙찰업체"
        assert bid["history"][0]["after"] == "우수기업"
        assert bid["history"][1]["item"] == "낙찰금액"
        assert bid["history"][1]["after"] == "100000000"
        assert bid["history"][2]["item"] == "계약번호"
        assert bid["history"][3]["item"] == "계약명"
        assert bid["history"][4]["item"] == "계약일자"
        assert bid["history"][4]["after"] == "2026-03-25"
        assert (
            bid["attachments"][0]["source"] == "getBidPblancListInfoEorderAtchFileInfo"
        )
        assert [item["name"] for item in bid["attachments"]] == ["A file", "B file"]
    finally:
        session.close()


def test_get_bid_uses_default_description_when_detail_missing() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000004-000",
                bid_no="R26BK00000004",
                bid_seq="000",
                title="no detail bid",
            )
        )
        session.commit()

        bid = repository.get_bid("R26BK00000004-000")

        assert bid["description_text"] == "상세 본문은 추가 연동 예정"
        assert bid["detail_url"] == ""
    finally:
        session.close()


def test_list_bids_filters_by_status_search_and_favorites() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000005-000",
                bid_no="R26BK00000005",
                bid_seq="000",
                title="AI 유지보수 용역",
                status="reviewing",
                is_favorite=True,
            )
        )
        session.add(
            Bid(
                bid_id="R26BK00000006-000",
                bid_no="R26BK00000006",
                bid_seq="000",
                title="일반 물품 구매",
                status="collected",
                is_favorite=False,
            )
        )
        session.commit()

        bids = repository.list_bids(
            search_query="유지보수", status="reviewing", favorites_only=True
        )

        assert [bid["bid_id"] for bid in bids] == ["R26BK00000005-000"]
    finally:
        session.close()


def test_list_bids_filters_and_sorts_in_repository() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000007-000",
                bid_no="R26BK00000007",
                bid_seq="000",
                title="데이터서비스 구축",
                notice_org="전라남도",
                demand_org="전라남도청",
                budget_amount=200000000,
                closed_at=datetime(2026, 3, 20, 10, 0),
                posted_at=datetime(2026, 3, 12, 10, 0),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK00000008-000",
                bid_no="R26BK00000008",
                bid_seq="000",
                title="도로 보수 공사",
                notice_org="전라남도",
                demand_org="전라남도청",
                budget_amount=900000000,
                closed_at=datetime(2026, 3, 18, 10, 0),
                posted_at=datetime(2026, 3, 11, 10, 0),
            )
        )
        session.add(
            BidDetail(
                bid_id="R26BK00000007-000",
                description_text="데이터서비스 고도화 사업",
            )
        )
        session.commit()

        bids = repository.list_bids(
            keyword="데이터서비스",
            org="전라남도",
            budget_min=100000000,
            budget_max=300000000,
            closed_from="2026-03-19 00:00",
            closed_to="2026-03-21 00:00",
            sort="budget_amount",
            order="asc",
        )

        assert [bid["bid_id"] for bid in bids] == ["R26BK00000007-000"]
    finally:
        session.close()


def test_list_bids_keyword_matches_attachment_name() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000009-000",
                bid_no="R26BK00000009",
                bid_seq="000",
                title="첨부 키워드 테스트",
            )
        )
        session.add(
            Attachment(
                attachment_id="attach-1",
                bid_id="R26BK00000009-000",
                name="특수시방서.zip",
                source="getBidPblancListInfoEorderAtchFileInfo",
                download_url="https://example.com/spec.zip",
            )
        )
        session.commit()

        bids = repository.list_bids(keyword="특수시방서")

        assert [bid["bid_id"] for bid in bids] == ["R26BK00000009-000"]
    finally:
        session.close()


def test_bid_version_fixture_preserves_each_version_as_separate_row() -> None:
    session, repository = _make_repository()
    try:
        ids = seed_bid_version_chain(session)

        original = repository.get_bid(ids["original_bid_id"])
        revision = repository.get_bid(ids["revision_bid_id"])
        cancellation = repository.get_bid(ids["cancellation_bid_id"])

        assert original["bid_seq"] == "000"
        assert revision["bid_seq"] == "001"
        assert cancellation["bid_seq"] == "002"
        assert original["title"] == "통합 유지보수 용역"
        assert revision["title"] == "통합 유지보수 용역 정정공고"
        assert cancellation["title"] == "통합 유지보수 용역 취소공고"
        assert cancellation["status"] == "보관"
    finally:
        session.close()


def test_list_bids_can_return_all_versions_for_same_bid_number() -> None:
    session, repository = _make_repository()
    try:
        ids = seed_bid_version_chain(session)

        bids = repository.list_bids(search_query=ids["bid_no"])

        assert [bid["bid_id"] for bid in bids] == [
            ids["cancellation_bid_id"],
            ids["revision_bid_id"],
            ids["original_bid_id"],
        ]
    finally:
        session.close()


def test_list_bids_can_include_historical_versions_with_filter() -> None:
    session, repository = _make_repository()
    try:
        ids = seed_bid_version_chain(session)

        bids = repository.list_bids(include_versions=True)

        assert [bid["bid_id"] for bid in bids] == [
            ids["cancellation_bid_id"],
            ids["revision_bid_id"],
            ids["original_bid_id"],
        ]
    finally:
        session.close()


def test_list_bids_defaults_to_latest_effective_version_per_bid_number() -> None:
    session, repository = _make_repository()
    try:
        ids = seed_bid_version_chain(session)

        bids = repository.list_bids()

        assert [bid["bid_id"] for bid in bids] == [ids["revision_bid_id"]]
        assert bids[0]["title"] == "통합 유지보수 용역 정정공고"
        assert bids[0]["version_label"] == "정정공고"
        assert (
            bids[0]["version_summary"]
            == "현재 보고 있는 공고는 검토 기준이 되는 최신 유효 차수입니다."
        )
    finally:
        session.close()


def test_get_bid_includes_version_history_metadata() -> None:
    session, repository = _make_repository()
    try:
        ids = seed_bid_version_chain(session)

        bid = repository.get_bid(ids["cancellation_bid_id"])

        assert bid["version_label"] == "취소공고"
        assert bid["is_latest_effective"] is False
        assert bid["latest_effective_bid_id"] == ids["revision_bid_id"]
        assert bid["version_history"][0]["bid_id"] == ids["cancellation_bid_id"]
        assert bid["version_history"][1]["is_latest_effective"] is True
        assert bid["version_history"][1]["bid_id"] == ids["revision_bid_id"]
        assert bid["timeline"][0]["stage"] == "공고 버전"
        assert bid["timeline"][0]["meta"] == "취소 공고 게시 · 공고상태"
        assert bid["history"][0]["item"] == "공고 차수 상태"
        assert bid["history"][0]["after"] == "취소공고"
        assert bid["history"][1]["item"] == "공고상태"
        assert bid["history"][1]["before"] == "정정공고"
    finally:
        session.close()


def test_list_bids_keyword_matches_timeline_and_history_sources() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000010-000",
                bid_no="R26BK00000010",
                bid_seq="000",
                title="타임라인 테스트 공고",
            )
        )
        session.add(
            TimelineStageSnapshot(
                bid_id="R26BK00000010-000",
                stage="개찰/낙찰",
                status="완료",
                number="우수기업",
                occurred_at="2026-03-21 10:00",
                meta="개찰완료",
            )
        )
        session.add(
            ContractProcessIntegration(
                bid_id="R26BK00000010-000",
                inqry_div=1,
                source_key="R26BK00000010",
                award_company="우수기업",
                award_amount="100000000",
                contract_no="CN-555",
                contract_name="유지보수 계약",
                contract_date="2026-03-25",
                raw_data='{"contract_name":"유지보수 계약"}',
            )
        )
        session.commit()

        timeline_bids = repository.list_bids(keyword="개찰완료")
        history_bids = repository.list_bids(keyword="CN-555")

        assert [bid["bid_id"] for bid in timeline_bids] == ["R26BK00000010-000"]
        assert [bid["bid_id"] for bid in history_bids] == ["R26BK00000010-000"]
    finally:
        session.close()


def test_list_bids_page_returns_total_and_paginated_items() -> None:
    session, repository = _make_repository()
    try:
        session.add(
            Bid(
                bid_id="R26BK00000011-000",
                bid_no="R26BK00000011",
                bid_seq="000",
                title="older",
                posted_at=datetime(2026, 3, 10, 9, 0),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK00000012-000",
                bid_no="R26BK00000012",
                bid_seq="000",
                title="middle",
                posted_at=datetime(2026, 3, 11, 9, 0),
            )
        )
        session.add(
            Bid(
                bid_id="R26BK00000013-000",
                bid_no="R26BK00000013",
                bid_seq="000",
                title="newer",
                posted_at=datetime(2026, 3, 12, 9, 0),
            )
        )
        session.commit()

        page = repository.list_bids_page(page=2, page_size=1)

        assert page.total == 3
        assert [bid["bid_id"] for bid in page.items] == ["R26BK00000012-000"]
    finally:
        session.close()


def test_get_bid_raises_key_error_for_unknown_bid() -> None:
    session, repository = _make_repository()
    try:
        try:
            repository.get_bid("missing")
        except KeyError as exc:
            assert "Bid not found: missing" in str(exc)
        else:
            raise AssertionError("KeyError was not raised")
    finally:
        session.close()
