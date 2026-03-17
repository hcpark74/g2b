from typing import Any, Literal

from pydantic import BaseModel, Field


class BidPublicInfoSyncRequest(BaseModel):
    begin: str = Field(..., description="조회 시작 시각 (YYYYMMDDHHMM)")
    end: str = Field(..., description="조회 종료 시각 (YYYYMMDDHHMM)")
    operations: list[str] | None = Field(
        default=None,
        description="실행할 입찰공고정보서비스 operation 목록. 비우면 기본 4종 사용",
    )
    rows: int = Field(default=100, ge=1, le=1000, description="API 페이지당 조회 건수")

    model_config = {
        "json_schema_extra": {
            "example": {
                "begin": "202603120000",
                "end": "202603132359",
                "operations": ["getBidPblancListInfoServc"],
                "rows": 100,
            }
        }
    }


class BidDetailEnrichmentRequest(BaseModel):
    bid_ids: list[str] | None = Field(
        default=None,
        description="특정 공고만 보강할 때 사용하는 bid_id 목록",
    )
    operations: list[str] | None = Field(
        default=None,
        description="실행할 상세 보강 operation 목록. 비우면 Phase 2 기본 보강 목록 사용",
    )
    selection_mode: Literal["targeted", "all"] = Field(
        default="targeted",
        description="bid_ids 미지정 시 대상 공고 선별 방식",
    )
    recent_days: int = Field(
        default=7, ge=1, le=30, description="최근 변경 공고 판정 일수"
    )
    rows: int = Field(default=100, ge=1, le=1000, description="API 페이지당 조회 건수")

    model_config = {
        "json_schema_extra": {
            "example": {
                "bid_ids": ["R26BK00001001-000"],
                "operations": ["getBidPblancListInfoLicenseLimit"],
                "selection_mode": "targeted",
                "recent_days": 7,
                "rows": 100,
            }
        }
    }


class ContractProcessSyncRequest(BaseModel):
    bid_ids: list[str] | None = Field(
        default=None,
        description="특정 공고만 보강할 때 사용하는 bid_id 목록",
    )
    rows: int = Field(default=100, ge=1, le=1000, description="API 페이지당 조회 건수")

    model_config = {
        "json_schema_extra": {
            "example": {
                "bid_ids": ["R26BK00001002-000"],
                "rows": 100,
            }
        }
    }


class BidCrawlRequest(BaseModel):
    bid_ids: list[str] = Field(..., min_length=1, description="크롤링할 bid_id 목록")
    headless: bool | None = Field(
        default=None,
        description="Playwright headless 모드 override. None이면 설정값 사용",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "bid_ids": ["R26BK00001003-000"],
                "headless": True,
            }
        }
    }


class Phase2BatchSyncRequest(BaseModel):
    bid_ids: list[str] | None = Field(
        default=None,
        description="특정 공고만 처리할 때 사용하는 bid_id 목록",
    )
    selection_mode: Literal["targeted", "all"] = Field(
        default="targeted",
        description="bid_ids 미지정 시 대상 공고 선별 방식",
    )
    recent_days: int = Field(
        default=7, ge=1, le=30, description="최근 변경 공고 판정 일수"
    )
    rows: int = Field(default=100, ge=1, le=1000, description="API 페이지당 조회 건수")
    skip_detail: bool = Field(default=False, description="상세 보강 단계 생략")
    skip_change_history: bool = Field(
        default=False, description="변경이력 보강 단계 생략"
    )
    skip_contract: bool = Field(default=False, description="계약과정통합공개 단계 생략")
    skip_crawl: bool = Field(default=False, description="Playwright 크롤링 단계 생략")
    skip_reference: bool = Field(
        default=False, description="업종 기준정보 보강 단계 생략"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "selection_mode": "targeted",
                "recent_days": 7,
                "rows": 100,
                "skip_detail": False,
                "skip_change_history": False,
                "skip_contract": False,
                "skip_crawl": False,
                "skip_reference": False,
            }
        }
    }


class JobLogCleanupRequest(BaseModel):
    older_than_days: int | None = Field(
        default=None,
        ge=1,
        description="이 일수보다 오래된 로그 삭제. 비우면 설정 기본값 사용",
    )
    status: str | None = Field(default=None, description="특정 상태 로그만 삭제")
    job_type: str | None = Field(default=None, description="특정 작업 유형 로그만 삭제")
    dry_run: bool = Field(default=False, description="실제 삭제 없이 대상 개수만 확인")

    model_config = {
        "json_schema_extra": {
            "example": {
                "older_than_days": 30,
                "status": "completed",
                "job_type": "bid_resync",
                "dry_run": True,
            }
        }
    }


class JobLogCleanupResponse(BaseModel):
    deleted_count: int
    cutoff_at: str
    dry_run: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "deleted_count": 12,
                "cutoff_at": "2026-02-13 12:00",
                "dry_run": True,
            }
        }
    }


class SyncExecutionResponse(BaseModel):
    job_type: str
    target: str
    status: Literal["completed", "failed", "running"]
    message: str
    started_at: str | None = None
    finished_at: str | None = None


class QueuedSyncResponse(BaseModel):
    job_id: int
    job_type: str
    target: str
    status: Literal["queued"]
    message: str
    started_at: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": 101,
                "job_type": "bid_resync",
                "target": "R26BK00000001-000",
                "status": "queued",
                "message": "bid resync queued",
                "started_at": "2026-03-14 07:30",
            }
        }
    }


class BidPublicInfoSyncResponse(SyncExecutionResponse):
    fetched_count: int
    upserted_count: int
    bid_ids: list[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_type": "bid_public_info_sync",
                "target": "getBidPblancListInfoServc",
                "status": "completed",
                "message": "fetched 3 bids, upserted 2 bids",
                "started_at": "2026-03-14 06:10",
                "finished_at": "2026-03-14 06:11",
                "fetched_count": 3,
                "upserted_count": 2,
                "bid_ids": ["R26BK00000001-000", "R26BK00000002-000"],
            }
        }
    }


class BidDetailEnrichmentResponse(SyncExecutionResponse):
    processed_bid_ids: list[str]
    fetched_item_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_type": "bid_detail_enrichment",
                "target": "R26BK00001001-000",
                "status": "completed",
                "message": "operations=getBidPblancListInfoLicenseLimit selection_mode=targeted processed 1 bids, fetched 4 items",
                "started_at": "2026-03-14 06:12",
                "finished_at": "2026-03-14 06:13",
                "processed_bid_ids": ["R26BK00001001-000"],
                "fetched_item_count": 4,
            }
        }
    }


class ContractProcessSyncResponse(SyncExecutionResponse):
    processed_bid_ids: list[str]
    fetched_item_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_type": "contract_process_sync",
                "target": "R26BK00001002-000",
                "status": "completed",
                "message": "processed 1 bids, fetched 1 items",
                "started_at": "2026-03-14 06:14",
                "finished_at": "2026-03-14 06:15",
                "processed_bid_ids": ["R26BK00001002-000"],
                "fetched_item_count": 1,
            }
        }
    }


class BidCrawlResponse(SyncExecutionResponse):
    processed_bid_ids: list[str]
    attachment_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_type": "bid_page_crawl",
                "target": "R26BK00001003-000",
                "status": "completed",
                "message": "processed 1 bids, stored 2 attachments",
                "started_at": "2026-03-14 06:16",
                "finished_at": "2026-03-14 06:17",
                "processed_bid_ids": ["R26BK00001003-000"],
                "attachment_count": 2,
            }
        }
    }


class Phase2BatchSyncResponse(SyncExecutionResponse):
    processed_bid_ids: list[str]
    detail_items: int
    change_history_items: int
    contract_items: int
    crawl_attachments: int
    reference_items: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_type": "phase2_batch_sync",
                "target": "R26BK00001004-000",
                "status": "completed",
                "message": "selection_mode=targeted processed 1 bids detail_items=2 change_history_items=1 contract_items=1 crawl_attachments=3 reference_items=2",
                "started_at": "2026-03-14 06:18",
                "finished_at": "2026-03-14 06:21",
                "processed_bid_ids": ["R26BK00001004-000"],
                "detail_items": 2,
                "change_history_items": 1,
                "contract_items": 1,
                "crawl_attachments": 3,
                "reference_items": 2,
            }
        }
    }


class SyncOperationItemResponse(BaseModel):
    id: int | None = None
    job_type: str
    target: str
    status: str
    started_at: str
    finished_at: str | None = None
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 12,
                "job_type": "phase2_batch_sync",
                "target": "R26BK00001004-000",
                "status": "completed",
                "started_at": "2026-03-14 06:18",
                "finished_at": "2026-03-14 06:21",
                "message": "selection_mode=targeted processed 1 bids detail_items=2 contract_items=1 crawl_attachments=3 reference_items=2",
            }
        }
    }


class SyncOperationListResponse(BaseModel):
    items: list[SyncOperationItemResponse]

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": 12,
                        "job_type": "phase2_batch_sync",
                        "target": "R26BK00001004-000",
                        "status": "completed",
                        "started_at": "2026-03-14 06:18",
                        "finished_at": "2026-03-14 06:21",
                        "message": "selection_mode=targeted processed 1 bids detail_items=2 contract_items=1 crawl_attachments=3 reference_items=2",
                    }
                ]
            }
        }
    }


class ApiErrorDetail(BaseModel):
    code: str
    message: str


BID_LIST_ITEM_EXAMPLE = {
    "bid_id": "R26BK00000001-000",
    "bid_no": "R26BK00000001-000",
    "bid_seq": "000",
    "display_bid_no": "R26BK00000001-000",
    "title": "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역",
    "notice_org": "조달청 경남지방조달청",
    "demand_org": "중소벤처기업진흥공단",
    "status": "검토중",
    "status_variant": "primary",
    "business_type": "용역",
    "domain_type": "내자",
    "notice_type": "등록공고",
    "budget_amount": "120,000,000",
    "last_synced_at": "2026-03-14 06:10",
    "detail_url": "",
    "posted_at": "2026-03-12 21:13:29",
    "closed_at": "2026-03-18 14:00",
    "opened_at": "2026-03-18 15:00",
    "stage_label": "입찰공고",
    "step_label": "공고등록",
    "progress_label": "진행완료",
    "favorite": True,
}


BID_DETAIL_ITEM_EXAMPLE = {
    **BID_LIST_ITEM_EXAMPLE,
    "detail_url": "https://example.com/bids/R26BK00000001-000",
    "detail_rows": [
        {
            "left_label": "공고종류",
            "left_value": "등록공고",
            "right_label": "게시일시",
            "right_value": "2026-03-12 21:13:29",
        }
    ],
    "qualification": {
        "industry_limited": True,
        "regions": ["전국"],
    },
    "business_info": {
        "service_division": "일반용역",
    },
    "attachments": [
        {
            "name": "입찰공고문.hwpx",
            "type": "일반",
            "source": "공고첨부",
            "url": "#",
        }
    ],
    "description_text": "사회적 고립청년 발굴 및 지원체계 운영을 위한 종합관리시스템 유지보수 사업이다.",
    "crawl_excerpt": "",
    "timeline": [
        {
            "stage": "입찰공고",
            "status": "진행중",
            "number": "R26BK00000001-000",
            "date": "2026-03-12 09:00",
            "meta": "입찰마감 2026-03-18 14:00",
        }
    ],
    "history": [
        {
            "changed_at": "2026-03-12 10:12",
            "item": "공고명",
            "before": "중소기업 인력지원사업 유지보수",
            "after": "2026년 중소기업 인력지원사업 종합관리시스템 유지보수 용역",
        }
    ],
}


class BidListItemResponse(BaseModel):
    bid_id: str
    bid_no: str
    bid_seq: str
    display_bid_no: str | None = None
    title: str
    notice_org: str | None = None
    demand_org: str | None = None
    status: str
    status_variant: str | None = None
    business_type: str | None = None
    domain_type: str | None = None
    notice_type: str | None = None
    budget_amount: str | None = None
    last_synced_at: str | None = None
    detail_url: str | None = None
    posted_at: str | None = None
    closed_at: str | None = None
    opened_at: str | None = None
    stage_label: str | None = None
    step_label: str | None = None
    progress_label: str | None = None
    favorite: bool = False

    model_config = {
        "extra": "allow",
        "json_schema_extra": {"example": BID_LIST_ITEM_EXAMPLE},
    }


class BidDetailResponseItem(BidListItemResponse):
    detail_rows: list[dict[str, str]] = Field(default_factory=list)
    qualification: dict[str, Any] = Field(default_factory=dict)
    business_info: dict[str, Any] = Field(default_factory=dict)
    attachments: list[dict[str, str]] = Field(default_factory=list)
    description_text: str = ""
    crawl_excerpt: str | None = None
    timeline: list[dict[str, str]] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)

    model_config = {
        "extra": "allow",
        "json_schema_extra": {"example": BID_DETAIL_ITEM_EXAMPLE},
    }


class BidListDataResponse(BaseModel):
    items: list[BidListItemResponse]


class BidListMetaResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    search_query: str
    keyword: str
    status: str
    favorites_only: bool
    sort: str
    order: str


class BidListApiResponse(BaseModel):
    success: bool = True
    data: BidListDataResponse
    meta: BidListMetaResponse
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {"items": [BID_LIST_ITEM_EXAMPLE]},
                "meta": {
                    "total": 1,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 1,
                    "search_query": "유지보수",
                    "keyword": "데이터서비스",
                    "status": "",
                    "favorites_only": False,
                    "sort": "posted_at",
                    "order": "desc",
                },
                "error": None,
            }
        }
    }


class LiveBidSearchItemResponse(BaseModel):
    bid_id: str
    bid_no: str
    bid_seq: str
    display_bid_no: str
    title: str
    notice_org: str | None = None
    demand_org: str | None = None
    business_type: str | None = None
    posted_at: str | None = None
    closed_at: str | None = None
    opened_at: str | None = None
    budget_amount: str | None = None
    detail_url: str | None = None
    source_api_name: str | None = None
    favorite: bool = False


class LiveBidSearchDataResponse(BaseModel):
    items: list[LiveBidSearchItemResponse]


class LiveBidSearchMetaResponse(BaseModel):
    total: int
    search_query: str
    org: str
    closed_from: str
    closed_to: str
    sort: str
    source: str = "external_api"


class LiveBidSearchApiResponse(BaseModel):
    success: bool = True
    data: LiveBidSearchDataResponse
    meta: LiveBidSearchMetaResponse
    error: None = None


class BidDetailApiResponse(BaseModel):
    success: bool = True
    data: BidDetailResponseItem
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": BID_DETAIL_ITEM_EXAMPLE,
                "meta": {},
                "error": None,
            }
        }
    }


class ApiErrorResponse(BaseModel):
    success: bool = False
    data: None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiErrorDetail

    model_config = {
        "json_schema_extra": {
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
    }


class BidStatusUpdateRequest(BaseModel):
    status: Literal[
        "collected",
        "reviewing",
        "favorite",
        "submitted",
        "won",
        "archived",
    ] = Field(..., description="변경할 내부 상태값")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "reviewing",
            }
        }
    }


class BidAttachmentItemResponse(BaseModel):
    name: str
    type: str
    source: str
    url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "입찰공고문.hwpx",
                "type": "일반",
                "source": "공고첨부",
                "url": "#",
            }
        }
    }


class BidAttachmentsDataResponse(BaseModel):
    bid_id: str
    items: list[BidAttachmentItemResponse]


class BidAttachmentsApiResponse(BaseModel):
    success: bool = True
    data: BidAttachmentsDataResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {
                    "bid_id": "R26BK00000001-000",
                    "items": [
                        {
                            "name": "입찰공고문.hwpx",
                            "type": "일반",
                            "source": "공고첨부",
                            "url": "#",
                        }
                    ],
                },
                "meta": {},
                "error": None,
            }
        }
    }


class BidTimelineItemResponse(BaseModel):
    stage: str
    status: str
    number: str
    date: str
    meta: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "stage": "입찰공고",
                "status": "진행중",
                "number": "R26BK00000001-000",
                "date": "2026-03-12 09:00",
                "meta": "입찰마감 2026-03-18 14:00",
            }
        }
    }


class BidTimelineDataResponse(BaseModel):
    bid_id: str
    items: list[BidTimelineItemResponse]


class BidTimelineApiResponse(BaseModel):
    success: bool = True
    data: BidTimelineDataResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {
                    "bid_id": "R26BK00000001-000",
                    "items": [
                        {
                            "stage": "입찰공고",
                            "status": "진행중",
                            "number": "R26BK00000001-000",
                            "date": "2026-03-12 09:00",
                            "meta": "입찰마감 2026-03-18 14:00",
                        }
                    ],
                },
                "meta": {},
                "error": None,
            }
        }
    }


class JobStatusDataResponse(BaseModel):
    job_id: int
    job_type: str
    target: str
    status: str
    started_at: str
    finished_at: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobStatusApiResponse(BaseModel):
    success: bool = True
    data: JobStatusDataResponse
    meta: dict[str, Any] = Field(default_factory=dict)
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {
                    "job_id": 101,
                    "job_type": "bid_resync",
                    "target": "R26BK00000001-000",
                    "status": "queued",
                    "started_at": "2026-03-14 07:30",
                    "finished_at": None,
                    "message": "bid resync queued",
                    "metadata": {
                        "steps": [
                            {"name": "detail_enrichment", "status": "queued"},
                            {"name": "contract_process", "status": "queued"},
                            {"name": "crawl", "status": "queued"},
                        ]
                    },
                },
                "meta": {},
                "error": None,
            }
        }
    }


class JobListItemResponse(BaseModel):
    job_id: int
    job_type: str
    target: str
    status: str
    started_at: str
    finished_at: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobListDataResponse(BaseModel):
    items: list[JobListItemResponse]


class JobListMetaResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class JobListApiResponse(BaseModel):
    success: bool = True
    data: JobListDataResponse
    meta: JobListMetaResponse
    error: None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "data": {
                    "items": [
                        {
                            "job_id": 101,
                            "job_type": "bid_resync",
                            "target": "R26BK00000001-000",
                            "status": "completed",
                            "started_at": "2026-03-14 07:30",
                            "finished_at": "2026-03-14 07:33",
                            "message": "processed 1 bids, fetched 4 detail items, fetched 3 contract items, stored 2 attachments",
                            "metadata": {
                                "steps": [
                                    {
                                        "name": "detail_enrichment",
                                        "status": "completed",
                                    },
                                    {"name": "contract_process", "status": "completed"},
                                    {"name": "crawl", "status": "completed"},
                                ]
                            },
                        }
                    ]
                },
                "meta": {"total": 1, "page": 1, "page_size": 20, "total_pages": 1},
                "error": None,
            }
        }
    }
