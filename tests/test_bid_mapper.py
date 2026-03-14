from app.presentation.mappers import (
    build_bid_drawer_vm,
    build_bid_list_item_vm,
    build_bids_page_vm,
)
from app.sample_data import get_sample_bids


def test_build_bids_page_vm_creates_summary_and_list_items() -> None:
    raw_bids = get_sample_bids()

    page_vm = build_bids_page_vm(
        raw_bids, last_synced_at="2026-03-12 19:45", active_nav="bids"
    )

    assert page_vm.total_count == 3
    assert page_vm.active_nav == "bids"
    assert page_vm.summary.items[0].label == "신규 공고"
    assert (
        page_vm.bids[0].title
        == "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역"
    )
    assert page_vm.bids[0].display_bid_no == "R26BK00000001-000"
    assert page_vm.selected_bid is not None


def test_build_bid_drawer_vm_maps_business_specific_fields() -> None:
    raw_bid = get_sample_bids()[0]

    drawer_vm = build_bid_drawer_vm(raw_bid)

    assert drawer_vm.bid_id == "R26BK00000001-000"
    assert drawer_vm.display_bid_no == "R26BK00000001-000"
    assert drawer_vm.business_type == "용역"
    assert drawer_vm.overview_rows[0].left_label == "공고종류"
    assert (
        drawer_vm.qualification.license_limits[0]
        == "소프트웨어사업자(컴퓨터관련서비스사업)"
    )
    assert drawer_vm.qualification.reference_infos[0].name == "정보통신공사업"
    assert drawer_vm.qualification.reference_infos[0].code == "INFO-001"
    assert drawer_vm.qualification.reference_infos[0].law_name == "정보통신공사업법"
    assert drawer_vm.qualification.business_specific[0].label == "용역구분"
    assert drawer_vm.timeline[0].status_variant == "success"


def test_build_bid_drawer_vm_maps_goods_specific_fields() -> None:
    raw_bid = get_sample_bids()[1]

    drawer_vm = build_bid_drawer_vm(raw_bid)

    assert drawer_vm.business_type == "물품"
    labels = [item.label for item in drawer_vm.qualification.business_specific]
    assert "세부품명번호" in labels
    assert "인도조건" in labels


def test_build_bid_list_item_vm_prefers_display_bid_no() -> None:
    item_vm = build_bid_list_item_vm(
        {
            "bid_id": "R26BK99999999-000",
            "bid_no": "R26BK99999999",
            "display_bid_no": "R26BK99999999-000",
            "title": "테스트 공고",
        },
        row_number=7,
    )

    assert item_vm.bid_id == "R26BK99999999-000"
    assert item_vm.display_bid_no == "R26BK99999999-000"
    assert item_vm.row_number == 7


def test_build_bid_drawer_vm_maps_detail_url() -> None:
    raw_bid = dict(get_sample_bids()[0])
    raw_bid["detail_url"] = "https://example.com/bids/R26BK00000001-000"

    drawer_vm = build_bid_drawer_vm(raw_bid)

    assert drawer_vm.description_text.startswith("사회적 고립청년")
    assert drawer_vm.detail_url == "https://example.com/bids/R26BK00000001-000"
