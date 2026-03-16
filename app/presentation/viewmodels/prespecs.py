from pydantic import BaseModel

from app.presentation.viewmodels.dashboard import DashboardSummaryVM


class PrespecItemVM(BaseModel):
    stage: str
    business_type: str
    title: str
    key: str
    org: str
    demand_org: str
    date: str
    linked_bid: str
    linked_bid_variant: str = "secondary"
    linked_bid_id: str = ""


class PrespecsPageVM(BaseModel):
    title: str
    description: str
    active_nav: str
    last_synced_at: str
    summary: DashboardSummaryVM
    items: list[PrespecItemVM]
