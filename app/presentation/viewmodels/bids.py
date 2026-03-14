from typing import Optional

from pydantic import BaseModel

from app.presentation.viewmodels.dashboard import DashboardSummaryVM
from app.presentation.viewmodels.timeline import TimelineStageVM


class BidDetailRowVM(BaseModel):
    left_label: str
    left_value: str
    right_label: str
    right_value: str


class BidQualificationItemVM(BaseModel):
    label: str
    value: str


class BidReferenceInfoVM(BaseModel):
    name: str
    code: str
    law_name: str
    source_api_name: str


class BidAttachmentVM(BaseModel):
    name: str
    type: str
    source: str
    url: str
    download_label: str = "다운로드"


class BidHistoryItemVM(BaseModel):
    changed_at: str
    item: str
    before: str
    after: str


class BidQualificationVM(BaseModel):
    industry_limited: bool
    international_bid: str
    rebid_allowed: str
    bid_participation_limit: str
    consortium_method: str
    license_limits: list[str]
    permitted_industries: list[str]
    regions: list[str]
    reference_infos: list[BidReferenceInfoVM]
    qualification_summary: str
    business_specific: list[BidQualificationItemVM]


class BidListItemVM(BaseModel):
    bid_id: str
    display_bid_no: str
    row_number: int
    favorite: bool
    status: str
    status_variant: str
    business_type: str
    domain_type: str
    notice_type: str
    bid_no: str
    title: str
    notice_org: str
    demand_org: str
    budget_amount: str
    posted_at: str
    closed_at: str
    opened_at: str
    stage_label: str
    step_label: str
    progress_label: str
    summary_badge: str


class BidDrawerVM(BaseModel):
    bid_id: str
    display_bid_no: str
    title: str
    business_type: str
    status: str
    status_variant: str
    description_text: str = ""
    detail_url: str = ""
    crawl_excerpt: str = ""
    overview_rows: list[BidDetailRowVM]
    qualification: BidQualificationVM
    attachments: list[BidAttachmentVM]
    timeline: list[TimelineStageVM]
    history: list[BidHistoryItemVM]


class BidsPageVM(BaseModel):
    summary: DashboardSummaryVM
    bids: list[BidListItemVM]
    selected_bid: Optional[BidDrawerVM] = None
    total_count: int
    active_nav: str = "bids"
