from typing import Any

from app.presentation.viewmodels.bids import (
    BidAttachmentVM,
    BidDetailRowVM,
    BidDrawerVM,
    BidHistoryItemVM,
    BidReferenceInfoVM,
    BidVersionItemVM,
    BidListItemVM,
    BidQualificationItemVM,
    BidQualificationVM,
    BidsPageVM,
)
from app.presentation.viewmodels.dashboard import DashboardStatVM, DashboardSummaryVM
from app.presentation.viewmodels.timeline import TimelineStageVM


def build_bid_list_item_vm(raw_bid: dict[str, Any], row_number: int) -> BidListItemVM:
    display_bid_no = str(
        raw_bid.get("display_bid_no")
        or raw_bid.get("bid_id")
        or raw_bid.get("bid_no", "")
    )
    return BidListItemVM(
        bid_id=str(raw_bid.get("bid_id", "")),
        display_bid_no=display_bid_no,
        row_number=row_number,
        favorite=bool(raw_bid.get("favorite", False)),
        status=str(raw_bid.get("status", "")),
        status_variant=str(raw_bid.get("status_variant", "secondary")),
        version_label=str(raw_bid.get("version_label", "")),
        version_variant=str(raw_bid.get("version_variant", "secondary")),
        version_summary=str(raw_bid.get("version_summary", "")),
        business_type=str(raw_bid.get("business_type", "")),
        domain_type=str(raw_bid.get("domain_type", "")),
        notice_type=str(raw_bid.get("notice_type", "")),
        bid_no=str(raw_bid.get("bid_no", "")),
        title=str(raw_bid.get("title", "")),
        notice_org=str(raw_bid.get("notice_org", "")),
        demand_org=str(raw_bid.get("demand_org", "")),
        budget_amount=str(raw_bid.get("budget_amount", "")),
        posted_at=str(raw_bid.get("posted_at", "")),
        closed_at=str(raw_bid.get("closed_at", "")),
        opened_at=str(raw_bid.get("opened_at", "")),
        stage_label=str(raw_bid.get("stage_label", "")),
        step_label=str(raw_bid.get("step_label", "")),
        progress_label=str(raw_bid.get("progress_label", "")),
        summary_badge=str(raw_bid.get("status", "")),
    )


def build_bid_drawer_vm(raw_bid: dict[str, Any]) -> BidDrawerVM:
    qualification = raw_bid.get("qualification", {})
    business_info = raw_bid.get("business_info", {})
    detail_rows = raw_bid.get("detail_rows", [])
    attachments = raw_bid.get("attachments", [])
    timeline_items = raw_bid.get("timeline", [])
    history_items = raw_bid.get("history", [])

    business_specific = [
        BidQualificationItemVM(label=_business_info_label(str(label)), value=str(value))
        for label, value in business_info.items()
    ]

    return BidDrawerVM(
        bid_id=str(raw_bid.get("bid_id", "")),
        display_bid_no=str(
            raw_bid.get("display_bid_no")
            or raw_bid.get("bid_id")
            or raw_bid.get("bid_no", "")
        ),
        title=str(raw_bid.get("title", "")),
        business_type=str(raw_bid.get("business_type", "")),
        status=str(raw_bid.get("status", "")),
        status_variant=str(raw_bid.get("status_variant", "secondary")),
        version_label=str(raw_bid.get("version_label", "")),
        version_variant=str(raw_bid.get("version_variant", "secondary")),
        version_summary=str(raw_bid.get("version_summary", "")),
        is_latest_effective=bool(raw_bid.get("is_latest_effective", False)),
        latest_effective_bid_id=str(raw_bid.get("latest_effective_bid_id", "")),
        latest_effective_title=str(raw_bid.get("latest_effective_title", "")),
        description_text=str(raw_bid.get("description_text", "")),
        detail_url=str(raw_bid.get("detail_url", "")),
        crawl_excerpt=str(raw_bid.get("crawl_excerpt", "")),
        overview_rows=[BidDetailRowVM(**row) for row in detail_rows],
        qualification=BidQualificationVM(
            industry_limited=bool(qualification.get("industry_limited", False)),
            international_bid=str(qualification.get("international_bid", "")),
            rebid_allowed=str(qualification.get("rebid_allowed", "")),
            bid_participation_limit=str(
                qualification.get("bid_participation_limit", "")
            ),
            consortium_method=str(qualification.get("consortium_method", "")),
            license_limits=[
                str(item) for item in qualification.get("license_limits", [])
            ],
            permitted_industries=[
                str(item) for item in qualification.get("permitted_industries", [])
            ],
            regions=[str(item) for item in qualification.get("regions", [])],
            reference_infos=[
                BidReferenceInfoVM(
                    name=str(item.get("name", "")),
                    code=str(item.get("code", "")),
                    law_name=str(item.get("law_name", "")),
                    source_api_name=str(item.get("source_api_name", "")),
                )
                for item in qualification.get("reference_infos", [])
                if isinstance(item, dict)
            ],
            qualification_summary=str(qualification.get("qualification_summary", "")),
            business_specific=business_specific,
        ),
        attachments=[BidAttachmentVM(**item) for item in attachments],
        timeline=[
            TimelineStageVM(
                stage=str(item.get("stage", "")),
                status=str(item.get("status", "")),
                status_variant=_timeline_variant(str(item.get("status", ""))),
                number=str(item.get("number", "")),
                date=str(item.get("date", "")),
                meta=str(item.get("meta", "")),
            )
            for item in timeline_items
        ],
        history=[BidHistoryItemVM(**item) for item in history_items],
        version_history=[
            BidVersionItemVM(**item) for item in raw_bid.get("version_history", [])
        ],
    )


def build_bids_page_vm(
    raw_bids: list[dict[str, Any]], last_synced_at: str, active_nav: str = "bids"
) -> BidsPageVM:
    list_items = [
        build_bid_list_item_vm(raw_bid, index + 1)
        for index, raw_bid in enumerate(raw_bids)
    ]
    selected_bid = build_bid_drawer_vm(raw_bids[0]) if raw_bids else None

    return BidsPageVM(
        summary=DashboardSummaryVM(
            items=[
                DashboardStatVM(label="신규 공고", value="12"),
                DashboardStatVM(label="오늘 마감", value="3"),
                DashboardStatVM(label="관심 공고", value="8"),
                DashboardStatVM(label="상태 변경 감지", value="5"),
            ],
            last_synced_at=last_synced_at,
        ),
        bids=list_items,
        selected_bid=selected_bid,
        total_count=len(list_items),
        active_nav=active_nav,
    )


def _timeline_variant(status: str) -> str:
    if status == "완료":
        return "success"
    if status == "진행중":
        return "primary"
    if status == "미체결":
        return "warning"
    if status == "확인 필요":
        return "danger"
    return "secondary"


def _business_info_label(key: str) -> str:
    labels = {
        "service_division": "용역구분",
        "public_procurement_cls": "공공조달분류",
        "tech_eval_rate": "기술평가비율",
        "price_eval_rate": "가격평가비율",
        "info_biz": "정보화사업 여부",
        "product_class_limited": "물품분류 제한",
        "manufacturing_required": "제조 여부",
        "detail_product_no": "세부품명번호",
        "detail_product_name": "세부품명",
        "product_qty": "수량",
        "delivery_condition": "인도조건",
        "main_construction_type": "주공종",
        "construction_site_region": "공사현장지역",
        "industry_eval_rate": "업종평가비율",
        "joint_contract_required": "지역의무공동도급",
        "construction_law_applied": "건산법 적용 여부",
        "market_entry_allowed": "상호시장진출 허용",
    }
    return labels.get(key, key)
