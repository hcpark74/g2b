from app.presentation.viewmodels.bids import BidListItemVM
from app.presentation.viewmodels.dashboard import DashboardStatVM, DashboardSummaryVM
from app.presentation.viewmodels.favorites import FavoritesPageVM
from app.presentation.viewmodels.operations import OperationItemVM, OperationsPageVM
from app.presentation.viewmodels.prespecs import PrespecItemVM, PrespecsPageVM
from app.presentation.viewmodels.results import ResultItemVM, ResultsPageVM


def build_prespecs_page_vm(items: list[dict[str, str]], last_synced_at: str) -> PrespecsPageVM:
    return PrespecsPageVM(
        title="사전 탐색",
        description="발주계획, 사전규격, 조달요청 화면이 여기에 배치됩니다.",
        active_nav="prespecs",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="발주계획", value="14"),
                DashboardStatVM(label="사전규격", value="9"),
                DashboardStatVM(label="조달요청", value="6"),
                DashboardStatVM(label="본공고 연결", value="5"),
            ],
        ),
        items=[PrespecItemVM(**item) for item in items],
    )


def build_results_page_vm(items: list[dict[str, str]], last_synced_at: str) -> ResultsPageVM:
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


def build_favorites_page_vm(items: list[BidListItemVM], last_synced_at: str) -> FavoritesPageVM:
    return FavoritesPageVM(
        title="관심 공고",
        description="즐겨찾기한 공고 목록 화면이 여기에 배치됩니다.",
        active_nav="favorites",
        last_synced_at=last_synced_at,
        summary=_build_summary(
            last_synced_at,
            [
                DashboardStatVM(label="관심 공고", value=str(len(items))),
                DashboardStatVM(label="오늘 마감", value="1"),
                DashboardStatVM(label="검토중", value="1"),
                DashboardStatVM(label="변경 감지", value="1"),
            ],
        ),
        items=items,
    )


def build_operations_page_vm(items: list[dict[str, str]], last_synced_at: str) -> OperationsPageVM:
    success_count = sum(1 for item in items if item.get("status") == "completed")
    failed_count = sum(1 for item in items if item.get("status") == "failed")
    running_count = sum(1 for item in items if item.get("status") == "running")
    last_execution = items[0]["finished_at"] if items and items[0].get("finished_at") not in {None, "-"} else "-"

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


def _build_summary(last_synced_at: str, items: list[DashboardStatVM]) -> DashboardSummaryVM:
    return DashboardSummaryVM(items=items, last_synced_at=last_synced_at)
