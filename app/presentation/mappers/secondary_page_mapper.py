from datetime import datetime, timedelta

from app.presentation.viewmodels.bids import BidListItemVM
from app.presentation.viewmodels.dashboard import DashboardStatVM, DashboardSummaryVM
from app.presentation.viewmodels.favorites import FavoritesPageVM
from app.presentation.viewmodels.operations import OperationItemVM, OperationsPageVM
from app.presentation.viewmodels.prespecs import PrespecItemVM, PrespecsPageVM
from app.presentation.viewmodels.results import ResultItemVM, ResultsPageVM


def build_prespecs_page_vm(
    items: list[dict[str, str]], last_synced_at: str
) -> PrespecsPageVM:
    order_plan_count = sum(1 for item in items if item.get("stage") == "발주계획")
    prespec_count = sum(1 for item in items if item.get("stage") == "사전규격")
    procurement_request_count = sum(
        1 for item in items if item.get("stage") == "조달요청"
    )
    linked_bid_count = sum(1 for item in items if item.get("linked_bid") == "연결됨")

    return PrespecsPageVM(
        title="사전 탐색",
        description="발주계획, 사전규격, 조달요청 화면이 여기에 배치됩니다.",
        active_nav="prespecs",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="발주계획", value=str(order_plan_count)),
                DashboardStatVM(label="사전규격", value=str(prespec_count)),
                DashboardStatVM(label="조달요청", value=str(procurement_request_count)),
                DashboardStatVM(label="본공고 연결", value=str(linked_bid_count)),
            ],
        ),
        items=[PrespecItemVM(**item) for item in items],
    )


def build_results_page_vm(
    items: list[dict[str, str]], last_synced_at: str
) -> ResultsPageVM:
    return ResultsPageVM(
        title="사후 분석",
        description="낙찰 및 계약 결과 분석 화면이 여기에 배치됩니다.",
        active_nav="results",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="낙찰 건수", value="7"),
                DashboardStatVM(label="계약 건수", value="6"),
                DashboardStatVM(label="평균 낙찰률", value="88.55%"),
                DashboardStatVM(label="분석 기관 수", value="4"),
            ],
        ),
        items=[ResultItemVM(**item) for item in items],
    )


def build_favorites_page_vm(
    items: list[BidListItemVM], last_synced_at: str
) -> FavoritesPageVM:
    now = datetime.now()
    closing_soon_count = sum(
        1
        for item in items
        if now <= _parse_datetime(item.closed_at) <= now + timedelta(days=3)
    )
    review_count = sum(
        1 for item in items if item.status in {"검토중", "관심", "수집완료"}
    )
    changed_count = sum(
        1
        for item in items
        if item.version_label and item.version_label not in {"", "최초공고"}
    )

    return FavoritesPageVM(
        title="관심 공고",
        description="즐겨찾기한 공고를 모아 마감 임박, 변경 감지, 재확인 필요 항목부터 집중 관리합니다.",
        active_nav="favorites",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="관심 공고", value=str(len(items))),
                DashboardStatVM(label="마감 임박", value=str(closing_soon_count)),
                DashboardStatVM(label="재확인 필요", value=str(review_count)),
                DashboardStatVM(label="변경 감지", value=str(changed_count)),
            ],
        ),
        items=items,
    )


def build_operations_page_vm(
    items: list[dict[str, str]], last_synced_at: str
) -> OperationsPageVM:
    success_count = sum(1 for item in items if item.get("status") == "completed")
    failed_count = sum(1 for item in items if item.get("status") == "failed")
    running_count = sum(1 for item in items if item.get("status") == "running")
    last_execution = (
        items[0]["finished_at"]
        if items and items[0].get("finished_at") not in {None, "-"}
        else "-"
    )

    return OperationsPageVM(
        title="운영 현황",
        description="동기화 상태와 실패 로그 화면이 여기에 배치됩니다.",
        active_nav="operations",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="최근 배치 성공", value=str(success_count)),
                DashboardStatVM(label="실패 건수", value=str(failed_count)),
                DashboardStatVM(label="재수집 실행중", value=str(running_count)),
                DashboardStatVM(label="마지막 실행", value=last_execution),
            ],
        ),
        items=[OperationItemVM(**item) for item in items],
    )


def _build_summary(
    last_synced_at: str, items: list[DashboardStatVM]
) -> DashboardSummaryVM:
    return DashboardSummaryVM(items=items, last_synced_at=last_synced_at)


def _parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.min
