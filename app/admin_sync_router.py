from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select

from app.api_schemas import (
    BidCrawlRequest,
    BidCrawlResponse,
    BidDetailEnrichmentRequest,
    BidDetailEnrichmentResponse,
    BidPublicInfoSyncRequest,
    BidPublicInfoSyncResponse,
    ContractProcessSyncRequest,
    ContractProcessSyncResponse,
    JobLogCleanupRequest,
    JobLogCleanupResponse,
    Phase2BatchSyncRequest,
    Phase2BatchSyncResponse,
    SyncOperationItemResponse,
    SyncOperationListResponse,
)
from app.cleanup_job_logs import cleanup_job_logs
from app.clients import (
    G2BBidPublicInfoClient,
    G2BContractProcessClient,
    G2BIndustryInfoClient,
)
from app.config import settings
from app.db import engine
from app.models import SyncJobLog
from app.services import (
    G2BBidCrawlService,
    G2BBidChangeHistoryService,
    G2BBidDetailEnrichmentService,
    G2BReferenceEnrichmentService,
    G2BBidPublicInfoSyncService,
    G2BContractProcessService,
)
from app.services.g2b_bid_page_crawler import G2BBidPageCrawler
from app.services.g2b_bid_sync_service import DEFAULT_BID_PUBLIC_INFO_OPERATIONS
from app.services.g2b_sync_plan import PHASE2_DETAIL_ENRICHMENT_OPERATIONS
from app.services.sync_logging import build_sync_failure_message


router = APIRouter(prefix="/admin", tags=["admin-sync"])
admin_sync_token_header = APIKeyHeader(name="X-Admin-Token", auto_error=True)

ADMIN_AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Missing admin sync token",
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
    },
    403: {
        "description": "Invalid admin sync token",
        "content": {
            "application/json": {"example": {"detail": "Invalid admin sync token"}}
        },
    },
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {
                    "detail": [
                        {
                            "type": "missing",
                            "loc": ["body", "begin"],
                            "msg": "Field required",
                            "input": {
                                "end": "202603132359",
                                "operations": ["getBidPblancListInfoServc"],
                                "rows": 100,
                            },
                        }
                    ]
                }
            }
        },
    },
}


def require_admin_sync_token(
    x_admin_token: str = Security(admin_sync_token_header),
) -> None:
    if x_admin_token != settings.admin_sync_token:
        raise HTTPException(status_code=403, detail="Invalid admin sync token")


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _status_value(value: str) -> Literal["completed", "failed", "running"]:
    if value == "completed":
        return "completed"
    if value == "running":
        return "running"
    return "failed"


def _log_job(
    *,
    session: Session,
    job_type: str,
    target: str,
    status: str,
    started_at: datetime,
    message: str,
) -> SyncJobLog:
    log = SyncJobLog(
        job_type=job_type,
        target=target,
        status=status,
        started_at=started_at,
        finished_at=datetime.now(),
        message=message,
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.post(
    "/sync/bid-public-info",
    response_model=BidPublicInfoSyncResponse,
    summary="Sync bid public info",
    description=(
        "G2B 입찰공고정보서비스를 호출해 공고 기본 정보를 수집하고 DB에 upsert합니다. "
        "Swagger UI에서는 `X-Admin-Token` 인증 후 begin/end 조회 구간과 operation 목록을 지정해 실행합니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def sync_bid_public_info(
    payload: BidPublicInfoSyncRequest,
    _: None = Depends(require_admin_sync_token),
) -> BidPublicInfoSyncResponse:
    started_at = datetime.now()
    client = G2BBidPublicInfoClient()
    operations = (
        tuple(payload.operations)
        if payload.operations
        else DEFAULT_BID_PUBLIC_INFO_OPERATIONS
    )
    target = ",".join(operations)

    try:
        with Session(engine) as session:
            result = G2BBidPublicInfoSyncService(
                session=session, client=client
            ).sync_bid_notices(
                inqry_bgn_dt=payload.begin,
                inqry_end_dt=payload.end,
                operations=operations,
                num_of_rows=payload.rows,
            )
            log = _log_job(
                session=session,
                job_type="bid_public_info_sync",
                target=target,
                status="completed",
                started_at=started_at,
                message=f"fetched {result.fetched_count} bids, upserted {result.upserted_count} bids",
            )
            return BidPublicInfoSyncResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                fetched_count=result.fetched_count,
                upserted_count=result.upserted_count,
                bid_ids=result.bid_ids,
            )
    except Exception as exc:
        with Session(engine) as session:
            log = _log_job(
                session=session,
                job_type="bid_public_info_sync",
                target=target,
                status="failed",
                started_at=started_at,
                message=build_sync_failure_message(exc),
            )
        return BidPublicInfoSyncResponse(
            job_type=log.job_type,
            target=log.target,
            status=_status_value(log.status),
            message=log.message,
            started_at=_format_datetime(log.started_at),
            finished_at=_format_datetime(log.finished_at),
            fetched_count=0,
            upserted_count=0,
            bid_ids=[],
        )
    finally:
        client.close()


@router.post(
    "/sync/bid-detail-enrichment",
    response_model=BidDetailEnrichmentResponse,
    summary="Enrich bid details",
    description=(
        "기존 공고에 대해 상세 보강 operation을 실행합니다. 특정 `bid_ids`만 보강하거나, "
        "`selection_mode`와 `recent_days`를 이용해 최근 변경 공고를 일괄 보강할 수 있습니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def sync_bid_detail_enrichment(
    payload: BidDetailEnrichmentRequest,
    _: None = Depends(require_admin_sync_token),
) -> BidDetailEnrichmentResponse:
    started_at = datetime.now()
    client = G2BBidPublicInfoClient()
    operations = (
        tuple(payload.operations)
        if payload.operations
        else PHASE2_DETAIL_ENRICHMENT_OPERATIONS
    )
    target = ",".join(payload.bid_ids) if payload.bid_ids else "all-bids"

    try:
        with Session(engine) as session:
            result = G2BBidDetailEnrichmentService(
                session=session, client=client
            ).enrich_bids(
                bid_ids=payload.bid_ids,
                operations=operations,
                num_of_rows=payload.rows,
                selection_mode=payload.selection_mode,
                recent_days=payload.recent_days,
            )
            log = _log_job(
                session=session,
                job_type="bid_detail_enrichment",
                target=target,
                status="completed",
                started_at=started_at,
                message=(
                    f"operations={','.join(operations)} selection_mode={payload.selection_mode} "
                    f"processed {len(result.processed_bid_ids)} bids, fetched {result.fetched_item_count} items"
                ),
            )
            return BidDetailEnrichmentResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                processed_bid_ids=result.processed_bid_ids,
                fetched_item_count=result.fetched_item_count,
            )
    except Exception as exc:
        with Session(engine) as session:
            log = _log_job(
                session=session,
                job_type="bid_detail_enrichment",
                target=target,
                status="failed",
                started_at=started_at,
                message=(
                    f"operations={','.join(operations)} selection_mode={payload.selection_mode} "
                    f"{build_sync_failure_message(exc)}"
                ),
            )
        return BidDetailEnrichmentResponse(
            job_type=log.job_type,
            target=log.target,
            status=_status_value(log.status),
            message=log.message,
            started_at=_format_datetime(log.started_at),
            finished_at=_format_datetime(log.finished_at),
            processed_bid_ids=[],
            fetched_item_count=0,
        )
    finally:
        client.close()


@router.post(
    "/sync/contract-process",
    response_model=ContractProcessSyncResponse,
    summary="Sync contract process",
    description=(
        "계약과정통합공개 데이터를 조회해 선택한 공고의 timeline 데이터를 보강합니다. "
        "`bid_ids`를 비우면 서비스가 정의한 대상 공고 기준으로 처리합니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def sync_contract_process(
    payload: ContractProcessSyncRequest,
    _: None = Depends(require_admin_sync_token),
) -> ContractProcessSyncResponse:
    started_at = datetime.now()
    client = G2BContractProcessClient()
    target = ",".join(payload.bid_ids) if payload.bid_ids else "all-bids"

    try:
        with Session(engine) as session:
            result = G2BContractProcessService(
                session=session, client=client
            ).enrich_timelines(
                bid_ids=payload.bid_ids,
                num_of_rows=payload.rows,
            )
            log = _log_job(
                session=session,
                job_type="contract_process_sync",
                target=target,
                status="completed",
                started_at=started_at,
                message=f"processed {len(result.processed_bid_ids)} bids, fetched {result.fetched_item_count} items",
            )
            return ContractProcessSyncResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                processed_bid_ids=result.processed_bid_ids,
                fetched_item_count=result.fetched_item_count,
            )
    except Exception as exc:
        with Session(engine) as session:
            log = _log_job(
                session=session,
                job_type="contract_process_sync",
                target=target,
                status="failed",
                started_at=started_at,
                message=build_sync_failure_message(exc),
            )
        return ContractProcessSyncResponse(
            job_type=log.job_type,
            target=log.target,
            status=_status_value(log.status),
            message=log.message,
            started_at=_format_datetime(log.started_at),
            finished_at=_format_datetime(log.finished_at),
            processed_bid_ids=[],
            fetched_item_count=0,
        )
    finally:
        client.close()


@router.post(
    "/sync/bid-crawl",
    response_model=BidCrawlResponse,
    summary="Crawl bid detail pages",
    description=(
        "Playwright로 공고 상세 페이지를 열어 본문과 첨부 메타데이터를 수집합니다. "
        "크롤링 대상 `bid_ids`는 반드시 지정해야 하며, `headless`로 브라우저 실행 모드를 덮어쓸 수 있습니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def sync_bid_crawl(
    payload: BidCrawlRequest,
    _: None = Depends(require_admin_sync_token),
) -> BidCrawlResponse:
    started_at = datetime.now()
    crawler = G2BBidPageCrawler(headless=payload.headless)
    target = ",".join(payload.bid_ids)

    try:
        with Session(engine) as session:
            result = G2BBidCrawlService(session=session, crawler=crawler).crawl_bids(
                bid_ids=payload.bid_ids,
            )
            log = _log_job(
                session=session,
                job_type="bid_page_crawl",
                target=target,
                status="completed",
                started_at=started_at,
                message=f"processed {len(result.processed_bid_ids)} bids, stored {result.attachment_count} attachments",
            )
            return BidCrawlResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                processed_bid_ids=result.processed_bid_ids,
                attachment_count=result.attachment_count,
            )
    except Exception as exc:
        with Session(engine) as session:
            log = _log_job(
                session=session,
                job_type="bid_page_crawl",
                target=target,
                status="failed",
                started_at=started_at,
                message=build_sync_failure_message(exc),
            )
        return BidCrawlResponse(
            job_type=log.job_type,
            target=log.target,
            status=_status_value(log.status),
            message=log.message,
            started_at=_format_datetime(log.started_at),
            finished_at=_format_datetime(log.finished_at),
            processed_bid_ids=[],
            attachment_count=0,
        )


@router.post(
    "/sync/phase2-batch",
    response_model=Phase2BatchSyncResponse,
    summary="Run phase 2 batch sync",
    description=(
        "상세 보강, 계약과정통합공개, Playwright 크롤링을 한 번에 실행하는 관리자용 배치 API입니다. "
        "`skip_*` 플래그로 특정 단계를 생략할 수 있습니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def sync_phase2_batch(
    payload: Phase2BatchSyncRequest,
    _: None = Depends(require_admin_sync_token),
) -> Phase2BatchSyncResponse:
    started_at = datetime.now()
    detail_client = G2BBidPublicInfoClient()
    contract_client = G2BContractProcessClient()
    industry_client = G2BIndustryInfoClient()
    crawler = G2BBidPageCrawler()
    target = ",".join(payload.bid_ids) if payload.bid_ids else "all-bids"

    try:
        with Session(engine) as session:
            processed_bid_ids = list(payload.bid_ids or [])
            detail_items = 0
            change_history_items = 0
            contract_items = 0
            crawl_attachments = 0
            reference_items = 0

            if not payload.skip_detail:
                detail_result = G2BBidDetailEnrichmentService(
                    session=session, client=detail_client
                ).enrich_bids(
                    bid_ids=payload.bid_ids,
                    operations=PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
                    num_of_rows=payload.rows,
                    selection_mode=payload.selection_mode,
                    recent_days=payload.recent_days,
                )
                processed_bid_ids = detail_result.processed_bid_ids
                detail_items = detail_result.fetched_item_count

            if payload.skip_detail and not processed_bid_ids:
                raise ValueError("skip_detail=true 인 경우 bid_ids가 필요합니다")

            if not payload.skip_change_history:
                change_history_result = G2BBidChangeHistoryService(
                    session=session, client=detail_client
                ).sync_change_history(
                    bid_ids=processed_bid_ids or None,
                    num_of_rows=payload.rows,
                )
                change_history_items = change_history_result.fetched_item_count

            if not payload.skip_contract:
                contract_result = G2BContractProcessService(
                    session=session, client=contract_client
                ).enrich_timelines(
                    bid_ids=processed_bid_ids or None,
                    num_of_rows=payload.rows,
                )
                contract_items = contract_result.fetched_item_count

            if not payload.skip_crawl:
                crawl_result = G2BBidCrawlService(
                    session=session, crawler=crawler
                ).crawl_bids(
                    bid_ids=processed_bid_ids,
                )
                crawl_attachments = crawl_result.attachment_count

            if not payload.skip_reference:
                reference_result = G2BReferenceEnrichmentService(
                    session=session, client=industry_client
                ).enrich_bids(
                    bid_ids=processed_bid_ids,
                    num_of_rows=payload.rows,
                )
                reference_items = reference_result.fetched_item_count

            log = _log_job(
                session=session,
                job_type="phase2_batch_sync",
                target=",".join(processed_bid_ids) if processed_bid_ids else target,
                status="completed",
                started_at=started_at,
                message=(
                    f"selection_mode={payload.selection_mode} processed {len(processed_bid_ids)} bids "
                    f"detail_items={detail_items} change_history_items={change_history_items} contract_items={contract_items} "
                    f"crawl_attachments={crawl_attachments} reference_items={reference_items}"
                ),
            )
            return Phase2BatchSyncResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                processed_bid_ids=processed_bid_ids,
                detail_items=detail_items,
                change_history_items=change_history_items,
                contract_items=contract_items,
                crawl_attachments=crawl_attachments,
                reference_items=reference_items,
            )
    except Exception as exc:
        with Session(engine) as session:
            log = _log_job(
                session=session,
                job_type="phase2_batch_sync",
                target=target,
                status="failed",
                started_at=started_at,
                message=f"selection_mode={payload.selection_mode} {build_sync_failure_message(exc)}",
            )
            return Phase2BatchSyncResponse(
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                message=log.message,
                started_at=_format_datetime(log.started_at),
                finished_at=_format_datetime(log.finished_at),
                processed_bid_ids=[],
                detail_items=0,
                change_history_items=0,
                contract_items=0,
                crawl_attachments=0,
                reference_items=0,
            )
    finally:
        detail_client.close()
        contract_client.close()
        industry_client.close()


@router.get(
    "/operations",
    response_model=SyncOperationListResponse,
    summary="List sync operations",
    description=(
        "최근 관리자 동기화 실행 로그를 조회합니다. `status`, `job_type`, `limit` 쿼리로 "
        "성공/실패 이력과 작업 유형별 로그를 필터링할 수 있습니다."
    ),
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def list_sync_operations(
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_admin_sync_token),
) -> SyncOperationListResponse:
    with Session(engine) as session:
        statement = select(SyncJobLog)
        if status:
            statement = statement.where(SyncJobLog.status == status)
        if job_type:
            statement = statement.where(SyncJobLog.job_type == job_type)
        logs = sorted(
            session.exec(statement).all(),
            key=lambda item: item.started_at or datetime.min,
            reverse=True,
        )[:limit]

    return SyncOperationListResponse(
        items=[
            SyncOperationItemResponse(
                id=log.id,
                job_type=log.job_type,
                target=log.target,
                status=_status_value(log.status),
                started_at=_format_datetime(log.started_at) or "-",
                finished_at=_format_datetime(log.finished_at),
                message=log.message,
            )
            for log in logs
        ]
    )


@router.post(
    "/jobs/cleanup",
    response_model=JobLogCleanupResponse,
    summary="Cleanup job logs",
    description="오래된 sync job 로그를 삭제하거나 dry-run으로 삭제 예정 개수를 확인합니다.",
    responses=ADMIN_AUTH_ERROR_RESPONSES,
)
def cleanup_sync_job_logs(
    payload: JobLogCleanupRequest,
    _: None = Depends(require_admin_sync_token),
) -> JobLogCleanupResponse:
    result = cleanup_job_logs(
        older_than_days=payload.older_than_days,
        status=payload.status,
        job_type=payload.job_type,
        dry_run=payload.dry_run,
    )
    return JobLogCleanupResponse(
        deleted_count=result.deleted_count,
        cutoff_at=result.cutoff_at.strftime("%Y-%m-%d %H:%M"),
        dry_run=payload.dry_run,
    )
