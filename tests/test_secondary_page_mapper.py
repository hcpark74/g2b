from datetime import datetime, timedelta

from app.presentation.mappers.secondary_page_mapper import (
    build_favorites_page_vm,
    build_operations_page_vm,
)
from app.presentation.viewmodels.bids import BidListItemVM


def _favorite_item(
    *,
    status: str = "검토중",
    version_label: str = "최초공고",
    closed_at: str | None = None,
) -> BidListItemVM:
    return BidListItemVM(
        bid_id="R26BK00000001-000",
        display_bid_no="R26BK00000001-000",
        row_number=1,
        favorite=True,
        status=status,
        status_variant="primary",
        version_label=version_label,
        version_variant="secondary",
        version_summary="",
        business_type="용역",
        domain_type="내자",
        notice_type="등록공고",
        bid_no="R26BK00000001",
        title="테스트 공고",
        notice_org="조달청",
        demand_org="한국지능정보원",
        budget_amount="120,000,000",
        posted_at="2026-03-13 09:00",
        closed_at=closed_at
        or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        opened_at="2026-03-20 19:00",
        stage_label="입찰공고",
        step_label="공고등록",
        progress_label="진행중",
        summary_badge="검토중",
    )


def test_build_favorites_page_vm_uses_item_count_in_summary() -> None:
    page_vm = build_favorites_page_vm(
        [
            _favorite_item(status="검토중", version_label="정정공고"),
            _favorite_item(
                status="투찰완료",
                version_label="최초공고",
                closed_at=(datetime.now() + timedelta(days=10)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            ),
        ],
        last_synced_at="2026-03-13 10:00",
    )

    assert page_vm.title == "관심 공고"
    assert page_vm.summary.items[0].value == "2"
    assert page_vm.summary.items[1].value == "1"
    assert page_vm.summary.items[2].value == "1"
    assert page_vm.summary.items[3].value == "1"
    assert page_vm.items[0].display_bid_no == "R26BK00000001-000"


def test_build_operations_page_vm_calculates_summary_counts() -> None:
    page_vm = build_operations_page_vm(
        [
            {
                "job_type": "bid_public_info_sync",
                "target": "service",
                "status": "completed",
                "started_at": "2026-03-13 06:00",
                "finished_at": "2026-03-13 06:04",
                "message": "ok",
            },
            {
                "job_type": "bid_public_info_sync",
                "target": "goods",
                "status": "failed",
                "started_at": "2026-03-13 05:00",
                "finished_at": "2026-03-13 05:01",
                "message": "fail",
            },
            {
                "job_type": "bid_public_info_sync",
                "target": "works",
                "status": "running",
                "started_at": "2026-03-13 04:00",
                "finished_at": "-",
                "message": "running",
            },
        ],
        last_synced_at="2026-03-13 06:04",
    )

    assert page_vm.summary.items[0].value == "1"
    assert page_vm.summary.items[1].value == "1"
    assert page_vm.summary.items[2].value == "1"
    assert page_vm.summary.items[3].value == "2026-03-13 06:04"
