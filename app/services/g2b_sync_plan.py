from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class G2BSyncOperationSpec:
    name: str
    stage: str
    priority: int
    purpose: str


@dataclass(frozen=True, slots=True)
class G2BConnectionKeys:
    bid_ntce_no: str | None = None
    bf_spec_rgst_no: str | None = None
    order_plan_no: str | None = None
    order_plan_unty_no: str | None = None
    prcrmnt_req_no: str | None = None


PHASE2_TIER1_OPERATION_SPECS = (
    G2BSyncOperationSpec(
        name="getBidPblancListInfoServc",
        stage="base_list",
        priority=1,
        purpose="용역 본공고 마스터 생성",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoThng",
        stage="base_list",
        priority=1,
        purpose="물품 본공고 마스터 생성",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoCnstwk",
        stage="base_list",
        priority=1,
        purpose="공사 본공고 마스터 생성",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoFrgcpt",
        stage="base_list",
        priority=1,
        purpose="외자 본공고 마스터 생성",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoLicenseLimit",
        stage="detail_enrichment",
        priority=2,
        purpose="면허 제한 보강",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoPrtcptPsblRgn",
        stage="detail_enrichment",
        priority=2,
        purpose="참가 가능 지역 보강",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoEorderAtchFileInfo",
        stage="detail_enrichment",
        priority=2,
        purpose="e발주 첨부파일 보강",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoThngPurchsObjPrdct",
        stage="detail_enrichment",
        priority=2,
        purpose="물품 구매대상 보강",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoServcPurchsObjPrdct",
        stage="detail_enrichment",
        priority=2,
        purpose="용역 구매대상 보강",
    ),
    G2BSyncOperationSpec(
        name="getBidPblancListInfoFrgcptPurchsObjPrdct",
        stage="detail_enrichment",
        priority=2,
        purpose="외자 구매대상 보강",
    ),
    G2BSyncOperationSpec(
        name="contractProcessIntegration",
        stage="timeline_enrichment",
        priority=3,
        purpose="입찰 이후 타임라인 보강",
    ),
    G2BSyncOperationSpec(
        name="industryBaseLaw",
        stage="reference_enrichment",
        priority=4,
        purpose="참가 자격/업종 기준정보 보강",
    ),
)

PHASE2_BASE_LIST_OPERATIONS = tuple(
    spec.name for spec in PHASE2_TIER1_OPERATION_SPECS if spec.stage == "base_list"
)

PHASE2_DETAIL_ENRICHMENT_OPERATIONS = tuple(
    spec.name
    for spec in PHASE2_TIER1_OPERATION_SPECS
    if spec.stage == "detail_enrichment"
)

PHASE2_TIMELINE_ENRICHMENT_OPERATIONS = tuple(
    spec.name
    for spec in PHASE2_TIER1_OPERATION_SPECS
    if spec.stage == "timeline_enrichment"
)

PHASE2_REFERENCE_ENRICHMENT_OPERATIONS = tuple(
    spec.name
    for spec in PHASE2_TIER1_OPERATION_SPECS
    if spec.stage == "reference_enrichment"
)

PHASE2_SYNC_SEQUENCE = (
    "base_list",
    "detail_enrichment",
    "timeline_enrichment",
    "reference_enrichment",
)

PHASE2_DETAIL_ENRICHMENT_TARGET_STATUSES = ("reviewing", "favorite", "submitted")


def extract_connection_keys(item: dict[str, Any]) -> G2BConnectionKeys:
    def _pick(*names: str) -> str | None:
        for name in names:
            value = item.get(name)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    return G2BConnectionKeys(
        bid_ntce_no=_pick("bidNtceNo", "untyNtceNo"),
        bf_spec_rgst_no=_pick("bfSpecRgstNo", "bfSpecRgstNo1"),
        order_plan_no=_pick("orderPlanNo"),
        order_plan_unty_no=_pick("orderPlanUntyNo"),
        prcrmnt_req_no=_pick("prcrmntReqNo"),
    )


def should_run_detail_enrichment(
    *,
    status: str | None,
    is_favorite: bool,
    changed_recently: bool,
    is_new_bid: bool,
) -> bool:
    if is_favorite or changed_recently or is_new_bid:
        return True
    normalized_status = (status or "").strip().lower()
    return normalized_status in PHASE2_DETAIL_ENRICHMENT_TARGET_STATUSES
