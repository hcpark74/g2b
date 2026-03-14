import csv
from copy import deepcopy
from contextlib import asynccontextmanager
from datetime import datetime
from io import StringIO
import json
from pathlib import Path
from typing import Literal, cast

from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.exceptions import HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.admin_sync_router import router as admin_sync_router
from app.api_schemas import (
    ApiErrorDetail,
    ApiErrorResponse,
    BidAttachmentItemResponse,
    BidAttachmentsApiResponse,
    BidAttachmentsDataResponse,
    BidDetailResponseItem,
    BidDetailApiResponse,
    BidListDataResponse,
    BidListApiResponse,
    BidListItemResponse,
    BidListMetaResponse,
    BidStatusUpdateRequest,
    JobListApiResponse,
    JobListDataResponse,
    JobListItemResponse,
    JobListMetaResponse,
    JobStatusApiResponse,
    JobStatusDataResponse,
    BidTimelineApiResponse,
    BidTimelineDataResponse,
    BidTimelineItemResponse,
    QueuedSyncResponse,
)
from app.config import settings
from app.db import engine, init_db
from app.models import BID_STATUS_OPTIONS, Bid, SyncJobLog  # noqa: F401
from app.presentation.mappers import (
    build_bid_drawer_vm,
    build_bids_page_vm,
    build_favorites_page_vm,
    build_operations_page_vm,
    build_prespecs_page_vm,
    build_results_page_vm,
    build_secondary_page_vm,
)
from app.repositories import (
    SampleBidRepository,
    SampleOperationRepository,
    SamplePageRepository,
    SqlModelBidRepository,
    SqlModelOperationRepository,
    SqlModelPageRepository,
)
from app.clients import G2BBidPublicInfoClient, G2BContractProcessClient
from app.services import (
    BidQueryService,
    G2BBidCrawlService,
    G2BContractProcessService,
    G2BBidDetailEnrichmentService,
    OperationQueryService,
    PageQueryService,
)
from app.services.g2b_bid_page_crawler import G2BBidPageCrawler
from app.services.g2b_sync_plan import PHASE2_DETAIL_ENRICHMENT_OPERATIONS
from app.services.sync_logging import build_sync_failure_message


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
)
app.include_router(admin_sync_router)
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


LAST_SYNCED_AT = "2026-03-12 19:45"
SWAGGER_CUSTOM_STYLES = """
<style>
  :root {
    --docs-swagger-accent: #2168b4;
    --docs-swagger-accent-strong: #0f4f92;
    --docs-swagger-soft: #eef5fd;
    --docs-swagger-line: #d8e4f0;
    --docs-swagger-text: #1e3953;
  }

  body {
    margin: 0;
    background: linear-gradient(180deg, #f7fbff 0%, #f1f6fc 100%);
    font-family: "Noto Sans KR", "Malgun Gothic", sans-serif;
  }

  .swagger-ui .topbar {
    display: none;
  }

  .swagger-ui {
    color: var(--docs-swagger-text);
  }

  .swagger-ui .info {
    margin: 0;
    padding: 1rem 1rem 0.5rem;
  }

  .swagger-ui .info .title {
    color: var(--docs-swagger-accent-strong);
    font-size: 1.45rem;
    font-weight: 800;
  }

  .swagger-ui .scheme-container {
    background: #fff;
    box-shadow: none;
    border-top: 1px solid var(--docs-swagger-line);
    border-bottom: 1px solid var(--docs-swagger-line);
    padding: 0.85rem 1rem;
  }

  .swagger-ui .opblock-tag {
    border-bottom: 1px solid var(--docs-swagger-line);
    color: var(--docs-swagger-accent-strong);
    font-weight: 800;
  }

  .swagger-ui .opblock {
    border-radius: 12px;
    overflow: hidden;
    border-width: 1px;
    box-shadow: 0 8px 18px rgba(54, 88, 130, 0.08);
  }

  .swagger-ui .opblock .opblock-summary {
    border-color: var(--docs-swagger-line);
  }

  .swagger-ui .opblock.opblock-get {
    border-color: #90bceb;
    background: #edf5ff;
  }

  .swagger-ui .opblock.opblock-post {
    border-color: #87c7b0;
    background: #eefaf5;
  }

  .swagger-ui .opblock.opblock-delete {
    border-color: #e5a1a1;
    background: #fff3f3;
  }

  .swagger-ui .opblock.opblock-put,
  .swagger-ui .opblock.opblock-patch {
    border-color: #e6c180;
    background: #fff8eb;
  }

  .swagger-ui .btn.execute {
    background: var(--docs-swagger-accent);
    border-color: var(--docs-swagger-accent);
  }

  .swagger-ui .btn.execute:hover {
    background: var(--docs-swagger-accent-strong);
    border-color: var(--docs-swagger-accent-strong);
  }

  .swagger-ui .btn.authorize,
  .swagger-ui .btn.cancel {
    border-radius: 999px;
  }

  .swagger-ui table thead tr td,
  .swagger-ui table thead tr th {
    color: var(--docs-swagger-accent-strong);
  }

  .swagger-ui section.models {
    border: 1px solid var(--docs-swagger-line);
    border-radius: 12px;
    overflow: hidden;
  }
</style>
"""
DOCS_NAV_ITEMS = [
    {
        "id": "g2b-bid-service",
        "group": "조달청_나라장터",
        "label": "입찰공고서비스",
        "description": "나라장터 입찰공고 목록, 상세, 첨부파일, 타임라인, 관심등록 및 재동기화 API를 제공합니다.",
        "openapi_path": "/docs/openapi/g2b-bid-service.json",
        "tags": ["bids"],
        "provider": "조달청_나라장터",
        "category": "입찰 / 공고 조회",
        "protocol": "REST / JSON",
        "version_label": "OpenAPI 3.1 / v1",
        "audience": "공공조달 데이터 조회 서비스 개발자",
        "updated_at": "2026-03-14",
        "base_url": "/api/v1/bids",
        "notes": "조회형 API와 상태 변경 API가 함께 포함되며 Swagger UI에서 즉시 테스트할 수 있습니다.",
    },
    {
        "id": "g2b-job-service",
        "group": "운영 / 모니터링",
        "label": "작업이력서비스",
        "description": "동기화 작업 이력 목록과 개별 작업 상태를 조회하는 운영 API를 제공합니다.",
        "openapi_path": "/docs/openapi/g2b-job-service.json",
        "tags": ["jobs"],
        "provider": "g2b 운영 API",
        "category": "운영 / 작업 모니터링",
        "protocol": "REST / JSON",
        "version_label": "OpenAPI 3.1 / v1",
        "audience": "운영자 및 관리자 대시보드 개발자",
        "updated_at": "2026-03-14",
        "base_url": "/api/v1/jobs",
        "notes": "최근 실행 이력, 상태별 필터링, 작업 상세 추적에 필요한 API만 분리해 제공합니다.",
    },
    {
        "id": "g2b-admin-sync-service",
        "group": "운영 / 관리자",
        "label": "관리자동기화서비스",
        "description": "관리자 토큰 기반 수동 동기화 실행과 운영성 작업을 위한 API를 제공합니다.",
        "openapi_path": "/docs/openapi/g2b-admin-sync-service.json",
        "tags": ["admin-sync"],
        "provider": "g2b 관리자 API",
        "category": "관리 / 수동 동기화",
        "protocol": "REST / JSON",
        "version_label": "OpenAPI 3.1 / admin",
        "audience": "백오피스 운영자 및 배치 관리 도구 개발자",
        "updated_at": "2026-03-14",
        "base_url": "/admin",
        "notes": "X-Admin-Token 인증이 필요하며 배치 실행, 상세보강, 계약처리, 작업 정리 API를 포함합니다.",
    },
]
page_query_service = PageQueryService(repository=SamplePageRepository())
operation_query_service = OperationQueryService(repository=SampleOperationRepository())


def list_raw_bids(
    *,
    search_query: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    closed_from: str | None = None,
    closed_to: str | None = None,
    sort: str = "posted_at",
    order: str = "desc",
) -> list[dict[str, object]]:
    if settings.bid_data_backend == "sample":
        return BidQueryService(repository=SampleBidRepository()).list_bids(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )

    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            bids = BidQueryService(repository=SqlModelBidRepository(session)).list_bids(
                search_query=search_query,
                status=status,
                favorites_only=favorites_only,
                keyword=keyword,
                org=org,
                budget_min=budget_min,
                budget_max=budget_max,
                closed_from=closed_from,
                closed_to=closed_to,
                sort=sort,
                order=order,
            )
        if bids or settings.bid_data_backend == "sqlmodel":
            return bids

    return BidQueryService(repository=SampleBidRepository()).list_bids(
        search_query=search_query,
        status=status,
        favorites_only=favorites_only,
        keyword=keyword,
        org=org,
        budget_min=budget_min,
        budget_max=budget_max,
        closed_from=closed_from,
        closed_to=closed_to,
        sort=sort,
        order=order,
    )


def list_raw_bids_page(
    *,
    page: int,
    page_size: int,
    search_query: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    closed_from: str | None = None,
    closed_to: str | None = None,
    sort: str = "posted_at",
    order: str = "desc",
):
    if settings.bid_data_backend == "sample":
        return BidQueryService(repository=SampleBidRepository()).list_bids_page(
            page=page,
            page_size=page_size,
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )

    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            result = BidQueryService(
                repository=SqlModelBidRepository(session)
            ).list_bids_page(
                page=page,
                page_size=page_size,
                search_query=search_query,
                status=status,
                favorites_only=favorites_only,
                keyword=keyword,
                org=org,
                budget_min=budget_min,
                budget_max=budget_max,
                closed_from=closed_from,
                closed_to=closed_to,
                sort=sort,
                order=order,
            )
        if result.items or result.total > 0 or settings.bid_data_backend == "sqlmodel":
            return result

    return BidQueryService(repository=SampleBidRepository()).list_bids_page(
        page=page,
        page_size=page_size,
        search_query=search_query,
        status=status,
        favorites_only=favorites_only,
        keyword=keyword,
        org=org,
        budget_min=budget_min,
        budget_max=budget_max,
        closed_from=closed_from,
        closed_to=closed_to,
        sort=sort,
        order=order,
    )


def get_raw_bid(bid_id: str) -> dict[str, object]:
    if settings.bid_data_backend == "sample":
        return BidQueryService(repository=SampleBidRepository()).get_bid(bid_id)

    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            repository = SqlModelBidRepository(session)
            try:
                return BidQueryService(repository=repository).get_bid(bid_id)
            except KeyError:
                if settings.bid_data_backend == "sqlmodel":
                    raise

    return BidQueryService(repository=SampleBidRepository()).get_bid(bid_id)


def get_last_synced_at(raw_bids: list[dict[str, object]]) -> str:
    timestamps = [str(bid.get("last_synced_at", "")).strip() for bid in raw_bids]
    valid_timestamps = [
        timestamp for timestamp in timestamps if timestamp and timestamp != "-"
    ]
    if not valid_timestamps:
        return LAST_SYNCED_AT
    return max(valid_timestamps)


def get_docs_nav_item(doc_id: str) -> dict[str, object]:
    for item in DOCS_NAV_ITEMS:
        if item["id"] == doc_id:
            return item
    raise HTTPException(status_code=404, detail="Document not found")


def get_grouped_docs_nav_items() -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in DOCS_NAV_ITEMS:
        grouped.setdefault(cast(str, item["group"]), []).append(item)

    return [
        {"group": group_name, "items": items} for group_name, items in grouped.items()
    ]


def build_filtered_openapi_schema(doc_id: str) -> dict[str, object]:
    nav_item = get_docs_nav_item(doc_id)
    allowed_tags = set(cast(list[str], nav_item["tags"]))
    schema = deepcopy(app.openapi())
    filtered_paths: dict[str, object] = {}

    for path, methods in schema["paths"].items():
        filtered_methods = {}

        for method, operation in methods.items():
            operation_tags = set(operation.get("tags", []))
            if operation_tags & allowed_tags:
                filtered_methods[method] = operation

        if filtered_methods:
            filtered_paths[path] = filtered_methods

    schema["paths"] = filtered_paths
    schema["tags"] = [
        tag for tag in schema.get("tags", []) if tag.get("name") in allowed_tags
    ]
    return schema


def list_operation_items() -> list[dict[str, str]]:
    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            items = OperationQueryService(
                repository=SqlModelOperationRepository(session)
            ).list_operations()
        if items or settings.bid_data_backend == "sqlmodel":
            return items

    return operation_query_service.list_operations()


def get_operations_last_synced_at(items: list[dict[str, str]]) -> str:
    timestamps = [
        item.get("finished_at", "")
        for item in items
        if item.get("finished_at") not in {None, "-"}
    ]
    if not timestamps:
        return LAST_SYNCED_AT
    return max(timestamps)


def get_bids_page_context(
    search_query: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
) -> dict[str, object]:
    raw_bids = list_raw_bids(
        search_query=search_query,
        status=status,
        favorites_only=favorites_only,
    )
    last_synced_at = get_last_synced_at(raw_bids)
    page_vm = build_bids_page_vm(
        raw_bids,
        last_synced_at=last_synced_at,
        active_nav="bids",
    )
    return {
        "page_vm": page_vm,
        "last_synced_at": page_vm.summary.last_synced_at,
        "active_nav": page_vm.active_nav,
        "selected_bid": page_vm.selected_bid,
        "search_query": (search_query or "").strip(),
        "status_filter": (status or "").strip(),
        "favorites_only": favorites_only,
        "bid_status_options": BID_STATUS_OPTIONS,
    }


def get_basic_page_context(active_nav: str) -> dict[str, object]:
    page_meta = {
        "prespecs": (
            "사전 탐색",
            "발주계획, 사전규격, 조달요청 화면이 여기에 배치됩니다.",
        ),
        "results": ("사후 분석", "낙찰 및 계약 결과 분석 화면이 여기에 배치됩니다."),
        "favorites": ("관심 공고", "즐겨찾기한 공고 목록 화면이 여기에 배치됩니다."),
        "operations": (
            "운영 현황",
            "동기화 상태와 실패 로그 화면이 여기에 배치됩니다.",
        ),
    }
    title, description = page_meta[active_nav]
    page_vm = build_secondary_page_vm(
        title=title,
        description=description,
        active_nav=active_nav,
        last_synced_at=LAST_SYNCED_AT,
    )
    return {
        "active_nav": active_nav,
        "last_synced_at": LAST_SYNCED_AT,
        "selected_bid": None,
        "page_vm": page_vm,
    }


def get_prespecs_page_context() -> dict[str, object]:
    page_vm = build_prespecs_page_vm(page_query_service.list_prespecs(), LAST_SYNCED_AT)
    return {
        "active_nav": page_vm.active_nav,
        "last_synced_at": page_vm.last_synced_at,
        "selected_bid": None,
        "page_vm": page_vm,
        "summary_stats": page_vm.summary.items,
        "items": page_vm.items,
    }


def list_result_items() -> list[dict[str, str]]:
    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            items = PageQueryService(
                repository=SqlModelPageRepository(session)
            ).list_results()
        if items or settings.bid_data_backend == "sqlmodel":
            return items

    return page_query_service.list_results()


def get_results_page_context() -> dict[str, object]:
    page_vm = build_results_page_vm(list_result_items(), LAST_SYNCED_AT)
    return {
        "active_nav": page_vm.active_nav,
        "last_synced_at": page_vm.last_synced_at,
        "selected_bid": None,
        "page_vm": page_vm,
        "summary_stats": page_vm.summary.items,
        "items": page_vm.items,
    }


def get_favorites_page_context(
    search_query: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    raw_bids = list_raw_bids(
        search_query=search_query,
        status=status,
        favorites_only=True,
    )
    last_synced_at = get_last_synced_at(raw_bids)
    favorite_bids = [
        bid
        for bid in build_bids_page_vm(raw_bids, last_synced_at=last_synced_at).bids
        if bid.favorite
    ]
    page_vm = build_favorites_page_vm(favorite_bids, last_synced_at)
    return {
        "active_nav": page_vm.active_nav,
        "last_synced_at": page_vm.last_synced_at,
        "selected_bid": None,
        "page_vm": page_vm,
        "summary_stats": page_vm.summary.items,
        "items": page_vm.items,
        "search_query": (search_query or "").strip(),
        "status_filter": (status or "").strip(),
        "favorites_only": True,
        "force_favorites_only": True,
        "filter_form_action": "/favorites",
        "filter_hx_get": "/partials/favorites/table",
        "filter_hx_target": "#favorites-table-container",
        "bid_status_options": BID_STATUS_OPTIONS,
    }


def get_operations_page_context(
    status_filter: str | None = None, job_type_filter: str | None = None
) -> dict[str, object]:
    all_items = list_operation_items()
    items = all_items
    normalized_status_filter = (status_filter or "").strip().lower()
    normalized_job_type_filter = (job_type_filter or "").strip()

    if normalized_status_filter in {"completed", "running", "failed"}:
        items = [
            item for item in items if item.get("status") == normalized_status_filter
        ]
    if normalized_job_type_filter:
        items = [
            item for item in items if item.get("job_type") == normalized_job_type_filter
        ]

    last_synced_at = get_operations_last_synced_at(items)
    page_vm = build_operations_page_vm(items, last_synced_at)
    available_job_types = sorted(
        {
            str(item.get("job_type", "")).strip()
            for item in all_items
            if str(item.get("job_type", "")).strip()
        }
    )
    return {
        "active_nav": page_vm.active_nav,
        "last_synced_at": page_vm.last_synced_at,
        "selected_bid": None,
        "page_vm": page_vm,
        "summary_stats": page_vm.summary.items,
        "items": page_vm.items,
        "status_filter": normalized_status_filter,
        "job_type_filter": normalized_job_type_filter,
        "available_job_types": available_job_types,
    }


def get_selected_raw_bid(bid_id: str) -> dict[str, object]:
    return get_raw_bid(bid_id)


def update_raw_bid_status(bid_id: str, status: str) -> dict[str, object]:
    if settings.bid_data_backend == "sample":
        return BidQueryService(repository=SampleBidRepository()).update_bid_status(
            bid_id, status
        )

    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            repository = SqlModelBidRepository(session)
            try:
                return BidQueryService(repository=repository).update_bid_status(
                    bid_id, status
                )
            except KeyError:
                if settings.bid_data_backend == "sqlmodel":
                    raise

    return BidQueryService(repository=SampleBidRepository()).update_bid_status(
        bid_id, status
    )


def set_raw_bid_favorite(bid_id: str, favorite: bool) -> dict[str, object]:
    if settings.bid_data_backend == "sample":
        return BidQueryService(repository=SampleBidRepository()).set_bid_favorite(
            bid_id, favorite
        )

    if settings.bid_data_backend in {"sqlmodel", "auto"}:
        with Session(engine) as session:
            repository = SqlModelBidRepository(session)
            try:
                return BidQueryService(repository=repository).set_bid_favorite(
                    bid_id, favorite
                )
            except KeyError:
                if settings.bid_data_backend == "sqlmodel":
                    raise

    return BidQueryService(repository=SampleBidRepository()).set_bid_favorite(
        bid_id, favorite
    )


def build_api_error_response(
    *, status_code: int, code: str, message: str
) -> JSONResponse:
    payload = ApiErrorResponse(
        success=False,
        error=ApiErrorDetail(code=code, message=message),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def queue_bid_resync_job(bid_id: str) -> QueuedSyncResponse:
    init_db()
    started_at = datetime.now()
    metadata = {
        "steps": [
            {"name": "detail_enrichment", "status": "queued"},
            {"name": "crawl", "status": "queued"},
        ]
    }
    with Session(engine) as session:
        log = SyncJobLog(
            job_type="bid_resync",
            target=bid_id,
            status="queued",
            started_at=started_at,
            finished_at=None,
            message="bid resync queued",
            metadata_json=json.dumps(metadata, ensure_ascii=False),
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return QueuedSyncResponse(
            job_id=log.id or 0,
            job_type=log.job_type,
            target=log.target,
            status="queued",
            message=log.message,
            started_at=started_at.strftime("%Y-%m-%d %H:%M"),
        )


def _update_sync_log(
    *,
    job_id: int,
    status: str,
    message: str,
    finished_at: datetime | None,
    metadata: dict[str, object] | None = None,
) -> None:
    with Session(engine) as session:
        log = session.get(SyncJobLog, job_id)
        if log is None:
            return
        log.status = status
        log.message = message
        log.finished_at = finished_at
        if metadata is not None:
            log.metadata_json = json.dumps(metadata, ensure_ascii=False)
        session.add(log)
        session.commit()


def _resync_metadata(
    detail_status: str,
    contract_status: str,
    crawl_status: str,
    *,
    detail_items: int = 0,
    contract_items: int = 0,
    attachments: int = 0,
    detail_started_at: str | None = None,
    detail_finished_at: str | None = None,
    contract_started_at: str | None = None,
    contract_finished_at: str | None = None,
    crawl_started_at: str | None = None,
    crawl_finished_at: str | None = None,
    failed_step: str | None = None,
    error_reason: str | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "steps": [
            {
                "name": "detail_enrichment",
                "status": detail_status,
                "fetched_item_count": detail_items,
                "started_at": detail_started_at,
                "finished_at": detail_finished_at,
            },
            {
                "name": "contract_process",
                "status": contract_status,
                "fetched_item_count": contract_items,
                "started_at": contract_started_at,
                "finished_at": contract_finished_at,
            },
            {
                "name": "crawl",
                "status": crawl_status,
                "attachment_count": attachments,
                "started_at": crawl_started_at,
                "finished_at": crawl_finished_at,
            },
        ]
    }
    if failed_step is not None:
        metadata["failed_step"] = failed_step
    if error_reason is not None:
        metadata["error_reason"] = error_reason
    return metadata


def execute_bid_resync_job(job_id: int, bid_id: str) -> None:
    queued_at = _now_text()
    _update_sync_log(
        job_id=job_id,
        status="running",
        message="bid resync running",
        finished_at=None,
        metadata=_resync_metadata(
            "running",
            "queued",
            "queued",
            detail_started_at=queued_at,
        ),
    )

    if settings.bid_data_backend == "sample":
        finished_at = _now_text()
        _update_sync_log(
            job_id=job_id,
            status="completed",
            message="sample backend resync completed",
            finished_at=datetime.now(),
            metadata=_resync_metadata(
                "completed",
                "completed",
                "completed",
                detail_started_at=queued_at,
                detail_finished_at=finished_at,
                contract_started_at=queued_at,
                contract_finished_at=finished_at,
                crawl_started_at=queued_at,
                crawl_finished_at=finished_at,
            ),
        )
        return

    client = G2BBidPublicInfoClient()
    contract_client = G2BContractProcessClient()
    crawler = G2BBidPageCrawler()
    detail_items = 0
    contract_items = 0
    detail_started_at = queued_at
    detail_finished_at: str | None = None
    contract_started_at: str | None = None
    contract_finished_at: str | None = None
    crawl_started_at: str | None = None
    crawl_finished_at: str | None = None

    try:
        with Session(engine) as session:
            detail_result = G2BBidDetailEnrichmentService(
                session=session,
                client=client,
            ).enrich_bids(
                bid_ids=[bid_id],
                operations=PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
                selection_mode="targeted",
                recent_days=7,
            )
            detail_items = detail_result.fetched_item_count
            detail_finished_at = _now_text()
            contract_started_at = detail_finished_at
            _update_sync_log(
                job_id=job_id,
                status="running",
                message="bid resync running",
                finished_at=None,
                metadata=_resync_metadata(
                    "completed",
                    "running",
                    "running",
                    detail_items=detail_items,
                    detail_started_at=detail_started_at,
                    detail_finished_at=detail_finished_at,
                    contract_started_at=contract_started_at,
                ),
            )
            contract_result = G2BContractProcessService(
                session=session,
                client=contract_client,
            ).enrich_timelines(bid_ids=[bid_id])
            contract_items = contract_result.fetched_item_count
            contract_finished_at = _now_text()
            crawl_started_at = contract_finished_at
            _update_sync_log(
                job_id=job_id,
                status="running",
                message="bid resync running",
                finished_at=None,
                metadata=_resync_metadata(
                    "completed",
                    "completed",
                    "running",
                    detail_items=detail_items,
                    contract_items=contract_items,
                    detail_started_at=detail_started_at,
                    detail_finished_at=detail_finished_at,
                    contract_started_at=contract_started_at,
                    contract_finished_at=contract_finished_at,
                    crawl_started_at=crawl_started_at,
                ),
            )
            crawl_result = G2BBidCrawlService(
                session=session,
                crawler=crawler,
            ).crawl_bids(bid_ids=[bid_id])
            crawl_finished_at = _now_text()

        _update_sync_log(
            job_id=job_id,
            status="completed",
            message=(
                f"processed {len(detail_result.processed_bid_ids)} bids, "
                f"fetched {detail_result.fetched_item_count} detail items, "
                f"fetched {contract_result.fetched_item_count} contract items, "
                f"stored {crawl_result.attachment_count} attachments"
            ),
            finished_at=datetime.now(),
            metadata=_resync_metadata(
                "completed",
                "completed",
                "completed",
                detail_items=detail_result.fetched_item_count,
                contract_items=contract_result.fetched_item_count,
                attachments=crawl_result.attachment_count,
                detail_started_at=detail_started_at,
                detail_finished_at=detail_finished_at,
                contract_started_at=contract_started_at,
                contract_finished_at=contract_finished_at,
                crawl_started_at=crawl_started_at,
                crawl_finished_at=crawl_finished_at,
            ),
        )
    except Exception as exc:
        failure_message = build_sync_failure_message(exc)
        error_reason = str(exc) or exc.__class__.__name__
        failed_at = _now_text()
        failed_step = "detail_enrichment"
        if detail_items > 0 and contract_items == 0:
            failed_step = "contract_process"
        elif contract_items > 0:
            failed_step = "crawl"
        _update_sync_log(
            job_id=job_id,
            status="failed",
            message=failure_message,
            finished_at=datetime.now(),
            metadata=_resync_metadata(
                "failed" if failed_step == "detail_enrichment" else "completed",
                (
                    "failed"
                    if failed_step == "contract_process"
                    else "queued"
                    if failed_step == "detail_enrichment"
                    else "completed"
                ),
                (
                    "failed"
                    if failed_step == "crawl"
                    else "queued"
                    if failed_step in {"detail_enrichment", "contract_process"}
                    else "completed"
                ),
                detail_items=detail_items,
                contract_items=contract_items,
                detail_started_at=detail_started_at,
                detail_finished_at=(
                    failed_at
                    if failed_step == "detail_enrichment"
                    else detail_finished_at
                ),
                contract_started_at=contract_started_at,
                contract_finished_at=(
                    failed_at
                    if failed_step == "contract_process"
                    else contract_finished_at
                ),
                crawl_started_at=crawl_started_at,
                crawl_finished_at=(
                    failed_at if failed_step == "crawl" else crawl_finished_at
                ),
                failed_step=failed_step,
                error_reason=error_reason,
            ),
        )
    finally:
        client.close()
        contract_client.close()


def _format_job_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%d %H:%M")


def _now_text() -> str:
    return _format_job_datetime(datetime.now()) or "-"


def _parse_job_metadata(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_sortable_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value or value == "없음":
        return datetime.min
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.min


def _parse_sortable_amount(value: object) -> int:
    if not isinstance(value, str):
        return 0
    digits = value.replace(",", "").strip()
    return int(digits) if digits.isdigit() else 0


def _sort_bid_payloads(
    bids: list[dict[str, object]], sort: str, order: str
) -> list[dict[str, object]]:
    reverse = order == "desc"
    if sort == "closed_at":
        return sorted(
            bids,
            key=lambda item: (
                _parse_sortable_datetime(item.get("closed_at")),
                str(item.get("bid_id", "")),
            ),
            reverse=reverse,
        )
    if sort == "budget_amount":
        return sorted(
            bids,
            key=lambda item: (
                _parse_sortable_amount(item.get("budget_amount")),
                str(item.get("bid_id", "")),
            ),
            reverse=reverse,
        )
    return sorted(
        bids,
        key=lambda item: (
            _parse_sortable_datetime(item.get("posted_at")),
            str(item.get("bid_id", "")),
        ),
        reverse=reverse,
    )


def _filter_bid_payloads(
    bids: list[dict[str, object]],
    *,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    closed_from: str | None = None,
    closed_to: str | None = None,
) -> list[dict[str, object]]:
    filtered = bids
    normalized_keyword = (keyword or "").strip().lower()
    normalized_org = (org or "").strip().lower()

    if normalized_keyword:
        filtered = [
            bid for bid in filtered if _bid_matches_keyword(bid, normalized_keyword)
        ]

    if normalized_org:
        filtered = [
            bid
            for bid in filtered
            if normalized_org in str(bid.get("notice_org", "")).lower()
            or normalized_org in str(bid.get("demand_org", "")).lower()
        ]

    if budget_min is not None:
        filtered = [
            bid
            for bid in filtered
            if _parse_sortable_amount(bid.get("budget_amount")) >= budget_min
        ]

    if budget_max is not None:
        filtered = [
            bid
            for bid in filtered
            if _parse_sortable_amount(bid.get("budget_amount")) <= budget_max
        ]

    closed_from_dt = _parse_sortable_datetime(closed_from) if closed_from else None
    if closed_from_dt is not None:
        filtered = [
            bid
            for bid in filtered
            if _parse_sortable_datetime(bid.get("closed_at")) >= closed_from_dt
        ]

    closed_to_dt = _parse_sortable_datetime(closed_to) if closed_to else None
    if closed_to_dt is not None:
        filtered = [
            bid
            for bid in filtered
            if _parse_sortable_datetime(bid.get("closed_at")) <= closed_to_dt
        ]

    return filtered


def _bid_matches_keyword(bid: dict[str, object], keyword: str) -> bool:
    searchable_values: list[str] = [
        str(bid.get("title", "")),
        str(bid.get("description_text", "")),
        str(bid.get("business_type", "")),
        str(bid.get("notice_type", "")),
    ]

    qualification = bid.get("qualification")
    if isinstance(qualification, dict):
        searchable_values.append(str(qualification.get("qualification_summary", "")))
        for key in ("license_limits", "permitted_industries", "regions"):
            value = qualification.get(key, [])
            if isinstance(value, list):
                searchable_values.extend(str(item) for item in value)

    business_info = bid.get("business_info")
    if isinstance(business_info, dict):
        searchable_values.extend(str(value) for value in business_info.values())

    return any(keyword in value.lower() for value in searchable_values)


def _get_filtered_bid_payloads(
    *,
    q: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    closed_from: str | None = None,
    closed_to: str | None = None,
    sort: str = "posted_at",
    order: str = "desc",
) -> list[dict[str, object]]:
    return list_raw_bids(
        search_query=q,
        status=status,
        favorites_only=favorites_only,
        keyword=keyword,
        org=org,
        budget_min=budget_min,
        budget_max=budget_max,
        closed_from=closed_from,
        closed_to=closed_to,
        sort=sort,
        order=order,
    )


EXPORT_FIELDNAMES = [
    "bid_id",
    "title",
    "notice_org",
    "demand_org",
    "status",
    "business_type",
    "budget_amount",
    "posted_at",
    "closed_at",
    "favorite",
]


def _export_bid_row(bid: dict[str, object]) -> dict[str, str]:
    return {
        "bid_id": str(bid.get("bid_id", "")),
        "title": str(bid.get("title", "")),
        "notice_org": str(bid.get("notice_org", "")),
        "demand_org": str(bid.get("demand_org", "")),
        "status": str(bid.get("status", "")),
        "business_type": str(bid.get("business_type", "")),
        "budget_amount": str(bid.get("budget_amount", "")),
        "posted_at": str(bid.get("posted_at", "")),
        "closed_at": str(bid.get("closed_at", "")),
        "favorite": str(bool(bid.get("favorite", False))).lower(),
    }


def _stream_bid_export_rows(bids: list[dict[str, object]]):
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDNAMES)
    writer.writeheader()
    yield buffer.getvalue()

    for bid in bids:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(_export_bid_row(bid))
        yield buffer.getvalue()


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {
        "success": True,
        "data": {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
        },
        "meta": {},
        "error": None,
    }


@app.get(
    "/api/v1/bids",
    response_model=BidListApiResponse,
    tags=["bids"],
    summary="List bids",
    description=(
        "입찰 공고 목록을 JSON으로 조회합니다. 검색, 기관명, 예산, 마감일, 관심 여부 필터와 "
        "페이지네이션/정렬을 지원합니다."
    ),
    responses={
        200: {
            "description": "Bid list retrieved successfully",
        },
        404: {
            "model": ApiErrorResponse,
            "description": "No bids matched the filters",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "meta": {},
                        "error": {
                            "code": "BIDS_NOT_FOUND",
                            "message": "조건에 맞는 공고를 찾을 수 없습니다.",
                        },
                    }
                }
            },
        },
    },
)
def list_bids_api(
    q: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
    closed_from: str | None = None,
    closed_to: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(
        default="posted_at", pattern="^(posted_at|closed_at|budget_amount)$"
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        raise HTTPException(
            status_code=422,
            detail="budget_max must be greater than or equal to budget_min",
        )

    if closed_from and closed_to:
        if _parse_sortable_datetime(closed_from) > _parse_sortable_datetime(closed_to):
            raise HTTPException(
                status_code=422,
                detail="closed_to must be greater than or equal to closed_from",
            )

    bid_page = list_raw_bids_page(
        page=page,
        page_size=page_size,
        search_query=q,
        status=status,
        favorites_only=favorites_only,
        keyword=keyword,
        org=org,
        budget_min=budget_min,
        budget_max=budget_max,
        closed_from=closed_from,
        closed_to=closed_to,
        sort=sort,
        order=order,
    )
    if bid_page.total == 0:
        return build_api_error_response(
            status_code=404,
            code="BIDS_NOT_FOUND",
            message="조건에 맞는 공고를 찾을 수 없습니다.",
        )

    total = bid_page.total
    total_pages = max(1, (total + page_size - 1) // page_size)

    return BidListApiResponse(
        data=BidListDataResponse(
            items=[BidListItemResponse.model_validate(bid) for bid in bid_page.items]
        ),
        meta=BidListMetaResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            search_query=(q or "").strip(),
            keyword=(keyword or "").strip(),
            status=(status or "").strip(),
            favorites_only=favorites_only,
            sort=sort,
            order=order,
        ),
    )


@app.get(
    "/api/v1/bids/export",
    tags=["bids"],
    summary="Export bids",
    description="현재 필터 기준 공고 목록을 CSV 형식으로 내려받습니다. Excel에서 바로 열 수 있습니다.",
    responses={
        200: {
            "description": "CSV export downloaded successfully",
            "content": {
                "text/csv": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
        404: {
            "model": ApiErrorResponse,
            "description": "No bids matched the filters",
        },
    },
)
def export_bids_api(
    q: str | None = None,
    status: str | None = None,
    favorites_only: bool = False,
    keyword: str | None = None,
    org: str | None = None,
    budget_min: int | None = Query(default=None, ge=0),
    budget_max: int | None = Query(default=None, ge=0),
    closed_from: str | None = None,
    closed_to: str | None = None,
    sort: str = Query(
        default="posted_at", pattern="^(posted_at|closed_at|budget_amount)$"
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    if budget_min is not None and budget_max is not None and budget_max < budget_min:
        raise HTTPException(
            status_code=422,
            detail="budget_max must be greater than or equal to budget_min",
        )

    if closed_from and closed_to:
        if _parse_sortable_datetime(closed_from) > _parse_sortable_datetime(closed_to):
            raise HTTPException(
                status_code=422,
                detail="closed_to must be greater than or equal to closed_from",
            )

    filtered_bids = _get_filtered_bid_payloads(
        q=q,
        status=status,
        favorites_only=favorites_only,
        keyword=keyword,
        org=org,
        budget_min=budget_min,
        budget_max=budget_max,
        closed_from=closed_from,
        closed_to=closed_to,
        sort=sort,
        order=order,
    )
    if not filtered_bids:
        return build_api_error_response(
            status_code=404,
            code="BIDS_NOT_FOUND",
            message="조건에 맞는 공고를 찾을 수 없습니다.",
        )

    return StreamingResponse(
        _stream_bid_export_rows(filtered_bids),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="bids-export.csv"',
        },
    )


@app.get(
    "/api/v1/bids/{bid_id}",
    response_model=BidDetailApiResponse,
    tags=["bids"],
    summary="Get bid detail",
    description="특정 입찰 공고의 상세 정보를 JSON으로 조회합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "meta": {},
                        "error": {
                            "code": "BID_NOT_FOUND",
                            "message": "해당 공고를 찾을 수 없습니다.",
                        },
                    }
                }
            },
        }
    },
)
def get_bid_api(bid_id: str):
    try:
        bid = get_raw_bid(bid_id)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    if str(bid.get("bid_id", "")) != bid_id:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    return BidDetailApiResponse(data=BidDetailResponseItem.model_validate(bid), meta={})


@app.patch(
    "/api/v1/bids/{bid_id}/status",
    response_model=BidDetailApiResponse,
    tags=["bids"],
    summary="Update bid status",
    description="특정 입찰 공고의 내부 관리 상태를 변경합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "data": None,
                        "meta": {},
                        "error": {
                            "code": "BID_NOT_FOUND",
                            "message": "해당 공고를 찾을 수 없습니다.",
                        },
                    }
                }
            },
        }
    },
)
def update_bid_status_api(bid_id: str, payload: BidStatusUpdateRequest):
    try:
        bid = update_raw_bid_status(bid_id, payload.status)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    return BidDetailApiResponse(data=BidDetailResponseItem.model_validate(bid), meta={})


@app.post(
    "/api/v1/bids/{bid_id}/favorite",
    response_model=BidDetailApiResponse,
    tags=["bids"],
    summary="Add bid favorite",
    description="특정 입찰 공고를 관심 공고로 등록합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
        }
    },
)
def add_bid_favorite_api(bid_id: str):
    try:
        bid = set_raw_bid_favorite(bid_id, True)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    return BidDetailApiResponse(data=BidDetailResponseItem.model_validate(bid), meta={})


@app.delete(
    "/api/v1/bids/{bid_id}/favorite",
    response_model=BidDetailApiResponse,
    tags=["bids"],
    summary="Remove bid favorite",
    description="특정 입찰 공고를 관심 공고에서 해제합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
        }
    },
)
def remove_bid_favorite_api(bid_id: str):
    try:
        bid = set_raw_bid_favorite(bid_id, False)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    return BidDetailApiResponse(data=BidDetailResponseItem.model_validate(bid), meta={})


@app.get(
    "/api/v1/bids/{bid_id}/attachments",
    response_model=BidAttachmentsApiResponse,
    tags=["bids"],
    summary="List bid attachments",
    description="특정 입찰 공고의 첨부파일 목록만 JSON으로 조회합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
        }
    },
)
def list_bid_attachments_api(bid_id: str):
    try:
        bid = get_raw_bid(bid_id)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    if str(bid.get("bid_id", "")) != bid_id:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    raw_attachments_value = bid.get("attachments", [])
    raw_attachments = (
        cast(list[object], raw_attachments_value)
        if isinstance(raw_attachments_value, list)
        else []
    )

    attachment_items = [
        BidAttachmentItemResponse.model_validate(item)
        for item in raw_attachments
        if isinstance(item, dict)
    ]
    return BidAttachmentsApiResponse(
        data=BidAttachmentsDataResponse(bid_id=bid_id, items=attachment_items),
        meta={},
    )


@app.get(
    "/api/v1/bids/{bid_id}/timeline",
    response_model=BidTimelineApiResponse,
    tags=["bids"],
    summary="List bid timeline",
    description="특정 입찰 공고의 타임라인 정보만 JSON으로 조회합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
        }
    },
)
def list_bid_timeline_api(bid_id: str):
    try:
        bid = get_raw_bid(bid_id)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    if str(bid.get("bid_id", "")) != bid_id:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    raw_timeline_value = bid.get("timeline", [])
    raw_timeline = (
        cast(list[object], raw_timeline_value)
        if isinstance(raw_timeline_value, list)
        else []
    )

    timeline_items = [
        BidTimelineItemResponse.model_validate(item)
        for item in raw_timeline
        if isinstance(item, dict)
    ]
    return BidTimelineApiResponse(
        data=BidTimelineDataResponse(bid_id=bid_id, items=timeline_items),
        meta={},
    )


@app.post(
    "/api/v1/bids/{bid_id}/resync",
    response_model=QueuedSyncResponse,
    tags=["bids"],
    summary="Queue bid resync",
    description="특정 입찰 공고의 재수집 작업을 큐에 등록합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bid not found",
        }
    },
)
def queue_bid_resync_api(bid_id: str, background_tasks: BackgroundTasks):
    try:
        bid = get_raw_bid(bid_id)
    except KeyError:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    if str(bid.get("bid_id", "")) != bid_id:
        return build_api_error_response(
            status_code=404,
            code="BID_NOT_FOUND",
            message="해당 공고를 찾을 수 없습니다.",
        )

    response = queue_bid_resync_job(bid_id)
    background_tasks.add_task(execute_bid_resync_job, response.job_id, bid_id)
    return response


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobStatusApiResponse,
    tags=["jobs"],
    summary="Get job status",
    description="재수집 또는 동기화 작업 로그의 현재 상태를 조회합니다.",
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Job not found",
        }
    },
)
def get_job_status_api(job_id: int):
    init_db()
    with Session(engine) as session:
        log = session.get(SyncJobLog, job_id)

    if log is None:
        return build_api_error_response(
            status_code=404,
            code="JOB_NOT_FOUND",
            message="해당 작업을 찾을 수 없습니다.",
        )

    started_at = _format_job_datetime(log.started_at) or "-"
    return JobStatusApiResponse(
        data=JobStatusDataResponse(
            job_id=log.id or job_id,
            job_type=log.job_type,
            target=log.target,
            status=log.status,
            started_at=started_at,
            finished_at=_format_job_datetime(log.finished_at),
            message=log.message,
            metadata=_parse_job_metadata(log.metadata_json),
        ),
        meta={},
    )


@app.get(
    "/api/v1/jobs",
    response_model=JobListApiResponse,
    tags=["jobs"],
    summary="List jobs",
    description="재수집/동기화 작업 로그 목록을 최신순으로 조회합니다.",
)
def list_jobs_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: Literal["started_at", "finished_at", "status"] = "started_at",
    order: Literal["asc", "desc"] = "desc",
    status: Literal["queued", "running", "completed", "failed"] | None = None,
    job_type: Literal[
        "bid_resync",
        "bid_public_info_sync",
        "bid_detail_enrichment",
        "contract_process_sync",
        "bid_page_crawl",
        "phase2_batch_sync",
    ]
    | None = None,
    started_from: str | None = None,
    started_to: str | None = None,
    finished_from: str | None = None,
    finished_to: str | None = None,
):
    if started_from and started_to:
        if _parse_sortable_datetime(started_from) > _parse_sortable_datetime(
            started_to
        ):
            raise HTTPException(
                status_code=422,
                detail="started_to must be greater than or equal to started_from",
            )
    if finished_from and finished_to:
        if _parse_sortable_datetime(finished_from) > _parse_sortable_datetime(
            finished_to
        ):
            raise HTTPException(
                status_code=422,
                detail="finished_to must be greater than or equal to finished_from",
            )

    init_db()
    with Session(engine) as session:
        statement = select(SyncJobLog)

        if status:
            statement = statement.where(SyncJobLog.status == status)  # type: ignore[operator]
        if job_type:
            statement = statement.where(SyncJobLog.job_type == job_type)  # type: ignore[operator]
        started_from_dt = (
            _parse_sortable_datetime(started_from) if started_from else None
        )
        if started_from_dt is not None and started_from_dt != datetime.min:
            statement = statement.where(SyncJobLog.started_at >= started_from_dt)  # type: ignore[operator]
        started_to_dt = _parse_sortable_datetime(started_to) if started_to else None
        if started_to_dt is not None and started_to_dt != datetime.min:
            statement = statement.where(SyncJobLog.started_at <= started_to_dt)  # type: ignore[operator]
        finished_from_dt = (
            _parse_sortable_datetime(finished_from) if finished_from else None
        )
        if finished_from_dt is not None and finished_from_dt != datetime.min:
            statement = statement.where(SyncJobLog.finished_at >= finished_from_dt)  # type: ignore[operator]
        finished_to_dt = _parse_sortable_datetime(finished_to) if finished_to else None
        if finished_to_dt is not None and finished_to_dt != datetime.min:
            statement = statement.where(SyncJobLog.finished_at <= finished_to_dt)  # type: ignore[operator]

        total = len(list(session.exec(statement).all()))
        sort_column = SyncJobLog.started_at
        if sort == "finished_at":
            sort_column = SyncJobLog.finished_at
        elif sort == "status":
            sort_column = SyncJobLog.status
        logs = list(
            session.exec(
                statement.order_by(
                    sort_column.asc() if order == "asc" else sort_column.desc()  # type: ignore[attr-defined]
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )

    items = [
        JobListItemResponse(
            job_id=log.id or 0,
            job_type=log.job_type,
            target=log.target,
            status=log.status,
            started_at=_format_job_datetime(log.started_at) or "-",
            finished_at=_format_job_datetime(log.finished_at),
            message=log.message,
            metadata=_parse_job_metadata(log.metadata_json),
        )
        for log in logs
    ]
    return JobListApiResponse(
        data=JobListDataResponse(items=items),
        meta=JobListMetaResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        ),
    )


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/doc", response_class=HTMLResponse, include_in_schema=False)
def custom_docs_page(request: Request, doc: str | None = Query(default=None)):
    selected_item = get_docs_nav_item(doc) if doc else None
    return templates.TemplateResponse(
        request=request,
        name="pages/docs/index.html",
        context={
            "active_nav": None,
            "docs_nav_items": DOCS_NAV_ITEMS,
            "docs_nav_groups": get_grouped_docs_nav_items(),
            "selected_doc": selected_item,
            "docs_group_name": selected_item["group"] if selected_item else None,
            "selected_doc_id": selected_item["id"] if selected_item else None,
            "selected_doc_label": selected_item["label"] if selected_item else None,
            "selected_doc_description": (
                selected_item["description"] if selected_item else None
            ),
            "swagger_embed_url": (
                f"{request.url_for('swagger_embed')}?doc={selected_item['id']}"
                if selected_item
                else None
            ),
            "openapi_url": app.openapi_url,
        },
    )


@app.get("/docs/openapi/{doc_id}.json", include_in_schema=False)
def filtered_openapi_schema(doc_id: str):
    return JSONResponse(build_filtered_openapi_schema(doc_id))


@app.get("/docs/swagger", response_class=HTMLResponse, include_in_schema=False)
def swagger_embed(doc: str = Query(...)):
    nav_item = get_docs_nav_item(doc)
    openapi_url = cast(str, nav_item["openapi_path"])
    response = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=f"{nav_item['label']} - Swagger UI",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "list",
            "filter": True,
            "displayRequestDuration": True,
        },
    )
    html = (
        bytes(response.body)
        .decode("utf-8")
        .replace("</head>", f"{SWAGGER_CUSTOM_STYLES}</head>")
    )
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/bids/index.html",
        context=get_bids_page_context(),
    )


@app.get("/bids", response_class=HTMLResponse, include_in_schema=False)
def bids_page(request: Request):
    search_query = request.query_params.get("q")
    status = request.query_params.get("status")
    favorites_only = request.query_params.get("favorites") in {"1", "true", "on"}
    return templates.TemplateResponse(
        request=request,
        name="pages/bids/index.html",
        context=get_bids_page_context(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
        ),
    )


@app.get("/prespecs", response_class=HTMLResponse, include_in_schema=False)
def prespecs_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/prespecs/index.html",
        context=get_prespecs_page_context(),
    )


@app.get("/results", response_class=HTMLResponse, include_in_schema=False)
def results_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/results/index.html",
        context=get_results_page_context(),
    )


@app.get("/favorites", response_class=HTMLResponse, include_in_schema=False)
def favorites_page(request: Request):
    search_query = request.query_params.get("q")
    status = request.query_params.get("status")
    return templates.TemplateResponse(
        request=request,
        name="pages/favorites/index.html",
        context=get_favorites_page_context(search_query=search_query, status=status),
    )


@app.get("/operations", response_class=HTMLResponse, include_in_schema=False)
def operations_page(request: Request):
    status_filter = request.query_params.get("status")
    job_type_filter = request.query_params.get("job_type")
    return templates.TemplateResponse(
        request=request,
        name="pages/operations/index.html",
        context=get_operations_page_context(
            status_filter=status_filter, job_type_filter=job_type_filter
        ),
    )


@app.get("/partials/bids/table", response_class=HTMLResponse, include_in_schema=False)
def bids_table_partial(request: Request):
    search_query = request.query_params.get("q")
    status = request.query_params.get("status")
    favorites_only = request.query_params.get("favorites") in {"1", "true", "on"}
    return templates.TemplateResponse(
        request=request,
        name="partials/bids/_bid_table.html",
        context=get_bids_page_context(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
        ),
    )


@app.get(
    "/partials/favorites/table", response_class=HTMLResponse, include_in_schema=False
)
def favorites_table_partial(request: Request):
    search_query = request.query_params.get("q")
    status = request.query_params.get("status")
    return templates.TemplateResponse(
        request=request,
        name="partials/favorites/_favorites_table.html",
        context=get_favorites_page_context(search_query=search_query, status=status),
    )


@app.get(
    "/partials/bids/{bid_id}/drawer",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def bid_drawer_partial(request: Request, bid_id: str):
    drawer_vm = build_bid_drawer_vm(get_selected_raw_bid(bid_id))
    return templates.TemplateResponse(
        request=request,
        name="partials/bids/_drawer.html",
        context={
            "selected_bid": drawer_vm,
            "last_synced_at": LAST_SYNCED_AT,
            "active_nav": "bids",
        },
    )


@app.get(
    "/partials/bids/{bid_id}/timeline-inline",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def bid_timeline_inline_partial(request: Request, bid_id: str):
    drawer_vm = build_bid_drawer_vm(get_selected_raw_bid(bid_id))
    return templates.TemplateResponse(
        request=request,
        name="partials/bids/_timeline_inline.html",
        context={
            "selected_bid": drawer_vm,
            "last_synced_at": LAST_SYNCED_AT,
            "active_nav": "bids",
        },
    )
